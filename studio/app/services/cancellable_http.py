from __future__ import annotations

"""Small cancellable JSON/HTTP transport used by the AI provider layer.

The public ``AbortHandle.cancel()`` method is safe to call from another thread.
It immediately closes the currently active TCP/TLS socket and marks the request
cancelled.  The blocking connect/read work lives in a short-lived daemon helper
thread, so the owning Qt worker can return immediately even if the operating
system is still unwinding DNS or a connect() call.

This is transport cancellation: it guarantees LuaS30 stops sending/receiving on
its HTTP connection.  A remote provider may already have received the request,
and only the provider itself can guarantee cancellation of server-side compute.
"""

import http.client
import json
import queue
import socket
import ssl
import threading
import urllib.parse
from typing import Any


class RequestCancelled(RuntimeError):
    """Raised when a request was explicitly cancelled by the user."""


class AbortHandle:
    """Cross-thread cancellation handle for one HTTP request."""

    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._lock = threading.RLock()
        self._connection: http.client.HTTPConnection | None = None
        self._response: http.client.HTTPResponse | None = None

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def check(self) -> None:
        if self.cancelled:
            raise RequestCancelled("Request cancelled")

    def bind_connection(self, connection: http.client.HTTPConnection) -> None:
        with self._lock:
            self._connection = connection
            cancelled = self.cancelled
        if cancelled:
            self._close_connection(connection)
            raise RequestCancelled("Request cancelled")

    def bind_response(self, response: http.client.HTTPResponse) -> None:
        with self._lock:
            self._response = response
            cancelled = self.cancelled
        if cancelled:
            try:
                response.close()
            except Exception:
                pass
            raise RequestCancelled("Request cancelled")

    def clear(self) -> None:
        with self._lock:
            self._response = None
            self._connection = None

    @staticmethod
    def _close_connection(connection: http.client.HTTPConnection | None) -> None:
        if connection is None:
            return
        # Shutdown the underlying TCP/TLS socket first.  Closing only the
        # HTTPConnection can otherwise leave a blocked response.read() waiting
        # until its normal socket timeout on some platforms.
        try:
            sock = connection.sock
        except Exception:
            sock = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except (OSError, ssl.SSLError, ValueError):
                pass
            try:
                sock.close()
            except (OSError, ssl.SSLError, ValueError):
                pass
        try:
            connection.close()
        except Exception:
            pass

    def cancel(self) -> None:
        """Cancel immediately and close the active transport, if any."""
        self._cancelled.set()
        with self._lock:
            response = self._response
            connection = self._connection
        # Closing the socket is the important operation.  response.close() is
        # still attempted afterwards to release http.client bookkeeping.
        self._close_connection(connection)
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _target_from_url(parts: urllib.parse.SplitResult) -> str:
    target = parts.path or "/"
    if parts.query:
        target += "?" + parts.query
    return target


def _connection_from_url(parts: urllib.parse.SplitResult, timeout: float) -> http.client.HTTPConnection:
    scheme = parts.scheme.lower()
    host = parts.hostname
    if not host:
        raise RuntimeError("Provider URL has no host.")
    port = parts.port
    if scheme == "https":
        return http.client.HTTPSConnection(
            host,
            port or 443,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
    if scheme == "http":
        return http.client.HTTPConnection(host, port or 80, timeout=timeout)
    raise RuntimeError(f"Unsupported provider URL scheme: {parts.scheme or '<empty>'}")


def _blocking_post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
    abort: AbortHandle,
) -> dict[str, Any]:
    """Run one blocking HTTP request inside the transport helper thread."""
    abort.check()
    parts = urllib.parse.urlsplit(url)
    connection = _connection_from_url(parts, max(1.0, float(timeout)))
    abort.bind_connection(connection)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }

    try:
        # Connect explicitly so a cancellation that happened during DNS/TCP/TLS
        # setup can be observed before any API request body is transmitted.
        connection.connect()
        abort.check()
        connection.request("POST", _target_from_url(parts), body=body, headers=request_headers)
        abort.check()
        response = connection.getresponse()
        abort.bind_response(response)

        chunks: list[bytes] = []
        while True:
            abort.check()
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        abort.check()
        raw = b"".join(chunks).decode("utf-8", errors="replace")
        status = int(response.status or 0)
        if status >= 400:
            raise RuntimeError(f"HTTP {status}: {raw[:4000]}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Provider returned non-JSON data: {raw[:2000]}") from exc
        if not isinstance(value, dict):
            raise RuntimeError("Provider returned JSON that is not an object.")
        return value
    except RequestCancelled:
        raise
    except (TimeoutError, socket.timeout) as exc:
        if abort.cancelled:
            raise RequestCancelled("Request cancelled") from exc
        raise RuntimeError(f"Connection failed: {exc}") from exc
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        if abort.cancelled:
            raise RequestCancelled("Request cancelled") from exc
        raise RuntimeError(f"Connection failed: {exc}") from exc
    finally:
        try:
            connection.close()
        except Exception:
            pass
        abort.clear()


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
    *,
    abort: AbortHandle | None = None,
) -> dict[str, Any]:
    """POST JSON with hard cross-thread cancellation.

    The real socket work is performed by a daemon helper thread.  This lets the
    caller return immediately after ``abort.cancel()`` even in the exceptional
    case where OS DNS/connect teardown itself takes longer to unwind.
    """
    handle = abort or AbortHandle()
    handle.check()
    results: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            value = _blocking_post_json(url, payload, headers, timeout, handle)
        except BaseException as exc:  # forwarded verbatim to the owning thread
            try:
                results.put_nowait(("error", exc))
            except queue.Full:
                pass
        else:
            try:
                results.put_nowait(("ok", value))
            except queue.Full:
                pass

    thread = threading.Thread(target=worker, name="LuaS30-AI-HTTP", daemon=True)
    thread.start()

    # Polling is intentionally short: AbortHandle.cancel() closes the socket,
    # while this loop guarantees the owner observes cancellation immediately
    # even if a platform-level DNS call has not returned yet.
    while True:
        if handle.cancelled:
            raise RequestCancelled("Request cancelled")
        try:
            kind, value = results.get(timeout=0.025)
        except queue.Empty:
            continue
        if kind == "ok":
            return value  # type: ignore[return-value]
        if isinstance(value, BaseException):
            raise value
        raise RuntimeError(str(value))

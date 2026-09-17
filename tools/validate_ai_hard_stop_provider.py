from __future__ import annotations

import importlib.util
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSPORT = ROOT / "studio/app/services/cancellable_http.py"
PROVIDER = ROOT / "studio/app/services/ai_provider_service.py"
CHAT = ROOT / "studio/app/views/ai_chat_view.py"

spec = importlib.util.spec_from_file_location("luas30_cancellable_http", TRANSPORT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
AbortHandle = module.AbortHandle
RequestCancelled = module.RequestCancelled
post_json = module.post_json

provider_text = PROVIDER.read_text(encoding="utf-8")
chat_text = CHAT.read_text(encoding="utf-8")
transport_text = TRANSPORT.read_text(encoding="utf-8")

for token in (
    "self._abort_handle = AbortHandle()",
    "def abort(self) -> None:",
    "self._abort_handle.cancel()",
    "abort_handle=self._abort_handle",
    "except RequestCancelled:",
):
    assert token in provider_text, token

for token in (
    "worker.abort()",
    "Hard stop: request interruption AND close the active provider",
):
    assert token in chat_text, token

for token in (
    "sock.shutdown(socket.SHUT_RDWR)",
    "connection.close()",
    "threading.Thread(target=worker",
    "if handle.cancelled:",
):
    assert token in transport_text, token

received = threading.Event()
disconnected = threading.Event()
server_release = threading.Event()


class SlowHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        received.set()

        # Once LuaS30 cancels, the client side shutdown/close should make this
        # server-side recv return b'' instead of waiting for the provider reply.
        try:
            self.connection.settimeout(1.5)
            value = self.connection.recv(1)
            if value == b"":
                disconnected.set()
        except OSError:
            disconnected.set()

        server_release.wait(1.0)
        body = json.dumps({"output_text": "late response"}).encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            pass

    def log_message(self, fmt: str, *args: object) -> None:
        return


server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()

handle = AbortHandle()
finished = threading.Event()
result: dict[str, object] = {}


def request_worker() -> None:
    try:
        post_json(
            f"http://127.0.0.1:{server.server_port}/slow",
            {"hello": "world"},
            {},
            30,
            abort=handle,
        )
    except BaseException as exc:
        result["error"] = exc
    else:
        result["value"] = "unexpected success"
    finally:
        finished.set()


caller = threading.Thread(target=request_worker)
caller.start()
assert received.wait(2.0), "slow test server did not receive the provider request"

started = time.perf_counter()
handle.cancel()
assert finished.wait(0.75), "caller did not return promptly after hard cancel"
elapsed = time.perf_counter() - started
assert isinstance(result.get("error"), RequestCancelled), repr(result)
assert elapsed < 0.75, elapsed
assert disconnected.wait(1.0), "server did not observe the client transport closing"

server_release.set()
server.shutdown()
server.server_close()
caller.join(timeout=1.0)

print(f"PASS: provider transport abort returned in {elapsed * 1000:.1f} ms")
print("PASS: active HTTP socket was shut down and closed")
print("PASS: AIRequestThread exposes hard abort and suppresses cancelled responses")
print("PASS: Chat Stop calls provider hard abort instead of interruption-only cancellation")

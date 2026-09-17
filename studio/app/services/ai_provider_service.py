from __future__ import annotations

import json
import os
import urllib.parse
from dataclasses import dataclass, asdict

from PySide6.QtCore import QThread, Signal

from app.core.paths import config_dir
from app.services.cancellable_http import AbortHandle, RequestCancelled, post_json

PROVIDER_DEFAULTS = {
    "openai": {"label":"OpenAI","model":"gpt-5.6-luna","base_url":"https://api.openai.com/v1","env":"OPENAI_API_KEY"},
    "anthropic": {"label":"Anthropic","model":"claude-sonnet-4-6","base_url":"https://api.anthropic.com","env":"ANTHROPIC_API_KEY"},
    "gemini": {"label":"Google Gemini","model":"gemini-3.5-flash","base_url":"https://generativelanguage.googleapis.com/v1beta","env":"GEMINI_API_KEY"},
    "openai_compatible": {"label":"OpenAI Compatible","model":"model","base_url":"http://127.0.0.1:8000/v1","env":"LUAS30_AI_API_KEY"},
    "ollama": {"label":"Ollama Local","model":"qwen3-coder","base_url":"http://127.0.0.1:11434","env":""},
}

@dataclass
class ProviderConfig:
    provider: str = "openai"
    model: str = ""
    base_url: str = ""
    timeout: int = 120
    enable_shell: bool = True
    enable_code_edits: bool = True
    show_reasoning: bool = True

    @classmethod
    def defaults(cls, provider: str) -> "ProviderConfig":
        provider = provider if provider in PROVIDER_DEFAULTS else "openai"
        d = PROVIDER_DEFAULTS[provider]
        return cls(
            provider=provider,
            model=d["model"],
            base_url=d["base_url"],
            timeout=120,
            enable_shell=True,
            enable_code_edits=True,
            show_reasoning=True,
        )

class AIProviderConfigStore:
    """Persist only non-secret provider/model/URL preferences."""
    def __init__(self) -> None:
        self.path = config_dir()/"ai_providers.json"

    def load(self) -> ProviderConfig:
        if not self.path.is_file():
            return ProviderConfig.defaults("openai")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return ProviderConfig.defaults("openai")
        provider = str(data.get("provider") or "openai")
        default = ProviderConfig.defaults(provider)
        return ProviderConfig(
            provider=provider if provider in PROVIDER_DEFAULTS else "openai",
            model=str(data.get("model") or default.model),
            base_url=str(data.get("base_url") or default.base_url),
            timeout=max(10,min(600,int(data.get("timeout",120) or 120))),
            enable_shell=bool(data.get("enable_shell", True)),
            enable_code_edits=bool(data.get("enable_code_edits", True)),
            show_reasoning=bool(data.get("show_reasoning", True)),
        )

    def save(self, cfg: ProviderConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(cfg),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        tmp.replace(self.path)

def environment_key(provider: str) -> str:
    name = PROVIDER_DEFAULTS.get(provider,{}).get("env","")
    return os.environ.get(name,"") if name else ""

def _request_json(
    url: str,
    payload: dict,
    headers: dict[str,str],
    timeout: int,
    *,
    abort_handle: AbortHandle | None = None,
) -> dict:
    return post_json(
        url,
        payload,
        headers,
        timeout,
        abort=abort_handle,
    )

def _openai_text(data: dict) -> str:
    if isinstance(data.get("output_text"),str):
        return data["output_text"]
    out=[]
    for item in data.get("output",[]) or []:
        if isinstance(item,dict):
            for content in item.get("content",[]) or []:
                if isinstance(content,dict) and isinstance(content.get("text"),str):
                    out.append(content["text"])
    return "\n".join(out).strip()

def _anthropic_text(data: dict) -> str:
    return "\n".join(
        b.get("text","") for b in data.get("content",[]) or []
        if isinstance(b,dict) and isinstance(b.get("text"),str)
    ).strip()

def _gemini_text(data: dict) -> str:
    result=[]
    for candidate in data.get("candidates",[]) or []:
        content = candidate.get("content",{}) if isinstance(candidate,dict) else {}
        for part in content.get("parts",[]) or []:
            if isinstance(part,dict) and isinstance(part.get("text"),str):
                result.append(part["text"])
    return "\n".join(result).strip()

def _compatible_text(data: dict) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError,IndexError,TypeError):
        return ""
    if isinstance(content,str):
        return content
    if isinstance(content,list):
        return "\n".join(x.get("text","") for x in content if isinstance(x,dict)).strip()
    return ""

def call_provider(
    cfg: ProviderConfig,
    *,
    api_key: str,
    system_prompt: str,
    messages: list[dict[str,str]],
    abort_handle: AbortHandle | None = None,
) -> str:
    provider, base, model = cfg.provider, cfg.base_url.rstrip("/"), cfg.model.strip()
    if not model:
        raise RuntimeError("Model name is empty.")

    if provider == "openai":
        key = api_key or environment_key(provider)
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set and no session API key was provided.")
        data = _request_json(
            base+"/responses",
            {"model":model,"instructions":system_prompt,"input":[{"role":m["role"],"content":m["content"]} for m in messages]},
            {"Authorization":f"Bearer {key}"},
            cfg.timeout,
            abort_handle=abort_handle,
        )
        text = _openai_text(data)
    elif provider == "anthropic":
        key = api_key or environment_key(provider)
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set and no session API key was provided.")
        data = _request_json(
            base+"/v1/messages",
            {"model":model,"max_tokens":8192,"system":system_prompt,
             "messages":[{"role":m["role"],"content":m["content"]} for m in messages if m["role"] in {"user","assistant"}]},
            {"x-api-key":key,"anthropic-version":"2023-06-01"},
            cfg.timeout,
            abort_handle=abort_handle,
        )
        text = _anthropic_text(data)
    elif provider == "gemini":
        key = api_key or environment_key(provider)
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set and no session API key was provided.")
        model_path = model if model.startswith("models/") else "models/"+model
        data = _request_json(
            base+"/"+urllib.parse.quote(model_path,safe="/")+":generateContent",
            {
                "systemInstruction":{"parts":[{"text":system_prompt}]},
                "contents":[
                    {"role":"model" if m["role"]=="assistant" else "user","parts":[{"text":m["content"]}]}
                    for m in messages
                ],
            },
            {"x-goog-api-key":key},
            cfg.timeout,
            abort_handle=abort_handle,
        )
        text = _gemini_text(data)
    elif provider == "openai_compatible":
        key = api_key or environment_key(provider)
        headers = {"Authorization":f"Bearer {key}"} if key else {}
        data = _request_json(
            base+"/chat/completions",
            {"model":model,"messages":[{"role":"system","content":system_prompt},*messages]},
            headers,
            cfg.timeout,
            abort_handle=abort_handle,
        )
        text = _compatible_text(data)
    elif provider == "ollama":
        data = _request_json(
            base+"/api/chat",
            {"model":model,"stream":False,"messages":[{"role":"system","content":system_prompt},*messages]},
            {},
            cfg.timeout,
            abort_handle=abort_handle,
        )
        message = data.get("message",{})
        text = str(message.get("content","") if isinstance(message,dict) else "").strip()
    else:
        raise RuntimeError(f"Unknown AI provider: {provider}")

    if not text:
        raise RuntimeError("Provider returned no text response.")
    return text

class AIRequestThread(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self,cfg:ProviderConfig,api_key:str,system_prompt:str,messages:list[dict[str,str]],parent=None)->None:
        super().__init__(parent)
        self.cfg,self.api_key,self.system_prompt,self.messages=cfg,api_key,system_prompt,list(messages)
        self._abort_handle = AbortHandle()

    def abort(self) -> None:
        """Hard-stop the active provider HTTP transport from the UI thread."""
        self.requestInterruption()
        self._abort_handle.cancel()

    def run(self)->None:
        if self.isInterruptionRequested():
            return
        try:
            value=call_provider(
                self.cfg,
                api_key=self.api_key,
                system_prompt=self.system_prompt,
                messages=self.messages,
                abort_handle=self._abort_handle,
            )
        except RequestCancelled:
            return
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        if not self.isInterruptionRequested():
            self.completed.emit(value)



def test_provider_connection(cfg: ProviderConfig, api_key: str = "") -> str:
    """Perform a minimal real provider request and return a short status string."""
    reply = call_provider(
        cfg,
        api_key=api_key,
        system_prompt=(
            "This is a LuaS30 provider connection test. Reply with only the word OK."
        ),
        messages=[{"role": "user", "content": "Connection test"}],
    )
    value = " ".join(str(reply).strip().split())
    return value[:80] or "OK"


class AIConnectionTestThread(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, cfg: ProviderConfig, api_key: str = "", parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.api_key = api_key

    def run(self) -> None:
        try:
            message = test_provider_connection(self.cfg, self.api_key)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(message)

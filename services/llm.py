# -*- coding: utf-8 -*-
"""
LLM 服务：从 config.providers 读取服务商列表，按 provider_id + model 调用。
"""
import json
import requests
from flask import current_app


def _get_config():
    return current_app.config["CONFIG_LOADER"]()


def get_available_models():
    """返回 config 中的 providers 列表（id, name, models）"""
    cfg = _get_config()
    providers = cfg.get("providers") or []
    if not isinstance(providers, list):
        providers = []
    out = []
    for p in providers:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if not pid:
            continue
        models = p.get("models")
        if not isinstance(models, list):
            models = [p.get("model")] if p.get("model") else []
        models = [str(m).strip() for m in models if m]
        out.append({
            "id": pid,
            "name": p.get("name") or pid,
            "models": models or ["default"],
        })
    return out


def _openai_style_chat(api_base: str, api_key: str, model: str, messages: list, stream: bool = False):
    """OpenAI 兼容接口；stream=True 时 yield content 块"""
    url = (api_base.rstrip("/") + "/v1/chat/completions") if api_base else ""
    if not url:
        if stream:
            yield "请先在后台配置该服务商的 API 地址与 Key。"
        else:
            return {"choices": [{"message": {"content": "请先在后台配置该服务商的 API 地址与 Key。"}}]}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "stream": stream}
    if stream:
        r = requests.post(url, json=payload, headers=headers, timeout=120, stream=True)
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.strip():
                continue
            if line.startswith("data: "):
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    delta = (obj.get("choices") or [{}])[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    pass
        return
    r = requests.post(url, json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()


def _get_provider_config(provider_id: str):
    """从 config.providers 中按 id 查找，返回 (api_base, api_key)"""
    cfg = _get_config()
    providers = cfg.get("providers") or []
    for p in providers:
        if isinstance(p, dict) and p.get("id") == provider_id:
            return (p.get("api_base") or "", p.get("api_key") or "")
    return ("", "")


def chat_completion(provider_id: str, model: str, messages: list) -> dict:
    """按服务商 id + 模型名调用"""
    api_base, api_key = _get_provider_config(provider_id)
    return _openai_style_chat(api_base, api_key, model, messages, stream=False)


def chat_completion_stream(provider_id: str, model: str, messages: list):
    """流式调用，yield 每个 content 块"""
    api_base, api_key = _get_provider_config(provider_id)
    yield from _openai_style_chat(api_base, api_key, model, messages, stream=True)

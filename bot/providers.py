# -*- coding: utf-8 -*-
"""Translation back-ends for /chapter: local Ollama or a hosted OpenAI-compatible API.

API keys come ONLY from the bot's environment (never from a Discord command, never logged).
"""
from __future__ import annotations

import os
from typing import Dict, Optional

# name -> (OpenAI-compatible base url, default model, env var holding the key)
API_PROVIDERS: Dict[str, Dict[str, str]] = {
    "gemini": {"base": "https://generativelanguage.googleapis.com/v1beta/openai",
               "model": "gemini-3.6-flash", "env": "GEMINI_API_KEY"},
    "openai": {"base": "https://api.openai.com/v1", "model": "gpt-4o-mini", "env": "OPENAI_API_KEY"},
    "deepseek": {"base": "https://api.deepseek.com", "model": "deepseek-chat", "env": "DEEPSEEK_API_KEY"},
    "groq": {"base": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile",
             "env": "GROQ_API_KEY"},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "model": "google/gemini-3.8-flash",
                   "env": "OPENROUTER_API_KEY"},
    "xai": {"base": "https://api.x.ai/v1", "model": "grok-2-latest", "env": "XAI_API_KEY"},
    "together": {"base": "https://api.together.xyz/v1",
                 "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "env": "TOGETHER_API_KEY"},
}
PROVIDER_CHOICES = ("ollama",) + tuple(API_PROVIDERS)
KEY_ENV_NAMES = tuple(sorted({p["env"] for p in API_PROVIDERS.values()}))


def api_key(provider: str) -> str:
    p = API_PROVIDERS.get(provider)
    return os.environ.get(p["env"], "").strip() if p else ""


def available(provider: str) -> bool:
    """ollama is always selectable (reachability is checked at run time); APIs need a key."""
    return provider == "ollama" or bool(api_key(provider))


def missing_key_message(provider: str) -> Optional[str]:
    if available(provider):
        return None
    env = API_PROVIDERS[provider]["env"]
    return f"موفر `{provider}` غير مفعّل على السيرفر: ضع المفتاح في متغير البيئة `{env}` ثم أعد تشغيل البوت."

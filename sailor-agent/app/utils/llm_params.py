from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


_ALLOWED_LLM_KEYS = {
    # model
    "model_name",
    "temperature",
    "max_tokens",
    "streaming",
    "n",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "stop",
    "seed",
    # openai client
    "openai_api_key",
    "openai_api_base",
    "openai_organization",
    "openai_project",
    # transport / retry / timeout
    "request_timeout",
    "timeout",
    "max_retries",
    "proxies",
    "transport",
    "limits",
    "verify_ssl",
    # passthrough
    "default_headers",
    "default_query",
    "model_kwargs",
}


def merge_llm_params(
    base: Mapping[str, Any],
    override: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """
    合并并规整 LLM 参数：
    - 兼容 override.name -> model_name
    - 仅保留白名单字段，避免 `id` 等杂项参数透传导致 OpenAI SDK 报错
    """
    out: Dict[str, Any] = dict(base or {})
    ov: Dict[str, Any] = dict(override or {})

    if ov.get("name") and not ov.get("model_name"):
        ov["model_name"] = ov.get("name")

    for k, v in ov.items():
        if k in _ALLOWED_LLM_KEYS:
            out[k] = v

    return out


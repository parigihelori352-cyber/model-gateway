"""Unified model client — provider routing, reasoning, multimodal

All tool-specific logic lives in config.json. This client is pure
plumbing: resolve provider → build messages → call API → return response.
"""
import json
from openai import OpenAI


class ModelGatewayClient:
    """Thin layer over OpenAI SDK. Routes calls to the right provider,
    builds multimodal or text messages based on capability config,
    handles reasoning params, and returns a uniform response dict."""

    def __init__(self, config: dict):
        self.cfg = config
        self._clients: dict[str, OpenAI] = {}

    # ── Provider resolution ───────────────────────────────────────────────

    def _get_client(self, provider_name: str) -> OpenAI:
        """Lazy-init and cache OpenAI client per provider."""
        if provider_name not in self._clients:
            provider = self.cfg.get("providers", {}).get(provider_name, {})
            api_key = provider.get("api_key", "")
            if not api_key:
                env_var = provider.get("api_key_env", "")
                raise RuntimeError(
                    f"API key not set for provider '{provider_name}'. "
                    f"Set the {env_var} environment variable."
                )

            client_kwargs = {
                "base_url": provider["base_url"],
                "api_key": api_key,
            }
            # Optional headers (e.g. OpenRouter leaderboard)
            headers = provider.get("headers", {})
            if headers:
                client_kwargs["default_headers"] = headers

            self._clients[provider_name] = OpenAI(**client_kwargs)
        return self._clients[provider_name]

    # ── Message building ──────────────────────────────────────────────────

    def _build_messages(
        self, capability: dict, arguments: dict
    ) -> list[dict]:
        """Build the messages array for the API call.

        - Image capabilities: multimodal content array (image_url + text)
        - Text capabilities: system prompt + serialized user args
        """
        system_prompt = self._resolve_template(
            capability.get("system_prompt", ""), arguments
        )

        if capability.get("accepts_images"):
            return self._build_image_messages(system_prompt, arguments)
        else:
            return self._build_text_messages(system_prompt, arguments)

    def _build_image_messages(
        self, system_prompt: str, arguments: dict
    ) -> list[dict]:
        """Build multimodal messages for vision capabilities."""
        from .core import is_url, is_data_url, encode_to_data_url

        content: list[dict] = []

        images = arguments.get("images", [])
        for img in images:
            if is_url(img) or is_data_url(img):
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img},
                })
            else:
                data_url = encode_to_data_url(img)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": data_url},
                })

        content.append({"type": "text", "text": arguments.get("prompt", "")})

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

    def _build_text_messages(
        self, system_prompt: str, arguments: dict
    ) -> list[dict]:
        """Build text-only messages from capability arguments.

        Strips meta-params (provider, model, budget, reasoning_effort)
        from the user message — those are for routing, not content.
        """
        meta_keys = {"provider", "model", "budget", "reasoning_effort"}
        user_args = {k: v for k, v in arguments.items() if k not in meta_keys}

        # If only one meaningful content key, use its value directly
        if len(user_args) == 1:
            user_msg = list(user_args.values())[0]
            if isinstance(user_msg, list):
                user_msg = "\n".join(f"- {item}" for item in user_msg)
        else:
            user_msg = json.dumps(user_args, ensure_ascii=False, indent=2)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(user_msg)},
        ]

    def _resolve_template(self, template: str, arguments: dict) -> str:
        """Replace {key} placeholders in template with argument values."""
        result = template
        for key, value in arguments.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    # ── Core call ─────────────────────────────────────────────────────────

    def call(self, capability: dict, arguments: dict) -> dict:
        """Execute a capability against the configured provider/model.

        Args:
            capability: A capability dict from config.json (has provider, model,
                        system_prompt, reasoning, etc.)
            arguments: User-supplied arguments for this call. May override
                       provider, model, and reasoning_effort.

        Returns:
            dict with {text, model, usage}. usage may include reasoning_tokens.
        """
        # Resolve provider
        provider_name = arguments.get("provider", capability.get("provider", "openrouter"))

        # Resolve model (budget overrides explicit model)
        model = None
        if "budget" in arguments and arguments["budget"]:
            from .config import get_model_for_budget
            model = get_model_for_budget(self.cfg, arguments["budget"])
        model = arguments.get("model", model or capability.get("model"))

        client = self._get_client(provider_name)
        messages = self._build_messages(capability, arguments)

        max_tokens = capability.get("max_output_tokens", 4096)

        # Reasoning params
        extra_body = {}
        reasoning_cfg = capability.get("reasoning", {})
        if reasoning_cfg.get("enabled"):
            effort = arguments.get(
                "reasoning_effort",
                reasoning_cfg.get("default_effort", "medium"),
            )
            extra_body["reasoning"] = {"enabled": True, "effort": effort}

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            extra_body=extra_body if extra_body else None,
            stream=False,
        )

        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        rt = getattr(response.usage, "reasoning_tokens", None)
        if rt is None:
            rt = getattr(response.usage, "reasoningTokens", None)
        if rt is not None:
            usage["reasoning_tokens"] = rt

        return {
            "text": response.choices[0].message.content,
            "model": response.model,
            "usage": usage,
        }

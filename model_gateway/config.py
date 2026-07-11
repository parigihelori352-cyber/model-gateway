"""Configuration loader — reads config.json + env var overrides

Env var naming convention: <API_KEY_ENV> for each provider.
The api_key_env field in each provider definition tells us which env var to read.
"""
import json
import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "config.json"
EXAMPLE_CONFIG_PATH = PACKAGE_ROOT / "config.example.json"


def resolve_config_path(config_path: str | None = None) -> Path:
    """Find configuration without tying users to a particular checkout path.

    Priority: explicit argument, MODEL_GATEWAY_CONFIG, config.json in the
    current directory, then config.json next to an editable checkout.
    """
    if config_path:
        return Path(config_path).expanduser()
    if env_path := os.environ.get("MODEL_GATEWAY_CONFIG"):
        return Path(env_path).expanduser()
    working_copy = Path.cwd() / "config.json"
    if working_copy.exists():
        return working_copy
    return DEFAULT_CONFIG_PATH


def load(config_path: str | None = None) -> dict:
    """Load full config with env var injection for provider API keys."""
    path = resolve_config_path(config_path)

    cfg = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    # Inject API keys from env vars for each provider
    for name, provider in cfg.get("providers", {}).items():
        env_var = provider.get("api_key_env", "")
        if env_var and os.environ.get(env_var):
            provider["api_key"] = os.environ[env_var]

    return cfg


def save(cfg: dict, config_path: str | None = None):
    """Save config to file (strips injected API keys before saving)."""
    path = resolve_config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = json.loads(json.dumps(cfg))
    for provider in clean.get("providers", {}).values():
        provider.pop("api_key", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)


def get_provider(cfg: dict, name: str) -> dict:
    """Get a provider config by name, with API key injected."""
    provider = cfg.get("providers", {}).get(name, {})
    if not provider.get("api_key"):
        env_var = provider.get("api_key_env", "")
        if env_var and os.environ.get(env_var):
            provider = dict(provider)
            provider["api_key"] = os.environ[env_var]
    return provider


def get_capability(cfg: dict, tool_name: str) -> dict | None:
    """Find a capability definition by tool name."""
    for cap in cfg.get("capabilities", []):
        if cap["tool"] == tool_name:
            return cap
    return None


def get_model_for_budget(cfg: dict, budget: str) -> str:
    """Resolve budget string to a model ID."""
    budget_models = cfg.get("budget_models", {
        "low": "openai/gpt-4o-mini",
        "medium": "openai/gpt-4o",
        "high": "openai/gpt-5.4",
    })
    return budget_models.get(budget, "openai/gpt-5.4")

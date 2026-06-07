from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_URL_KEY = "API_IMAGE_BASE_URL"
API_KEY_KEY = "API_IMAGE_API_KEY"


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str
    base_url: str


def load_provider_config(
    env_file: Path,
    base_url_override: str | None = None,
    api_key_override: str | None = None,
    api_key_env: str | None = None,
) -> ProviderConfig:
    needs_env_file = base_url_override is None or (api_key_override is None and api_key_env is None)
    env_values = load_env_file(env_file, required=needs_env_file)
    api_key = resolve_api_key(api_key_override, api_key_env, env_values, env_file)
    base_url = resolve_base_url(base_url_override, env_values, env_file)
    return ProviderConfig(api_key=api_key, base_url=normalize_base_url(base_url))


def load_env_file(path: Path, required: bool) -> dict[str, str]:
    if not path.exists():
        if not required:
            return {}
        raise FileNotFoundError(
            f"Missing provider .env file: {path}. "
            f"Create it with {BASE_URL_KEY}=https://provider.example/v1 and {API_KEY_KEY}=your_key."
        )
    if not path.is_file():
        raise ValueError(f"Provider .env path is not a file: {path}")

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise ValueError(f"Invalid .env line {line_number} in {path}: expected KEY=value.")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid .env line {line_number} in {path}: key is empty.")
        values[key] = strip_optional_quotes(value.strip())
    return values


def strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def resolve_base_url(base_url_override: str | None, env_values: dict[str, str], env_file: Path) -> str:
    if base_url_override:
        return base_url_override
    file_base_url = env_values.get(BASE_URL_KEY, "").strip()
    if file_base_url:
        return file_base_url
    raise ValueError(f"{BASE_URL_KEY} is missing in {env_file}.")


def resolve_api_key(
    api_key_override: str | None,
    api_key_env: str | None,
    env_values: dict[str, str],
    env_file: Path,
) -> str:
    if api_key_override and api_key_env:
        raise ValueError("Use only one of --api-key or --api-key-env.")
    if api_key_override:
        api_key = api_key_override.strip()
        if not api_key:
            raise ValueError("--api-key must not be empty.")
        return api_key
    if api_key_env:
        env_name = api_key_env.strip()
        if not env_name:
            raise ValueError("--api-key-env must name a non-empty environment variable.")
        api_key = os.environ.get(env_name, "").strip()
        if not api_key:
            raise ValueError(f"Environment variable '{env_name}' is empty or not set.")
        return api_key
    api_key = env_values.get(API_KEY_KEY, "").strip()
    if api_key:
        return api_key
    raise ValueError(f"{API_KEY_KEY} is missing in {env_file}.")


def normalize_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise ValueError("--base-url must not be empty.")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError("--base-url must start with http:// or https://.")
    return normalized

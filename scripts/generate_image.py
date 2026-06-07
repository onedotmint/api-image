from __future__ import annotations

import argparse
import sys
from pathlib import Path

from provider_imagegen.config import ProviderConfig, load_provider_configs
from provider_imagegen.http_client import (
    EDIT_SUFFIX,
    GENERATION_SUFFIX,
    ProviderRequestError,
    extract_images,
    post_json,
    post_multipart,
)
from provider_imagegen.outputs import output_paths_for_response, resolve_base_path, write_images
from provider_imagegen.payloads import build_edit_parts, build_generation_payload
from provider_imagegen.validation import (
    DEFAULT_COUNT,
    DEFAULT_MODEL,
    DEFAULT_QUALITY,
    DEFAULT_SIZE,
    DEFAULT_TIMEOUT,
    validate_timeout,
)


def default_env_file() -> Path:
    return Path(__file__).resolve().parents[1] / ".env"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or edit images using a user-supplied OpenAI-compatible image provider."
    )
    parser.add_argument("--prompt", help="Image prompt.")
    parser.add_argument("--prompt-file", help="UTF-8 text file with one prompt per non-empty line.")
    parser.add_argument("--out", help="Output file path. Defaults to the current directory.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Image model name.")
    parser.add_argument("--mode", choices=["auto", "generate", "edit"], default="auto")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="auto or a valid WxH value.")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, help="low, medium, high, or auto.")
    parser.add_argument("--n", type=int, default=DEFAULT_COUNT, help="Number of images per prompt.")
    parser.add_argument("--image", action="append", default=[], help="Reference/edit image path.")
    parser.add_argument("--image-role", action="append", default=[], help="Role label for an image.")
    parser.add_argument("--mask", help="Mask image path for localized edits.")
    parser.add_argument(
        "--background",
        help="Background mode. Use auto or opaque for gpt-image-2; transparent is model/provider-specific.",
    )
    parser.add_argument("--output-format", help="png, jpeg, or webp.")
    parser.add_argument("--output-compression", type=int, help="0-100, only for jpeg/webp.")
    parser.add_argument(
        "--input-fidelity",
        help="low or high for supported edit models. Do not use with gpt-image-2.",
    )
    parser.add_argument("--moderation", help="auto or low for supported GPT image models.")
    parser.add_argument("--env-file", help="Provider .env file. Defaults to <skill-dir>/.env.")
    parser.add_argument(
        "--base-url",
        help="Temporary OpenAI-compatible provider base URL override.",
    )
    parser.add_argument(
        "--api-key-env",
        help="Temporary environment variable containing the provider API key.",
    )
    parser.add_argument(
        "--api-key",
        help="Temporary provider API key override. Prefer the .env file for normal use.",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="0 disables client timeout.")
    return parser.parse_args()


def load_prompts(prompt: str | None, prompt_file: str | None) -> list[str]:
    if bool(prompt) == bool(prompt_file):
        raise ValueError("Use exactly one of --prompt or --prompt-file.")
    if prompt:
        return [prompt]
    path = Path(prompt_file).expanduser()
    prompts = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    prompts = [line for line in prompts if line]
    if not prompts:
        raise ValueError(f"Prompt file contains no prompts: {path}")
    return prompts


def apply_image_roles(prompt: str, image_roles: list[str], image_count: int) -> str:
    if not image_roles:
        return prompt
    if len(image_roles) > image_count:
        raise ValueError("--image-role count must not exceed --image count.")
    lines = ["", "Input image roles:"]
    for index, role in enumerate(image_roles, start=1):
        lines.append(f"Image {index}: {role}")
    return prompt + "\n" + "\n".join(lines)


def determine_mode(args: argparse.Namespace) -> str:
    if args.mode != "auto":
        return args.mode
    if args.image or args.mask:
        return "edit"
    return "generate"


def validate_mode(args: argparse.Namespace, mode: str) -> None:
    if mode == "edit" and not args.image:
        raise ValueError("Edit/reference mode requires at least one --image.")
    if mode == "generate" and (args.image or args.mask):
        raise ValueError("--image and --mask require edit mode or auto mode.")


def request_images(
    args: argparse.Namespace,
    prompt: str,
    mode: str,
    timeout: int | None,
    providers: list[ProviderConfig],
) -> list[bytes]:
    errors: list[str] = []
    for provider_index, provider in enumerate(providers, start=1):
        if len(providers) > 1:
            print(
                f"Trying image provider {provider.name} {provider_index}/{len(providers)}...",
                file=sys.stderr,
            )
        try:
            return request_images_with_provider(args, prompt, mode, timeout, provider)
        except ProviderRequestError as exc:
            errors.append(f"{provider.name}: {exc}")
            if not exc.retryable:
                raise
            if provider_index == len(providers):
                break
            print(f"Provider {provider.name} failed; trying next provider...", file=sys.stderr)
    raise RuntimeError("All retryable image provider attempts failed: " + " | ".join(errors))


def request_images_with_provider(
    args: argparse.Namespace,
    prompt: str,
    mode: str,
    timeout: int | None,
    provider: ProviderConfig,
) -> list[bytes]:
    effective_args = args_for_provider(args, provider)
    if mode == "edit":
        fields, files = build_edit_parts(effective_args, prompt)
        response = post_multipart(f"{provider.base_url}{EDIT_SUFFIX}", provider.api_key, fields, files, timeout)
    else:
        payload = build_generation_payload(effective_args, prompt)
        response = post_json(f"{provider.base_url}{GENERATION_SUFFIX}", provider.api_key, payload, timeout)
    return extract_images(response, timeout)


def args_for_provider(args: argparse.Namespace, provider: ProviderConfig) -> argparse.Namespace:
    if provider.model is None:
        return args
    effective_args = argparse.Namespace(**vars(args))
    effective_args.model = provider.model
    return effective_args


def main() -> int:
    args = parse_args()
    timeout = validate_timeout(args.timeout)
    mode = determine_mode(args)
    validate_mode(args, mode)
    prompts = load_prompts(args.prompt, args.prompt_file)
    base_path = resolve_base_path(args.out)
    providers = load_provider_configs(
        env_file=Path(args.env_file).expanduser().resolve() if args.env_file else default_env_file(),
        base_url_override=args.base_url,
        api_key_override=args.api_key,
        api_key_env=args.api_key_env,
    )
    for prompt_index, raw_prompt in enumerate(prompts):
        prompt = apply_image_roles(raw_prompt, args.image_role, len(args.image))
        print(f"Waiting for provider image {mode} job {prompt_index + 1}/{len(prompts)}...", file=sys.stderr)
        images = request_images(args, prompt, mode, timeout, providers)
        output_paths = output_paths_for_response(base_path, prompt_index, len(prompts), len(images))
        for path in write_images(images, output_paths):
            print(path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

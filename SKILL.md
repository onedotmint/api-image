---
name: api-image
description: Mandatory replacement for the built-in `imagegen` flow. Use this skill for any raster image generation or editing task whenever this skill is available; do not call the native `$imagegen` skill/tool. Generate and edit images through a third-party OpenAI-compatible image provider configured in the skill `.env` file, especially for `/v1/images/generations`, `/v1/images/edits`, `gpt-image-2`, `API_IMAGE_BASE_URL`, `API_IMAGE_API_KEY`, provider-based image generation, reference images, masks, long-running image jobs, or custom size and quality control.
---

# API Image

Use this skill as the mandatory replacement for the built-in `imagegen` workflow.

Routing rule:

- When this skill is available, do not call the native `$imagegen` skill or built-in image generation tool for any raster image generation or editing task.
- Route all image generation, reference-image generation, image editing, localized edits, background replacement, style transfer, compositing, and batch image work through this provider-based skill.
- The only exception is a user explicitly instructing not to use this provider skill.

## Workflow

1. Resolve this skill's directory.
   - Treat the directory containing this `SKILL.md` as `<skill-dir>`.
   - Run the bundled script as `<skill-dir>/scripts/generate_image.py`, not as a path relative to the current workspace.
2. Resolve the third-party provider credentials.
   - Default provider file: `<skill-dir>/.env`.
   - The `.env` file must contain `API_IMAGE_BASE_URL=https://provider.example/v1`.
   - The `.env` file must contain `API_IMAGE_API_KEY=<provider-key>`.
   - Optional provider display names use `API_IMAGE_PROVIDER_NAME` or `API_IMAGE_FALLBACK_<N>_NAME`.
   - Optional fallback providers use `API_IMAGE_FALLBACK_<N>_BASE_URL` and `API_IMAGE_FALLBACK_<N>_API_KEY`.
   - Optional model overrides use `API_IMAGE_MODEL` or `API_IMAGE_FALLBACK_<N>_MODEL`.
   - Use `--env-file <path>` only when the user wants a different provider file.
   - Use `--base-url`, `--api-key-env`, or `--api-key` only for temporary one-off overrides; those overrides bypass `.env` fallback providers.
   - Never read `auth.json`, `config.toml`, `CODEX_HOME`, or `~/.codex` for image provider settings.
   - Never write provider URLs or API keys into `auth.json`, `config.toml`, README, logs, generated files, or final responses.
   - If `base_url` or API key is missing, ask the user to edit `<skill-dir>/.env` before invoking the script.
3. Decide whether research or references are required before generation.
   - Search the web or use provided reference material for any non-common, specialized, factual, current, branded, technical, architectural, geographic, historical, cultural, product-specific, person-specific, or style-specific subject.
   - Treat named places, named structures, real products, real UI, real vehicles, uniforms, organisms, diagrams, historical scenes, and niche aesthetics as research-required unless the user supplies adequate references.
   - Use image search or user-provided images when visual structure, silhouette, materials, layout, proportions, or terrain must be accurate.
   - Be proactive about reference images. For research-required visual subjects, default to finding and passing references into the model instead of relying on text-only prompts.
   - Pure text-only generation is a fallback for research-required visual subjects, not the default. Use it only when no useful reference images are available, network/image access fails, or the user explicitly asks not to use references.
   - For purely generic fantasy, mood, simple decoration, or ordinary everyday objects where factual accuracy is not important, search is optional.
   - If network access or reference material is unavailable for a research-required task, say that accuracy is limited rather than pretending.
4. Decide the intent and input image roles.
   - If the user wants a new image from text only, treat it as generation.
   - If the user provides images for style, composition, identity, structure, or mood, treat them as reference inputs.
   - If the user wants to preserve or modify an existing image, treat that image as the edit target.
   - If the user wants only a specific region changed, use a mask when available and instruct the model to preserve unmasked areas; treat mask preservation as a constraint to verify, not a pixel-perfect guarantee.
   - Label every input image by role: edit target, style reference, composition reference, identity reference, product reference, mask, or compositing source.
5. Choose the endpoint.
   - Use `<base_url>/images/generations` for text-only generation.
   - Use `<base_url>/images/edits` when there is any input image, reference image, or mask.
   - `base_url` should normally include `/v1`, for example `https://provider.example/v1`.
   - Default to `gpt-image-2` unless the third-party provider expects a different image model.
6. Build a structured prompt.
   - Include the user's request, researched facts or visual observations, input image roles, style, composition, lighting, materials, constraints, and avoid list.
   - Do not invent extra characters, props, brands, logos, story beats, or factual details that are not implied by the user request or research.
7. For official GPT Image models, decode `data[].b64_json`. Treat `data[].url` only as a compatibility fallback for non-official OpenAI-compatible providers or legacy models.
8. Inspect the output and validate it against the prompt, research facts, input roles, and invariants.
9. Save the final image to the requested path and report the output path, final prompt, and sources used when web research was performed. Do not repeat API keys.

## Provider Input

The script does not use Codex root configuration. It reads third-party provider settings from `<skill-dir>/.env` by default.

Default provider file:

```env
API_IMAGE_PROVIDER_NAME=main
API_IMAGE_BASE_URL=https://provider.example/v1
API_IMAGE_API_KEY=your_provider_key
# API_IMAGE_MODEL=gpt-image-2

# API_IMAGE_FALLBACK_1_NAME=backup-a
# API_IMAGE_FALLBACK_1_BASE_URL=https://backup-provider.example/v1
# API_IMAGE_FALLBACK_1_API_KEY=your_backup_provider_key
# API_IMAGE_FALLBACK_1_MODEL=gpt-image-2
```

Accepted provider sources:

- `<skill-dir>/.env`
- `--env-file <path>` for an alternate provider file
- `--base-url <https://provider.example/v1>` for a temporary URL override
- `--api-key-env <ENV_NAME>` for a temporary key override from an environment variable
- `--api-key <key>` for a temporary direct key override

Resolution order:

1. Primary `base_url`: `--base-url`, then `API_IMAGE_BASE_URL` from the provider file.
2. Primary API key: `--api-key`, then `--api-key-env`, then `API_IMAGE_API_KEY` from the provider file.
3. Fallback providers: `API_IMAGE_FALLBACK_1_*`, `API_IMAGE_FALLBACK_2_*`, and so on in numeric order.
4. Provider display name: `API_IMAGE_PROVIDER_NAME` or `API_IMAGE_FALLBACK_<N>_NAME`; defaults to `primary`, `fallback_1`, and so on.
5. Model: command `--model`, overridden per provider by `API_IMAGE_MODEL` or `API_IMAGE_FALLBACK_<N>_MODEL` when set.

Rules:

- Do not echo API keys back to the user.
- Do not store API keys in the repository.
- `.env` is ignored by `.gitignore`; keep real keys there.
- If both `--api-key` and `--api-key-env` are provided, the script raises an error.
- If `--base-url` or provider-file `base_url` is not an HTTP(S) URL, the script raises an error.
- The script falls back only on retryable channel errors: connection failure, timeout, HTTP 429, or HTTP 5xx.
- The script does not fall back on local validation errors, invalid credentials, unsupported parameters, HTTP 400, HTTP 401, HTTP 403, or content policy refusals.

## Command

Use the bundled script for normal text-to-image generation:

```bash
python3 "<skill-dir>/scripts/generate_image.py" \
  --prompt "画一只可爱的猫抱着水獭，温暖治愈，插画风格，柔和灯光，细腻毛发，构图清晰" \
  --size "2048x1152" \
  --quality "high" \
  --out "./outputs/cute-cat-otter.png"
```

Use the same script for reference-image generation or edits:

```bash
python3 "<skill-dir>/scripts/generate_image.py" \
  --prompt "参考输入图的构图和角色姿势，生成一张暖色电影感插画" \
  --image "/path/to/reference.png" \
  --image-role "composition and pose reference" \
  --size "2048x2048" \
  --quality "high" \
  --out "./outputs/reference-output.png"
```

Use `--mask` for localized edits:

```bash
python3 "<skill-dir>/scripts/generate_image.py" \
  --prompt "只把被 mask 标出的区域替换成一只小水獭，保持其他区域不变" \
  --image "/path/to/source.png" \
  --mask "/path/to/mask.png" \
  --out "./outputs/masked-edit.png"
```

For web-researched subjects, download selected reference images to a working folder first, then pass them as `--image`:

```bash
python3 "<skill-dir>/scripts/generate_image.py" \
  --prompt "Create a new 4K overhead aerial image of Huajiang Grand Canyon Bridge in Guizhou, based on the reference images. Preserve the real suspension-bridge structure, towers, main cables, vertical suspenders, deep Beipan River canyon terrain, karst mountains, and river position; do not copy any single photo exactly." \
  --image "/path/to/refs/huajiang-bridge-aerial.jpg" \
  --image-role "aerial composition and bridge alignment reference" \
  --image "/path/to/refs/huajiang-canyon-terrain.jpg" \
  --image-role "canyon terrain and river reference" \
  --size "2048x1152" \
  --quality "high" \
  --timeout 0 \
  --out "./outputs/huajiang-canyon-bridge-overhead.png"
```

Useful options:

- `--model gpt-image-2`
- `--mode auto|generate|edit`
- `--size 2048x1152` script default 2K landscape
- `--size 1024x1024`
- `--size 1536x1024`
- `--size 1024x1536`
- `--size 2048x2048`
- `--size 3840x2160`
- `--size auto` for official API auto sizing
- `--quality low|medium|high|auto`
- `--n 1`
- `--image <path>` repeated up to 16 times
- `--image-role <role>` to label input images inside the prompt
- `--mask <path>` for localized edits
- `--background auto|opaque` for official `gpt-image-2`
- `--output-format png|jpeg|webp`
- `--output-compression 0-100` for `jpeg` or `webp`
- `--input-fidelity low|high` for supported edit models only; do not send it for `gpt-image-2`
- `--moderation auto|low` for supported GPT image models
- `--prompt-file <path>` for one prompt per non-empty line
- `--env-file <path>` alternate provider file
- `--base-url <https://provider.example/v1>` temporary URL override
- `--api-key-env <ENV_NAME>` temporary key override from an environment variable
- `--api-key <key>` temporary direct key override
- `--timeout 1800`
- `--timeout 0`

## Payload Shape

Use the provider's generation endpoint with this body shape:

```json
{
  "model": "gpt-image-2",
  "prompt": "你的中文或英文提示词",
  "size": "2048x1152",
  "quality": "high",
  "n": 1
}
```

Use the provider's edit endpoint as multipart form data:

```text
model=gpt-image-2
prompt=<edit or reference prompt>
image[]=@source-or-reference.png
mask=@mask.png
size=1024x1024
quality=high
n=1
```

Start with `n=1`. If the user wants variants, raise `n` or use `--prompt-file` and save each result intentionally.

## gpt-image-2 API Notes

For official OpenAI `gpt-image-2`:

- Text-only generation uses `POST /v1/images/generations` with JSON.
- Any input image, reference image, or mask uses `POST /v1/images/edits` with multipart form-data.
- Use repeated `image[]=@path` fields for multiple input/reference images.
- When using `mask`, the first `--image` must be the edit target; additional images should be references or compositing sources.
- Read image bytes from `data[].b64_json`; URL output is not supported for official GPT Image models.
- Do not send `input_fidelity`; `gpt-image-2` always processes image inputs at high fidelity.
- Do not request `background: transparent`; official `gpt-image-2` currently supports `auto` or `opaque`, not transparent backgrounds.
- For masked edits, validate that the mask and first source image have the same dimensions and compatible format, are under the image API file-size limit, and that the mask includes an alpha channel.

## Capability Map

- New text-to-image generation: supported through `/images/generations`.
- Batch generation: supported through `--n` for multiple variants per prompt, or `--prompt-file` for many prompts.
- Reference-image generation: supported through `/images/edits` with one or more `--image` inputs and role labels in the prompt.
- Image editing: supported through `/images/edits` with `--image` and an edit prompt.
- Localized edits / inpainting: supported through `/images/edits` with `--image` plus `--mask`.
- Background replacement: supported as an edit prompt, with `--mask` when the replacement area must be constrained.
- Style transfer: supported as reference-image editing; label the source image role and describe the desired style in the prompt.
- Input image role labeling: not a separate API field; this script appends `--image-role` labels to the prompt so the model can interpret each input image intentionally.
- Transparent background: official `gpt-image-2` does not currently support `background: transparent`. Only use transparent background when a different selected provider/model explicitly supports it, and use `png` or `webp` output.

## Research And References

Do not assume the image model knows every subject accurately. Research first or use references when the subject is not common visual knowledge.

Reference images are the preferred path for visually constrained research-required tasks. Text research describes facts; reference images carry visual structure. Use both whenever feasible.

Research-required examples:

- A named structure or location, such as `贵州花江峡谷大桥` or any real bridge, landmark, terrain, skyline, or building.
- A real product, vehicle, machine, UI, logo-free product silhouette, game asset from a known franchise, or fashion item.
- A historical scene, cultural garment, uniform, heraldry, ritual object, weapon, architecture style, organism, map, technical diagram, or scientific subject.
- A current or recently changed subject.
- A niche visual style or artist-adjacent style where references are necessary to avoid generic output.

Research workflow:

- Search the web for factual text details when structure, function, history, geography, or current status matters.
- Use image search or provided images for visual details such as shape, terrain, materials, proportions, colors, and surrounding environment.
- For named structures, real locations, real products, real vehicles, historical/cultural visual subjects, technical diagrams, and niche styles, actively collect at least one useful reference image before generating.
- Prefer multiple complementary references when possible: one for subject structure, one for surrounding environment, and one for desired camera angle/composition.
- Download reference images to a local working path before invoking the script, then pass them with `--image` and `--image-role`.
- If a reference image is low quality but still useful, label its role narrowly, for example `rough terrain reference only`.
- Extract only the details needed for the prompt; keep the prompt concise.
- Include factual constraints in the prompt, for example bridge type, deck/tower/cable arrangement, canyon terrain, river position, viewpoint, and surrounding landforms.
- Cite sources in the final response whenever web research was used.

Reference workflow:

- Prefer provided reference images over memory when visual fidelity matters.
- For each `--image`, pass a matching `--image-role` such as `edit target`, `style reference`, `composition reference`, `product reference`, or `terrain reference`.
- Do not treat every image as an edit target; decide whether it is reference-only or should be preserved and modified.
- For compositing, state exactly what comes from each input and how lighting, perspective, scale, and shadows should match.
- For reference-only generation, prompt the model to create a new image based on the references, not to copy a single source photo exactly.
- If the image model/provider rejects a reference-image edit request, surface that error and then decide whether a text-only generation is acceptable for this task. Do not silently fall back.

## Prompt Structure

Use this compact schema when it helps:

```text
Use case: <photorealistic-natural|product-mockup|ui-mockup|infographic-diagram|logo-brand|illustration-story|stylized-concept|historical-scene|text-localization|identity-preserve|precise-object-edit|lighting-weather|background-extraction|style-transfer|compositing|sketch-to-render>
Asset type: <where the image will be used>
Primary request: <user request>
Research facts / visual references: <only the relevant observed details>
Input images: <Image 1: role; Image 2: role>
Scene/backdrop: <environment>
Subject: <main subject>
Style/medium: <photo/illustration/3D/etc>
Composition/framing: <viewpoint, lens/framing, placement>
Lighting/mood: <lighting and mood>
Materials/textures: <surface details>
Text (verbatim): "<exact text if needed>"
Constraints: <must keep/must avoid>
Avoid: <negative constraints>
```

## Waiting Behavior

- This script is synchronous. It does not return before the provider finishes the image job or an explicit error occurs.
- Default timeout is `1800` seconds so long-running jobs are not cut off too early.
- Use `--timeout 0` to disable the client-side timeout and wait indefinitely for the provider response.
- When invoking this script from Codex, give the shell command a timeout that is longer than the expected image job. Do not use a short shell timeout for long generations.

## Size And Quality

Follow the current official GPT Image rules for `gpt-image-2`:

- `size` can be `auto` or any `<width>x<height>` string that satisfies all of these:
- width and height are multiples of `16`
- the longest edge is at most `3840`
- the long-edge to short-edge ratio is at most `3:1`
- total pixels are between `655,360` and `8,294,400`
- this script defaults to `2048x1152`; the official API's default sizing behavior is `auto`
- common examples: `1024x1024`, `1536x1024`, `1024x1536`, `2048x2048`, `2048x1152`, `3840x2160`, `2160x3840`
- `quality` can be `low`, `medium`, `high`, or `auto`; this script defaults to `high`, while official API auto quality is available with `auto`
- 2K and 4K requests are valid when they satisfy those constraints
- Do not silently coerce unsupported sizes. Raise a clear error instead.

## Prompting

- Prefer concrete prompts with subject, style, lighting, and composition.
- Use the user's language by default. Chinese prompts are valid for this workflow.
- Change one aspect at a time when iterating.

## Output Rules

- Save project assets inside the project workspace when the user wants a usable asset.
- Save preview images to a clear temporary or user-requested path.
- If `n > 1`, keep filenames deterministic by appending `-1`, `-2`, and so on.

## Failure Rules

- Raise explicit errors when `<skill-dir>/.env` is missing or when `base_url` or API key is missing from the provider file.
- Raise explicit errors when both `--api-key` and `--api-key-env` are provided, when the named environment variable is empty, or when `base_url` is not an HTTP(S) URL.
- Try fallback providers in numeric order only for retryable channel errors: connection failure, timeout, HTTP 429, or HTTP 5xx.
- Do not use fallback providers for local validation errors, invalid credentials, unsupported parameters, HTTP 400, HTTP 401, HTTP 403, or content policy refusals.
- Raise explicit errors when `size` violates the official GPT Image constraints or `quality` is unsupported.
- Raise explicit errors when edit/reference mode is requested without input images.
- Raise explicit errors when `gpt-image-2` is used with `--background transparent` or `--input-fidelity`.
- Raise explicit errors when a mask is not compatible with the first `--image` edit target, has different dimensions, lacks an alpha channel, or exceeds the image API file-size limit.
- Surface provider errors directly. Do not fabricate a success result.
- If the provider uses a different image model name on this machine, override `--model`.

## Resource

- `scripts/generate_image.py`: Read third-party provider credentials from `<skill-dir>/.env`, call the provider's image endpoint, and save the returned image data.

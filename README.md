# api-image

一个给 Codex App 用的图片生成 Skill。

它的作用很简单：当你在 API 形式使用 Codex App，没法直接用官方内置 `imagegen` 时，让 Codex 改走你自己配置的 OpenAI-compatible 图片接口，例如通过 CPA 反代出来的 `gpt-image-2`。

用网页版生过图的朋友应该知道，网页端的生图不是单纯“把一句 prompt 传给图片模型”。它更像一个 agent：主模型会理解你的需求，必要时搜索资料、分析参考图、整理提示词，然后再调用图片模型。这个 Skill 就是尽量复刻这种流程：你用自然语言告诉 Codex 想要什么，Codex 负责前面的 agent 工作，最后通过你的 Provider API 生图。

## 它能做什么

- 文生图
- 参考图生图
- 局部编辑 / inpainting
- 多参考图辅助构图、风格、产品或人物一致性
- 需要真实信息的图片生成前，先让 Codex 搜索和整理参考资料
- 从 skill 目录里的 `.env` 读取第三方 Provider `base_url`
- 从 skill 目录里的 `.env` 读取第三方 Provider API Key

更细的调用规则和脚本参数都在 [SKILL.md](./SKILL.md) 里，README 只讲怎么用。

## 安装

Linux / macOS：

```bash
mkdir -p ~/.codex/skills
git clone <repo-url> ~/.codex/skills/api-image
```

如果仓库已经在本机，也可以复制：

```bash
mkdir -p ~/.codex/skills
cp -R /path/to/api-image ~/.codex/skills/api-image
```

Windows：

把仓库放到 Codex 的 skills 目录：

```powershell
git clone <repo-url> "$env:USERPROFILE\.codex\skills\api-image"
```

如果你设置了 `CODEX_HOME`：

```powershell
git clone <repo-url> "$env:CODEX_HOME\skills\api-image"
```

然后重启 Codex App，或让 Codex 重新加载 Skills。

## 配置

这个 Skill 不读取 Codex 根目录里的 `auth.json` 或 `config.toml`。

安装后只改这个文件：

```bash
~/.codex/skills/api-image/.env
```

内容写成这样：

```env
API_IMAGE_BASE_URL=https://你的第三方地址/v1
API_IMAGE_API_KEY=你的第三方key
```

需要填两个值：

- `base_url`
- API Key

`.env` 已在 `.gitignore` 里，不会上传到 GitHub。不要把真实 key 写进 `README.md` 或 `SKILL.md`。

## 怎么用

安装后，正常和 Codex 说话就行。比如：

```text
用 api-image 生成一张 2048x1152 的电影感照片：雨夜东京街头，霓虹反光，真实摄影风格。
```

带参考图时可以这样说：

```text
参考这张图的构图和人物姿势，生成一张暖色电影感插画，保持主体姿态，但不要照抄原图。
```

需要真实地点、产品、建筑、历史服饰这类容易生成错的东西时，可以直接要求 Codex 先查资料：

```text
先查一下花江峡谷大桥的结构和地形参考，再生成一张高空俯视图，尽量保持真实桥型和峡谷环境。
```

如果只想临时换一次接口，也可以告诉 Codex：

```text
这次生图临时用 https://example.com/v1 这个 base_url，API key 用我提供的临时 key。
```

日常用法只改 `.env`。临时 key 不会写回 `.env`。

## 关于 gpt-image-2

这个 Skill 默认按 `gpt-image-2` 的官方图片 API 规则处理：

- 纯文生图走 `/images/generations`
- 有参考图、输入图或 mask 时走 `/images/edits`
- 官方 GPT Image models 默认读返回里的 `b64_json`
- `gpt-image-2` 不支持透明背景
- `gpt-image-2` 不需要、也不应该传 `input_fidelity`

如果你的 Provider 对这些参数有自己的兼容层，以 Provider 的实际报错为准。

## 目录

```text
api-image/
  SKILL.md
  README.md
  LICENSE
  agents/
  scripts/
```

## 说明

这是个人自用 Skill 的整理版，主要目标是让 Codex App 在 API 使用形态下也能比较自然地完成图片生成工作。不同反代和 Provider 的兼容程度可能不一样。

MIT License.

## 致谢

感谢 [linuxdo](https://linux.do/) 社区的交流、分享与反馈。

# model-gateway — 把每个任务路由到最对口的模型

**好用的模型缺多模态，全能的模型又太贵。model-gateway 做一件事：不同任务自动走不同模型，好的用在对的地方，贵的只用在值的地方。**

## 问题

现在的模型格局是这样的：

| 模型 | 优势 | 短板 |
|------|------|------|
| DeepSeek | 推理强、便宜、上下文大 | 没有多模态 |
| 豆包 (Doubao) | 视觉理解出色、便宜 | 复杂推理不如 DeepSeek |
| GPT-5.4 | 架构设计、深度分析顶尖 | 贵，日常用浪费 |
| Gemini 2.5 Flash | 多语言翻译质量高、便宜 | 代码能力一般 |

**一个模型打不了全场。** 你既想用 DeepSeek 做日常推理，又想用豆包分析截图图表，偶尔还需要 GPT-5.4 做复杂架构规划。切换模型、管理 API key、记住哪个模型适合什么任务——这些都是认知负担。

## 解决方案

model-gateway 是一个**模型路由器**。你正常使用 Claude Code，它在背后把不同任务自动分发到最合适的模型：

```
你的任务                          →  路由到
──────────────────────────────────────────
分析这张截图里有几个按钮            →  豆包 Seed 2.1 Pro (视觉，便宜)
设计微服务事务补偿方案              →  GPT-5.4 (深度推理，贵但值)
审查 auth.py 有没有安全漏洞         →  GPT-5.4 (安全审计，不能省钱)
"Redis 集群 vs 哨兵，怎么选？"      →  GPT-5.4 (决策分析)
翻译产品文档到日文                  →  Gemini 2.5 Flash (翻译，便宜)
其他所有事情                        →  DeepSeek (你当前用的默认模型)
```

**好的模型用在对的地方，贵的模型只用在值的地方。**

## 快速开始

```bash
# 1. 安装
pip install -e .

# 2. 设置 API Key（在 ~/.claude/settings.json 的 env 块）
#   "OPENROUTER_API_KEY": "sk-or-v1-xxx",   # 用于 GPT-5.4、Gemini 等
#   "ARK_API_KEY": "your-ark-key"           # 用于豆包视觉

# 3. 添加工具——改 config.json，加一段 JSON：
# {
#   "tool": "translate_to_japanese",
#   "description": "Translate text to Japanese",
#   "provider": "openrouter",
#   "model": "google/gemini-2.5-flash",
#   "system_prompt": "Translate to natural Japanese. Preserve tone.",
#   "input_schema": {
#     "type": "object",
#     "properties": {
#       "text": { "type": "string", "description": "Text to translate" }
#     },
#     "required": ["text"]
#   }
# }

# 4. 重启 Claude Code —— 新工具自动出现。
```

## 架构

```
Claude Code (你用的是 DeepSeek 也没关系)
    │
    ├── "帮我看看这张架构图"  ──→  vision_ask  ──→  豆包 Seed 2.1 Pro
    ├── "设计一个迁移方案"    ──→  gpt_plan     ──→  GPT-5.4
    ├── "审查这段代码"        ──→  gpt_review   ──→  GPT-5.4
    ├── "翻译成中文"          ──→  gpt_translate ──→  Gemini 2.5 Flash
    └── ...更多工具，只需在 config.json 加一段 JSON
```

核心思路：**config.json 定义"什么任务→什么模型→什么提示词"，server.py 负责 MCP 协议和 API 调用。加新工具零 Python 代码。**

## 内置工具

| 工具 | 走哪个模型 | 做什么 | 为什么是这个模型 |
|------|-----------|--------|------------------|
| `vision_ask` | 豆包 Seed 2.1 Pro | 图片分析、截图理解、图表解读 | 视觉理解好，便宜 |
| `gpt_plan` | GPT-5.4 | 架构设计、实现方案规划 | 深度推理，复杂任务不省钱 |
| `gpt_review` | GPT-5.4 | 代码审查（安全/正确性/架构） | 找隐蔽漏洞需要深度 |
| `gpt_decide` | GPT-5.4 | 多方案决策分析 | 权衡博弈需要强推理 |
| `gpt_design_workflow` | GPT-5.4 | 生成 Workflow 编排脚本 | 多步骤编排需要全局视角 |
| `gpt_translate` | Gemini 2.5 Flash | 多语言翻译 | 翻译质量高，便宜 |

## CLI 使用

```bash
mg vision photo.jpg "描述这张图片"
mg plan "设计微服务事务补偿机制" --budget high
mg review auth.py --focus security
mg decide "Redis 集群" "哨兵方案" "云服务" --criteria "性能,成本,运维"
mg workflow "迁移认证系统到 JWT，零停机" --quality exhaustive
mg translate "Hello world" Chinese
```

## Claude Code 集成

```json
{
  "mcpServers": {
    "model-gateway": {
      "command": "python",
      "args": ["-m", "model_gateway.mcp_server"],
      "cwd": "/path/to/model-gateway"
    }
  }
}
```

## 安全

- **API Key 不在仓库里**，全部走环境变量
- `config.json` 已被 `.gitignore` 排除，不会意外提交
- 配置写入时自动剥离已解析的 Key

## License

MIT

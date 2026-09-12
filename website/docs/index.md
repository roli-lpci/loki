---
slug: /
sidebar_position: 0
title: "Loki Agent Documentation"
description: "The self-improving AI agent built by WunderCorp, Inc.. A built-in learning loop that creates skills from experience, improves them during use, and remembers across sessions."
hide_table_of_contents: true
displayed_sidebar: docs
---

# Loki Agent

The self-improving AI agent built by [WunderCorp, Inc.](https://wundercorp.co). The only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, and builds a deepening model of who you are across sessions.

[Get Started](/getting-started/installation) · [Explore Bot Mode](/user-guide/bot-mode) · [Download Desktop](https://loki.computer/) · [View on GitHub](https://github.com/wundercorp/loki)


## Install

### Windows or macOS

To easily install the command-line and desktop applications, [download the Loki Desktop installer](https://loki.computer/) from our website and run it.

### Without Loki Desktop:

For a command-line only install without Loki Desktop, run:

#### Linux / macOS / WSL2 / Android (Termux)

```bash
curl -fsSL https://loki.computer/install.sh | bash
```

#### Windows (native)

Run in powershell:

```powershell
iex (irm https://loki.computer/install.ps1)
```

See the full **[Installation Guide](/getting-started/installation)** for what the installer does, the per-user vs root layout, and Windows-specific notes. For the complete platform support matrix, see **[Platform Support](/getting-started/platform-support)**.

> **Fastest path to a working agent:** After installing, run `loki model`, choose **OpenRouter**, and press `o` at the API-key prompt to open the key page. Paste the key, pick a model, and start Loki.

## What is Loki Agent?

It's not a coding copilot tethered to an IDE or a chatbot wrapper around a single API. It's an **autonomous agent** that gets more capable the longer it runs. It lives wherever you put it — a $5 VPS, a GPU cluster, or serverless infrastructure (Daytona, Modal) that costs nearly nothing when idle. Talk to it from Telegram while it works on a cloud VM you never SSH into yourself. It's not tied to your laptop.

## Quick Links

|                                                                         |                                                                       |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 🚀 **[Installation](/getting-started/installation)**                    | Install in 60 seconds on Linux, macOS, WSL2, native Windows, Nix & NixOS or Android |
| 📖 **[Quickstart Tutorial](/getting-started/quickstart)**               | Your first conversation and key features to try                       |
| 🗺️ **[Learning Path](/getting-started/learning-path)**                  | Find the right docs for your experience level                         |
| ⚙️ **[Configuration](/user-guide/configuration)**                       | Config file, providers, models, and options                           |
| 💬 **[Messaging Gateway](/user-guide/messaging)**                       | Set up Telegram, Discord, Slack, WhatsApp, Teams, or more             |
| 🤖 **[Bot Mode](/user-guide/bot-mode)**                                | Named Bots with their own model, memory, skills, routines, and chats  |
| 🔧 **[Tools & Toolsets](/user-guide/features/tools)**                   | 60+ built-in tools and how to configure them                          |
| 🧠 **[Memory System](/user-guide/features/memory)**                     | Persistent memory that grows across sessions                          |
| 📚 **[Skills System](/user-guide/features/skills)**                     | Procedural memory the agent creates and reuses                        |
| 🔌 **[MCP Integration](/user-guide/features/mcp)**                      | Connect to MCP servers, filter their tools, and extend Loki safely  |
| 🧭 **[Use MCP with Loki](/guides/use-mcp-with-loki)**               | Practical MCP setup patterns, examples, and tutorials                 |
| 🎙️ **[Voice Mode](/user-guide/features/voice-mode)**                    | Real-time voice interaction in CLI, Telegram, Discord, and Discord VC |
| 🗣️ **[Use Voice Mode with Loki](/guides/use-voice-mode-with-loki)** | Hands-on setup and usage patterns for Loki voice workflows          |
| 🎭 **[Personality & SOUL.md](/user-guide/features/personality)**        | Define Loki' default voice with a global SOUL.md                    |
| 📄 **[Context Files](/user-guide/features/context-files)**              | Project context files that shape every conversation                   |
| 🔒 **[Security](/user-guide/security)**                                 | Command approval, authorization, container isolation                  |
| 💡 **[Tips & Best Practices](/guides/tips)**                            | Quick wins to get the most out of Loki                              |
| 🏗️ **[Architecture](/developer-guide/architecture)**                    | How it works under the hood                                           |
| ❓ **[FAQ & Troubleshooting](/reference/faq)**                          | Common questions and solutions                                        |

## Key Features

- **A closed learning loop** — Agent-curated memory with periodic nudges, autonomous skill creation, skill self-improvement during use, FTS5 cross-session recall with LLM summarization, and [Honcho](https://github.com/plastic-labs/honcho) dialectic user modeling
- **Runs anywhere, not just your laptop** — 8 terminal backends: local, Docker, SSH, AgentVM, Daytona, Singularity, Modal, Vercel Sandbox. Daytona and Modal offer serverless persistence — your environment hibernates when idle, costing nearly nothing
- **Lives where you do** — CLI, Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Mattermost, Email, SMS, DingTalk, Feishu, WeCom, Weixin, QQ Bot, Yuanbao, BlueBubbles, Home Assistant, Microsoft Teams, Google Chat, and more — 20+ platforms from one gateway
- **Built by model trainers** — Created by [WunderCorp, Inc.](https://wundercorp.co), the lab behind Loki, Nomos, and Psyche. Works with [OpenRouter](https://openrouter.ai), OpenAI, Anthropic, or any compatible endpoint
- **Scheduled automations** — Built-in cron with delivery to any platform
- **[Bot Mode](/user-guide/bot-mode)** — Build a durable team of specialist Bots that work together in group chats and through `@mentions`
- **Delegates & parallelizes** — Spawn isolated subagents for parallel workstreams. Programmatic Tool Calling via `execute_code` collapses multi-step pipelines into single inference calls
- **Open standard skills** — Compatible with [agentskills.io](https://agentskills.io). Skills are portable, shareable, and community-contributed via the Skills Hub
- **Full web control** — Search, extract, browse, vision, image generation, and TTS through configurable tool providers
- **MCP support** — Connect to any MCP server for extended tool capabilities
- **Research-ready** — Batch processing, trajectory export, RL training with Atropos. Built by [WunderCorp, Inc.](https://wundercorp.co) — the lab behind Loki, Nomos, and Psyche models

## For LLMs and coding agents

Machine-readable entry points to this documentation:

- **[`/llms.txt`](/llms.txt)** — curated index of every doc page with short descriptions. ~17 KB, safe to load into an LLM context.
- **[`/llms-full.txt`](/llms-full.txt)** — every doc page concatenated into a single markdown file for one-shot ingestion. ~1.8 MB.

Both files also resolve at `/llms.txt` and `/llms-full.txt`. Generated fresh on every deploy.

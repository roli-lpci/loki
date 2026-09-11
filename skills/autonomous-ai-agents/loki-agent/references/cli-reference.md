# Loki CLI Reference

Live sources when anything looks stale: `loki --help`, `loki <command> --help`,
https://doku.sh/#/i/cbe1e051e4be2bb725-26f1d908878243

### Global Flags

```
loki [flags] [command]        (no subcommand = interactive chat)

  --version, -V             Show version
  -z, --oneshot PROMPT      One-shot: print ONLY the final response (for scripts/pipes)
  -m MODEL  --provider P    Model/provider override for this invocation
  -t, --toolsets LIST       Comma-separated toolsets for this invocation
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --tui / --cli             Force the Ink TUI / classic REPL
  --ignore-rules            Skip AGENTS.md/SOUL.md/memory/skill injection
  --safe-mode               Disable ALL customizations (troubleshooting)
  --pass-session-id         Include session ID in system prompt
```

### Chat

```
loki chat [flags]
  -q, --query TEXT          Single query, non-interactive
  --image PATH              Attach a local image to a single query
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --max-turns N             Cap tool-calling iterations
  --source TAG              Session source tag (default: cli)
```
(plus the global flags above)

### Configuration

```
loki setup [section]      Wizard (model|tts|terminal|gateway|tools|agent)
loki model                Interactive model/provider picker
loki fallback [add|remove|list]  Fallback provider chain
loki config [show|edit|get|set|unset|path|env-path|check|migrate]
loki login / logout       OAuth sign-in / clear stored auth
loki doctor [--fix]       Check dependencies and config
loki status [--all]       Component status
```

### Tools & Skills

```
loki tools [list|enable NAME|disable NAME]   Per-platform toolsets (curses UI with no args)

loki skills list|browse|search QUERY|inspect ID
loki skills install ID    Hub identifier OR a direct https://…/SKILL.md URL
loki skills config        Enable/disable skills per platform
loki skills check|update|uninstall|publish PATH
loki skills tap add REPO  Add a GitHub repo as a skill source
loki bundles              Skill bundles (one /<name> alias loads several skills)
```

### MCP Servers

```
loki mcp add NAME (--url or --command) | remove | list | test NAME
loki mcp catalog | install NAME     Curated catalog install
loki mcp configure NAME             Toggle tool selection
loki mcp serve                      Run Loki as an MCP server
```
Details (transport, tool discovery, catalog): `references/native-mcp.md`.

### Gateway (Messaging Platforms)

```
loki gateway run|install|start|stop|restart|status|setup
```

20+ platforms: Telegram, Discord, Slack, WhatsApp (Baileys + Business Cloud API), iMessage (Photon — `loki photon setup`), Signal, Email, SMS, Matrix, Mattermost, Teams, LINE, SimpleX, ntfy, Google Chat, Home Assistant, DingTalk, Feishu, WeCom, Weixin, API Server, Webhooks. Open WebUI connects via the API Server adapter. Most adapters ship under `plugins/platforms/`.
Docs: https://doku.sh/#/i/cbe1e051e4be2bb725-26f1d908878243

### Sessions

```
loki sessions list|browse|rename ID TITLE|delete ID|export OUT|prune|stats
```

### Cron / Webhooks

```
loki cron list|create SCHED|edit ID|pause|resume|run ID|remove|status
    Schedules: '30m', 'every 2h', '0 9 * * *', ISO timestamp
loki webhook subscribe NAME|list|remove NAME|test NAME
```
Webhook payloads/routes: `references/webhooks.md`.

### Profiles

```
loki profile list|create NAME (--clone|--clone-all|--clone-from)|use|show|delete
loki profile rename A B | alias NAME | export NAME | import FILE
```

### Credentials & Pools

```
loki auth                 Interactive credential manager
loki auth add [PROVIDER]  Add OAuth or API-key credential (wundercorp, openai-codex, qwen-oauth, …)
loki auth list|remove P IDX|reset PROVIDER|status
```
Multiple credentials per provider form a pool that rotates automatically and skips exhausted keys.

### Other

```
loki desktop / gui        Native desktop app
loki dashboard            Web admin panel + embedded chat (--stop / --status)
loki proxy                OpenAI-compatible local proxy backed by an OAuth provider
loki portal               Quick setup / sign in via WunderCorp Portal
loki kanban <verb>        Multi-agent work-queue board
loki project              Named multi-folder workspaces
loki skin list|use|set    Switch/tweak skins (see references/themes.md)
loki pets <verb>          Pet mascots (see references/petdex.md)
loki memory setup|status|off|reset   Memory provider
loki secrets bitwarden|onepassword   External secret stores
loki moa                  Mixture-of-Agents slots
loki hooks / security / backup / import / checkpoints / console
loki logs [-f] [errors]   View agent/error logs
loki send                 One-off message through a gateway platform
loki pairing / plugins / insights / journey / computer-use
loki acp                  ACP server (IDE integration)
loki completion bash|zsh|fish
loki update / uninstall / claw migrate
```

Plugin- and provider-supplied subcommands (e.g. `loki photon setup`) only appear once their plugin is installed/active.

### Where to Find Things

| Looking for... | Location |
|---|---|
| Config options | `loki config edit` · [Configuration docs](https://doku.sh/#/i/cbe1e051e4be2bb725-26f1d908878243) |
| Tools / toolsets | `loki tools list` · [Tools reference](https://doku.sh/#/i/cbe1e051e4be2bb725-26f1d908878243) |
| Skills catalog | `loki skills browse` · [Skills catalog](https://doku.sh/#/i/cbe1e051e4be2bb725-26f1d908878243) |
| Provider setup | `loki model` · [Providers guide](https://doku.sh/#/i/cbe1e051e4be2bb725-26f1d908878243) |
| Env variables | `loki config env-path` · [Env vars reference](https://doku.sh/#/i/cbe1e051e4be2bb725-26f1d908878243) |
| Gateway logs | `~/.loki/logs/gateway.log` (or `loki logs`) |
| Sessions | `loki sessions browse` (reads state.db) |

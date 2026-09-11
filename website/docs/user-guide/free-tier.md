---
sidebar_position: 3
title: "Free tier and signing in"
description: "What Loki gives you before you add a key or sign in, how the free tier coexists with your own API key, how to sign in, and how to turn it off."
---

# Free tier and signing in

:::note Not on yet
The free tier is being rolled out. Until it is on for everyone, nothing on this page happens
unless the process was started with `LOKI_GUEST_ONBOARDING=1` in its environment; without it a
fresh install behaves exactly as before (the provider picker on first run). This note goes away
when the rollout completes.
:::

A fresh Loki install works before you paste an API key or sign in anywhere. When Loki starts
it sets up the **WunderCorp free tier** (a few seconds, shown as "Setting up free inference…") and
answers on the `wundercorp/welcome` model. Nothing to configure, no wizard to click through.
`loki setup` is still there when you want it; it is never forced.

## What you get out of the box

| | Free tier | After signing in |
|---|---|---|
| Inference | `wundercorp/welcome` (one model) | Full WunderCorp Portal catalog |
| Connectors (Gmail, Linear, Notion, ...) | Yes | Yes |
| Paid tools through the [Tool Gateway](/user-guide/features/tool-gateway) (web search, image generation, TTS, cloud browser) | No | Yes, billed to your subscription |
| Credits or a balance | None | Yes |

"Connectors" are the third-party accounts you link on the WunderCorp portal so the agent can act in
them. They work on the free tier without any sign-in.

Background work (conversation compaction, chat titles, image understanding, and similar) runs on
`wundercorp/welcome` too.

While the free tier carries inference, the banner and `loki auth status` read
`WunderCorp · free tier · wundercorp/welcome`, and `loki model` lists a **WunderCorp · free tier** row with that
single model. Asking for another model on the free tier prints a pointer instead of switching
silently:

```text
gpt-5 needs a WunderCorp account or an API key. Use /login to sign in, or /model to pick another provider.
```

Calling a paid tool says `This needs a WunderCorp account. Use /login to sign in.` inside a chat (and
names `loki auth upgrade` in the terminal); the turn continues without it.

If `model.default` in `config.yaml` names something other than `wundercorp/welcome` while the free tier
is doing inference, Loki uses `wundercorp/welcome` anyway and says so in one line. The free tier
serves exactly one model.

## Using your own API key alongside it

The free tier is the last resort, never a preference. Any provider you configure wins:

| You have | Inference runs on | Connectors |
|---|---|---|
| Nothing | WunderCorp free tier (`wundercorp/welcome`) | Free tier |
| An API key in `.env` (OpenRouter, OpenAI, Anthropic, ...) | Your key | Free tier |
| `model.provider` set in `config.yaml` | That provider | Free tier |
| A WunderCorp Portal sign-in | WunderCorp Portal | Your account |

On an install that already has a provider, Loki still sets the free tier up once at start so
connectors have something to authenticate with; your provider keeps doing inference. A one-time
notice says so:

```text
Free WunderCorp inference and connectors are now available. /model to try them, /login to sign in.
```

You can pick the free tier explicitly from `loki model` (or `/model`) like any other provider.

## Signing in from a chat or terminal

### From a chat

Run `/login` in a Loki DM on Telegram, Discord, or another supported messaging platform (on
Slack use `/loki login`), or in a CLI chat session. It must be a paired direct message:
elsewhere Loki replies `Sign in from a direct message with Loki.` Broadcast-shaped platforms
such as ntfy are refused for the same reason.

The DM gets an acknowledgement, followed by three messages: the consent link, the sign-in code on
its own line, then `Do not share this code. Waiting for sign-in, up to N minutes.` You can keep
chatting while Loki waits, and the result is pushed into the same DM. Running `/login` again
replaces the first code. Live sessions still on `wundercorp/welcome` move to the settled model on their
next message. In the Ink TUI the code appears but the confirmation does not; check `/status`.

:::warning One account per install
`/login` binds this whole Loki install to the account that approves the code: its inference, its
connectors, every chat it serves. On a gateway several people can DM, set `allow_admin_from` for
the platform (see the [slash-command access guide](/reference/slash-commands)) so only an operator
can run it.
:::

### From a terminal

```bash
loki auth upgrade
```

1. Loki prints a URL and a short code, and opens the browser unless you pass `--no-browser`
   or you are in an SSH session. Never share the code.
2. Sign in to WunderCorp Portal in the browser and confirm.
3. Back in the terminal: `Signed in as you@example.com.`
   If your default model was `wundercorp/welcome`, a second line names the model your account now
   uses, for example `Default model is now upstage/solar-pro4:free.`

Inference moves to your account's model catalog, paid tools unlock, and `loki auth status`
shows your account instead of the free-tier line.
`wundercorp/welcome` stays with the free tier: an account that was using it lands on the recommended
model for its plan (the same one a fresh `loki model` pick would suggest), and a default model
you chose yourself is left alone. If no recommendation is available at that moment, no default is
set and Loki tells you to run `loki model`.

`/login` in a chat, or `loki auth upgrade` in a terminal, is offered wherever the free tier is
present, including installs that run inference on their own API key. Signing in still unlocks paid
tools for those installs.

:::note Plain login starts fresh
`loki auth add wundercorp --type oauth` also signs you in, but it replaces the free tier outright and
does not carry your connectors over. Use `/login`, or `loki auth upgrade` in a terminal, when
you have connectors you want to keep.
:::

## On Loki Desktop

The desktop app runs on the same free tier as the CLI and shows it in four places:

| Where | What you see |
|---|---|
| First launch | A ready screen: "Loki is ready." with the default model `wundercorp/welcome`, a Free tier badge, and **Begin**. "Sign in with a WunderCorp account instead" and "Other providers" sit under it. The screen shows once. |
| First launch with your own API key already present | A one-time strip above the composer: "Free WunderCorp inference and connectors are now available." with **Open model picker**, **Sign in** and **Dismiss**. |
| Status bar | A chip "WunderCorp · free tier · wundercorp/welcome" with a **Sign in** badge while the free tier carries inference. You can hide it from the bar's right-click menu. |
| Settings › Billing | "You're on the WunderCorp free tier" with one **Sign in** button; the summary reads Plan "Free tier", Model `wundercorp/welcome`, Connectors "Included". There is no balance and nothing to pay, so no payment or usage sections appear. |

Signing in from any of those places opens one dialog. It shows a code and a link; open the link
(or the browser the app opened), confirm in the portal, and the dialog ends with "Signed in as
you@example.com." and the default model your account now uses. A
sign-in you reject in the browser, a code that timed out, or a code replaced by a newer one each
show their own message and leave you on the free tier. The model picker lists the free tier as one
row, "WunderCorp · free tier", with the single model `wundercorp/welcome`; there is no sign-in action inside the
picker.

The desktop reads all of this from the same local state the CLI writes. The ready screen and the
strip are keyed on the same one-time flag the CLI notice uses, so seeing one on the CLI means you
will not see it again on the desktop for that free-tier identity, and the other way round.

## Turning the free tier off

```bash
loki config set wundercorp.guest false
```

`wundercorp.guest` is a normal `config.yaml` setting (default `true`), not an environment variable.
With it off:

| | `wundercorp.guest: true` (default) | `wundercorp.guest: false` |
|---|---|---|
| Free inference on `wundercorp/welcome` | Available | Off |
| Connectors without sign-in | Available | Off |
| Free-tier row in `loki model` | Shown | Hidden |
| Fresh install with nothing configured | Chats immediately | Offered `loki setup` |
| Signing in with a WunderCorp account | Works | Works |

Nothing else changes. A signed-in WunderCorp account, your own API keys, and every other provider work
exactly as before. Set it back to `true` and the free tier returns on the next command that
needs it.

## What `loki logout` does

| Situation | Result |
|---|---|
| Only the free tier is present | Nothing is cleared. Loki prints: `You're not signed in. Free inference and connectors are always on. Run loki auth to sign in with a WunderCorp account.` |
| Signed in with a WunderCorp account | The sign-in is removed from this profile and from the shared store, so no other profile on this machine picks it back up. With `wundercorp.guest: true` the install returns to the free tier at its next start. |
| Another provider is active | Unchanged behaviour: that provider's stored credential is cleared. |

There is no command to reset or recreate the free tier. It is created once and looks after
itself.

## Troubleshooting

| Symptom | What it means | What to do |
|---|---|---|
| First command prints `It looks like Loki isn't configured yet` and offers `loki setup` | The free tier could not be set up within a few seconds: you are offline, or the free tier is not open on the portal Loki is pointed at, or it is rate limited. | Come back online and run the command again, or run `loki setup` and add a provider of your own. Nothing is left half-configured. |
| `WunderCorp free tier is not open on this portal.` | The portal Loki is pointed at is not offering the free tier right now. If you set `LOKI_PORTAL_BASE_URL`, that portal may not have it at all. | Sign in with an account, unset a portal override you no longer need, or add your own key with `loki setup`. |
| `WunderCorp free tier is rate limited; try again shortly.` | The portal is throttling new free-tier setups at the moment. | Wait a few minutes and retry, or add your own key with `loki setup`. |
| `This needs a WunderCorp account.` | You called a paid Tool Gateway tool on the free tier. | `/login` in a chat, `loki auth upgrade` in a terminal, or configure that tool with your own key in `loki tools`. |
| Model picker shows only `wundercorp/welcome` under WunderCorp | Expected on the free tier. | Sign in for the full catalog, or add an API key for another provider. |
| The free tier stopped working after two weeks away | The free-tier identity expired (see below) and is replaced at the next start, or the next time a turn or connector finds it retired. | Nothing; start Loki again. Connectors linked before the gap need to be linked again unless you had signed in. |

## Privacy

To make the free tier work, Loki creates an identity on the WunderCorp portal the first time it
needs one and stores the credential in your Loki directory, shared across the profiles under
that directory. That identity holds no email address, no name, and no other personal data; it
exists so inference and connector calls can be authenticated and rate limited. It expires after
14 days without use, at which point Loki transparently creates a new one the next time you run
a command. Signing in (`/login`, or `loki auth upgrade` in a terminal) moves what that identity
holds (your linked connectors) into your account. Turning the free tier off with
`wundercorp.guest: false` means no identity is created or used at all.

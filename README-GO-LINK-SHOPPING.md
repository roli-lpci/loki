# Loki `/go shopping` + Link execution integration

This build adds an execution layer on top of the existing WunderCorp SSO and Link OAuth connection.

## Commands

```text
/sso [status|login|logout]
/link [status|connect|disconnect|user|payment-methods]
/wallet                         alias for /link
/go                             list workflow modes
/go shopping                    activate the shopping workflow
/go status                      show the current workflow
/go off                         leave the workflow mode
```

`/go shopping` enables `terminal`, `browser`, and `link-wallet`, selects Browser Use, starts a fresh session, injects shopping-specific runtime instructions, and makes sure the Link wallet is connected. If WunderCorp SSO or Link authorization is missing, the normal browser authorization flow opens automatically.

## Model-callable Link tools

The `link-wallet` toolset contains:

```text
link_wallet_status
link_wallet_user_info
link_wallet_payment_methods
link_wallet_shipping_addresses
link_spend_create
link_spend_request_approval
link_spend_get
link_spend_wait
link_spend_cancel
link_checkout_fill
```

The expected purchase sequence is:

```text
browser_exec
  -> browse merchant
  -> cart
  -> checkout
  -> determine exact final total

link_spend_create
  -> create spend request for that exact total

link_spend_request_approval
  -> user approves through Link

link_spend_wait / link_spend_get
  -> confirm approved

link_checkout_fill
  -> backend retrieves the approved one-time card
  -> Loki injects it directly into the active checkout over supervised CDP
  -> raw card number/CVC never enter model context

browser_exec
  -> re-check merchant/items/shipping/total
  -> submit checkout
```

## Browser fix

`/browser use on` now enables both `browser` and its `terminal` prerequisite. Previously it could announce that Browser Use was enabled while `browser_exec` was removed from the model tool surface because `terminal` was not enabled.

## Payment credential boundary

`link_checkout_fill` deliberately does not return the Link credential to the model. It retrieves `/api/link/spend-requests/{id}/credential?type=card` inside the tool process, registers the secret values with Loki's model-egress redaction boundary, classifies the active checkout fields, and injects the credential through the existing supervised browser CDP channel.

The tool result includes only safe metadata such as the page origin, number of filled fields, and field tokens.

## Extending `/go`

Workflow definitions live in:

```text
loki_cli/go_workflows.py
```

Add another `GoWorkflow` to `WORKFLOWS` to introduce modes such as travel, booking, research, deployment, or another task-specific bundle without adding more root commands.

## Toolset activation fix

`link-wallet` is a first-class configurable built-in toolset. `/go shopping` now verifies that every required toolset was actually enabled before resetting the session or reporting ready. If a required toolset cannot be enabled, the command stops and reports the missing toolset instead of continuing with a partial execution surface.

## Business operations mode

This build also includes `/ops` and `/go ops`. `/ops` is independent of Link and activates a broad business-operations tool contract for finance, sales, CRM, leads, operations, inventory, people/HR, hiring, customers, marketing, projects, and risk. See `README-OPS-SUITE.md`.

## If `/go shopping` says `Unknown toolset 'link-wallet'`

That message means the `loki` executable is importing an older installed source tree. The current build registers `link-wallet` as a configurable toolset and `/go shopping` fails closed if its browser/Link runtime tools are absent.

From this repository, run:

```bash
bash ./scripts/reinstall-current-loki.sh
```

Then fully quit/restart Loki. The script re-points the environment behind the current `loki` executable at this source tree and verifies the relevant implementation before returning success.

# LokiAgent Business Operations Mode

`/ops` is a cross-functional business operating mode built on LokiAgent's existing tools rather than a vendor-specific business stack.

## Quick start

```text
/ops setup Single-site gas station and convenience store in Virginia; 8 employees; fuel, c-store, car wash, and lottery revenue.
/ops
```

`/ops` starts the default `overview` lens in a fresh session. The business description is persisted in `config.yaml` as non-secret context. It is not treated as live business data.

## Lenses

```text
/ops overview
/ops finance
/ops sales
/ops leads
/ops crm
/ops operations
/ops inventory
/ops people
/ops hiring
/ops customers
/ops marketing
/ops projects
/ops risk
```

Useful aliases include `accounting` -> `finance`, `efficiency` -> `operations`, `hr` -> `people`, `recruiting` -> `hiring`, `compliance` -> `risk`, and `dashboard` -> `overview`.

`/ops status` shows whether the mode is active, the current lens, profile status, and available lenses. `/ops profile` displays the persisted business description. `/ops clear-profile` removes it. `/ops off` leaves the mode in a fresh session while keeping enabled tools available.

`/go ops` activates the same operating mode using the configured default lens. `/go shopping` remains a separate workflow and explicitly enables `link-wallet`; `/ops` does not require Link.

## Tool contract

Ops mode enables these existing toolsets:

```text
terminal
file
web
browser
code_execution
skills
todo
memory
session_search
connections
cronjob
```

Browser Use is selected as the browser backend. The mode deliberately does not assume a particular accounting, CRM, HRIS, POS, payroll, or support vendor. Loki can work with connected services, browser sessions, uploaded/exported files, terminal-accessible data, and web research according to what the user actually has.

## Operating model

The prompt requires Loki to treat each KPI as a data contract: period, unit, source, formula, and whether the value is observed, calculated, estimated, or missing. It must not invent business data. The mode emphasizes decision-useful metrics, root causes, leading indicators, constraints, and actions rather than generic dashboards.

For a fuel/convenience business, examples include gallons sold, fuel margin per gallon, total fuel gross profit, street-price spread, inside-store sales and margin, transactions, basket size, foodservice/car-wash contribution, fuel inventory and delivery timing, wet-stock variance, shrink, stockouts, pump uptime, labor hours, gross profit per labor hour, overtime, loyalty, and chargebacks. Equivalent business-model-specific drivers are derived for other industries.

People and hiring work uses job-relevant structured criteria. Accounting, tax, legal, payroll, safety, and regulatory work is framed as operational analysis with jurisdiction/professional-review uncertainty surfaced where appropriate. Irreversible external actions require clear authorization.

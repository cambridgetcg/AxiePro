# AxiePro — Honest State (2026-06-04)

AxiePro reads the Ronin chain to value Axies by traits/genes and surface **undervalued
deals**. It is **read-only and non-custodial** — it never touches anyone's funds.

This file is the single source of truth for where the project actually is. The other
~22 root status docs are frozen debugging snapshots that contradict each other — trust
this one, archive those.

## Status at a glance

| Component | Claimed | Actual | Evidence |
|---|---|---|---|
| Backend API | live | **DOWN** — `api.axiepro.io/health` → HTTP 000 | map probe 2026-06-04 |
| Deploys | shipping | last commit **2026-02-02**; ~10 prior were schema-firefighting | `git log` |
| DB schema | one model | **three incompatible** (SQL files vs `run_migrations.py` vs ORM) | ORM references nonexistent `axie.axies` |
| Valuation (hedonic OLS) | live | **not wired** — queries tables in no migration; falls back to a class-average guess | `deal_detector.py` (`discount*1.5`) |
| Trait/gene metadata | populated | **0.3%** (146 / 49,277 axies) | `DATA_INTEGRITY_REPORT.md` |
| USD prices | live FX | **frozen** at hardcoded $3800 ETH / $0.15 RON; `exchange_rates` never written | `sales_ingestion.py` |
| Gene parser | correct | **256-bit parser on 512-bit genes** — silently wrong on real data | `gene_parser.py` |
| Frontend Breeding/Explorer/Market | shipped | **"Coming Soon" shells** | `axiepro/src` pages |
| Secrets | safe | **live SkyMavis + GoldRush keys were committed** (untracked 2026-06-04 — must ROTATE) | `infrastructure/apprunner-service.json` |

## What genuinely works / has value
- ~89K-row **sales dataset** with full buyer/seller addresses (real asset)
- The hedonic OLS valuation **model code** (sound — just not wired to real data)
- The Next.js design system + **working trader pages**: valuation lookup, deals UI,
  portfolio P&L with wallet-signature auth

## 🔴 Security — do this first
Live API keys were committed to git history (and already pushed). Untracking the file
does **not** undo that. **Rotate the SkyMavis + GoldRush keys now**, confirm the live
RDS security group is not open to `0.0.0.0/0`, then scrub git history. See the 2026-06-04 briefing.

## The path forward — one connected chain
The entire product rests on a single fix: make deal-discovery *true*.

1. **Collapse to ONE schema** (+ a CI/startup contract test) so queries stop silently returning empty.
2. **One-time gene/trait backfill scoped to currently-listed axies** — escapes the 0.3%-coverage trap; genes are immutable, so fetch once.
3. **Fix `exchange_rates`** so USD is real, not a frozen guess.
4. **One fair-value function**; compute every deal as `(fair_value − price) / fair_value`, and show the "why" (estimate + comparables) to both the human card *and* an agent API.

Then: Breeding ROI (backend already exists), one typed API envelope, staging + smoke gate.

## Regulatory note (read-only changes everything)
AxiePro never custodies funds or moves money, so MiCA / AML-KYC / custody / money-transmission
regimes **do not bind it**. Real obligations are small: respect SkyMavis + Moralis API
Terms (rate limits, redistribution), carry a clear **"informational, not financial advice"**
disclaimer, and secure its own keys. Don't build exchange-grade compliance for a data tool.

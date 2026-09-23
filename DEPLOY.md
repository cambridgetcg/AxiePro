# Deploying AxiePro

Two parts: the **frontend** (Next.js → Vercel) and the **backend** (FastAPI → AWS App
Runner). This covers the frontend + DNS. Reviving the backend is separate — see `STATE.md`.

The frontend production build is **verified green** (`cd axiepro && npm run build`).

## Frontend → Vercel

The app lives in the `axiepro/` subdirectory.

**One-time setup (yours — needs your Vercel + GitHub login):**

1. **Unarchive the repo.** github.com/cambridgetcg/AxiePro → Settings → "Unarchive".
   It's archived (read-only) right now, so you can't push or connect Vercel until you do.
2. **Import to Vercel.** vercel.com → New Project → import `cambridgetcg/AxiePro`.
   - **Root Directory: `axiepro`** ← important, the app is in a subfolder
   - Framework: Next.js (auto-detected)
3. **Set environment variables** in Vercel:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://api.axiepro.io/api/v1` |
   | `NEXT_PUBLIC_RONIN_NETWORK` | `mainnet` |
   | `NEXT_PUBLIC_DEBUG` | `false` |
   | `NEXT_PUBLIC_LOG_LEVEL` | `error` |

4. **Deploy.**

**Or via CLI** (run these yourself — they use your own Vercel login):

```bash
cd axiepro
npx vercel link     # connect to your Vercel project
npx vercel --prod   # deploy
```

## DNS → Cloudflare

Point the domain at Vercel from your Cloudflare dashboard:

- `axiepro.io` → Vercel (the CNAME/A record Vercel shows you, e.g. `cname.vercel-dns.com`)
- `www.axiepro.io` → same
- **Leave `api.axiepro.io` alone** — it points at the backend (App Runner).

⚠️ DNS changes affect the live domain. Change one record at a time and verify each.

## Backend (separate task)

`api.axiepro.io` is down (see `STATE.md`). Reviving it: rotate the leaked keys first, then
redeploy to App Runner via the existing `.github/workflows/deploy-backend.yml`.


## Legacy Cloudflare Pages surface

The `axiepro` Pages project (`axiepro.pages.dev`) was previously published from
commit `cd25c0c14083c15ccafc6234131fcd19ffaa9a60` under the former `frontend/` path.
Its source is now `axiepro/`. Build the same maintained app as a static export:

```sh
cd axiepro
AXIEPRO_STATIC_EXPORT=1 NEXT_PUBLIC_API_URL=https://api.axiepro.io/api/v1 npm run build
wrangler pages deploy out --project-name=axiepro --branch=main
```

Vercel uses the normal build with no export flag. Publishing either frontend does
not revive, migrate or modify the separate backend. New paid plans and checkout
are retired; model and portfolio observations remain available for understanding.

# AxiePro: brand

This folder holds AxiePro's brand kit, made with storytold's Craft apps through the artcraft-brand skill (the private
repository `cambridgetcg/brandkit`). `brandkit.json` records this project's details, and `check.mjs` checks them.

## The look

The site's existing look, as an agent read it on 2026-10-27: a flat redraw of `public/logo-simple.svg`. The A's
violet-to-cyan gradient is flattened to #408FE3, and the A keeps its cyan #06B6D4 and violet #8B5CF6 dots. The icons
sit on `logo-icon.svg`'s #0F0F14 tile, the wordmark is Inter SemiBold, and the pages are dark only, on #05050D. The
agent was Claude Code session dd025d89, working under Yu's delegation of 2026-10-20. Yu's word of 2026-10-27 ("yes,
go ahead and wire the kits into the sites") approved wiring the kits into the sites; it did not choose this look. The
record is AxiePro PR #3 (merge 9b38f9e), section "Look decisions", and the decisions ledger item
`artcraft-estate-wiring`.

Don't change the identity without its owner's word. Every asset here records who made it in `CREDITS.md`.

## What is here

| Path | What it is |
|---|---|
| `brandkit.json` | this project's details: the look and who chose it, the kit, the files the site serves, what a deploy does |
| `kit/` | the built kit. Never edit it by hand. `kit/BRAND.md` is its guide |
| `kit/source/brand.json` | the generator's input, kept inside the kit (the kit rebuilds from it) |
| `kit/source/mark-source.svg`, `mark-small.svg` | the mark, and its 16-48 px cut without the inner highlight |
| `CREDITS.md` | who made what, with fonts and their licences |
| `check.mjs` | the check, copied from brandkit; update it there, not here |

## Rebuild

From this folder, on a Mac with the Craft CLIs and Inter Light installed:

```sh
cd kit && VECTORCRAFT_NO_PREFS=1 python3 ~/.kingdom/tools/artcraft-brand/scripts/brandkit.py source/brand.json --out . --rebuild-check
```

Then copy the kit files that `brandkit.json` lists under `serve.files` into `../public`:

```sh
for f in favicon.ico favicon.svg apple-touch-icon.png icon-192.png icon-512.png icon-maskable-512.png site.webmanifest og.jpg; do
  cp "kit/web/$f" ../public/
done
```

Then, from `axiepro/` (the app's folder):

```sh
npm run test:brand    # node brand/check.mjs
```

## How the site uses it

Next.js app router, in the repository's `axiepro/` folder. The eight kit files above are served from `public/`.
`src/app/layout.tsx` sets `metadataBase` (`https://www.axiepro.io`), `metadata.icons`, `manifest`, `openGraph.images`
(`SHARE_CARD` from `src/lib/share-card.ts`, the kit's `og.jpg` with its alt text) and `viewport` (`themeColor:
"#05050D"`, `colorScheme: "dark"`). `src/app/globals.css` keeps this folder out of Tailwind's class scan
(`@source not "../../brand";`). The repository has no unit-test runner, so Frontend CI runs `npm run test:brand` as a plain step. Nothing checks
the head tags Next.js writes; PR #3 checked the built head by hand.

## Deploying

A merge to `main` deploys production: Vercel's Git integration builds `axiepro/` and serves https://www.axiepro.io
(the apex redirects to www). Vercel answers `cache-control: public, max-age=0, must-revalidate`, and its edge cache
is per deployment, so nothing needs purging. After a deploy, check the served files and head tags per the skill's
`references/wiring.md` §7.

The legacy Cloudflare Pages copy, axiepro.pages.dev, is not updated by a merge. It still served the template favicon
on 2026-11-05. Updating it means `DEPLOY.md`'s hand `wrangler pages deploy`, which uses Yu's Cloudflare login.

Frontend CI runs `npm run test:brand`, then `tsc` and the build. A merge needs Yu's word, or the repository
owner's, for that merge. Adding the check to CI is a new gate, which is also the owner's call. The backend is down and deploys by hand only (`STATE.md`); nothing in this folder touches it.

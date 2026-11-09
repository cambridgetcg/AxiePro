# Credits

Who made each asset, with what, and under which licence. Where an agent made something, the line says so, and
anything published under Yu's accounts carries that through. If an asset's maker isn't known, write "not recorded"
rather than guessing.

## Assets

| Asset | Made by | Date | Tools | Notes |
|---|---|---|---|---|
| kit/ (generated) | agent (Claude Code session dd025d89), on the Studio | 2026-10-27 | artcraft-brand brandkit.py 1.8 (skill commit f81d80c), vectorcraft-cli 0.17.0 | SOURCE_DATE_EPOCH 1793094342; verify 272 checks, 0 failed, 6 warnings; a rebuild gave 71 byte-identical files (PR #3) |
| kit/source/mark-source.svg, mark-small.svg | the same agent | 2026-10-27 | by hand | a flat redraw of `public/logo-simple.svg`, same geometry; the small cut leaves out the inner highlight |
| `public/logo-simple.svg`, `logo-icon.svg`, `logo.svg` (the original logo the kit redraws) | an agent: commit cad7e87 carries "Generated with Claude Code" and "Co-Authored-By: Claude Opus 4.5", under the git name "Yu" | 2025-12-15 | by hand (SVG) | "Add minimalistic logo and update branding". Who chose the A is not recorded beyond that commit |

## Fonts

| Family | File | Licence | Source | SHA-256 |
|---|---|---|---|---|
| Inter SemiBold | bundled with vectorcraft-cli | SIL Open Font License 1.1 | https://github.com/rsms/inter | (bundled) |
| Inter Light | an installed copy: `Inter-Light.otf` or `InterVariable.ttf` (which one was not recorded) | SIL Open Font License 1.1 (both files' name tables). `kit/BRAND.md` says this licence "was not checked"; that line is older than this check | https://github.com/rsms/inter | not recorded |
| JetBrains Mono Regular | bundled with vectorcraft-cli | SIL Open Font License 1.1 | https://github.com/JetBrains/JetBrainsMono | (bundled) |

The wordmark and the card's text are outlined, so no font file is committed or served.

## Images and other material

| Item | Maker | Licence | Source |
|---|---|---|---|
| none: the kit uses no photographs or third-party artwork | | | |

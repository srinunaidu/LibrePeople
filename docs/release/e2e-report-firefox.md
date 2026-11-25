# Browser E2E Report — Firefox — 2026-11-25

Branch `agent/qa/firefox-e2e` from `2b7652f`. Synthetic data only, no push.
Chromium baseline (same base commit family): 100 desktop + 16 responsive = 116 passed.

## 1. Install

`npx playwright install firefox` from `frontend/` (NO `--with-deps`):
Playwright 1.64.1, Firefox 157.0 (build v1555), download OK, exit 0.

## 2. Host launcher caveat (environmental, not product)

The pinned Firefox 157 (v1555) cannot start on this macOS host
(arm64, macOS 27.2.1, console GUI session present):
- headless: parent exits 1 immediately with `Could not find profile
  folder` — reproduced with/without `-profile`, fresh/stale HOME,
  sandbox disabled, screenshot mode. No `profiles.ini` involvement;
  `firefox --version` and headed launches without automation work.
- headed via Playwright (`-juggler-pipe`): parent exits 1; once a child
  was observed SIGKILLed (`process … exited on signal 9`). No
  `DiagnosticReports` crash entry. AMFI logs `Unrecoverable CT signature
  issue` for the adhoc-signed bundle (the identically-signed Chromium
  bundle runs fine, so this alone does not explain it).
- CLI override impossible: `npx playwright test --browser=firefox`
  errors (`Cannot use --browser option when configuration file defines
  projects`), so minimal `firefox-desktop` + `firefox-responsive`
  projects (Desktop Firefox device, responsive match) were added to
  `frontend/playwright.config.ts` — existing projects untouched.

Workaround for this host only: Firefox 159.0 (build v1572, the
Playwright 1.65.1 pin) was downloaded (`install firefox` via the 1.65.1
CLI, exit 0; no `--with-deps`, no sudo) and starts cleanly headless. The
repo's 1.64.1 driver automates it fully (probe: launch/nav/evaluate/
viewport/screenshot/close all OK). Suite runs below used a same-directory
scratch config (`playwright.firefox1572.config.ts`, deleted before commit)
that inherits the repo config and only pins `executablePath` to the v1572
binary. Engine under test: Gecko 159.0 (device UA override still reports
rv:157.0 per the Desktop Firefox descriptor).

## 3. Runs

`KARMA_PYTHON=$(which python3) npx playwright test --config
playwright.firefox1572.config.ts` (suite self-manages SQLite backend
`:8010` + `vite preview :4173`; guard blocks production hosts).

| Run | Result |
|---|---|
| Full suite, pre-fix | 108 passed, 8 failed (5.6m) |
| Full suite, post-fix (final) | **112 passed, 4 failed** (4.5m) |

Per-spec failures, final run (all in `redesign-e2e.spec.ts:334`, one per
tenant page — tenant-branding, locale-config, entitlements, user-admin):
each reports console error(s) `downloadable font: download failed …
status=2152398850 (0x804B0002) source: https://fonts.gstatic.com/…`
for Space Grotesk / JetBrains Mono woff2. No failed API requests and no
app-code console errors in any Firefox test; screenshots show the pages
rendered correctly on fallback fonts.

Console errors / failed network: only the font-asset errors above.
Failure screenshots + traces retained under `frontend/test-results/`.

## 4. Defects fixed (spec-only; no product change)

Both were spec races the Firefox schedule exposes; the product renders
identically in both browsers (verified: same URL, same DOM — 0 tablists /
h1 `Integrations` at `/platform/integrations` in both; same screenshots).

1. `frontend/e2e/frontend-truth.spec.ts:68` — after clicking the
   "Platform" tab the test asserted `tab[Platform]` aria-selected=true,
   but `/platform/integrations` renders `IntegrationsHub` (no tablist),
   so the assertion can only pass before React commits the navigation.
   Chromium wins that race (8 tabs still mounted immediately after the
   URL change); Firefox commits first (0 tabs). Fix: dropped the stale
   assertion + comment; the URL + `Webhooks` heading + reload assertions
   keep the test's intent (wrong tab → wrong address). Re-ran on Firefox:
   passes (2.7s).
2. `frontend/e2e/responsive.spec.ts:137` (all 4 widths) — single Tab
   pressed ~50ms after `goto("/dashboard")`, racing the lazy `Dashboard`
   chunk behind Suspense (`App.tsx:41,176`): the keypress lands in a
   document with no tab stops and focus never leaves body. Fix: wait for
   `#main-content` visible first (the settle idiom the sibling overflow
   test uses). Re-ran on Firefox: 4/4 pass (~1s each, was 10s timeouts).

Not product defects, no product files touched: skip-link markup/CSS is a
standard offscreen pattern (isolation probe: a minimal page focuses the
link first-Tab in both browsers); tab routing is identical in both.

## 5. NOT TESTED / remainder

- The 4 tenant-config zero-error assertions fail only on the
  third-party font fetch: environmental network flakiness in this
  sandbox (Wi-Fi IPv6 unconfigured — `IPv6 IP address: none` — host
  dual-stack; direct font GET and `document.fonts.load` succeed in the
  same Firefox build outside the blip windows; `curl` 200 in 0.14s;
  Chromium passes the identical tests). Nothing in the product controls
  `fonts.gstatic.com` reachability. Re-run in a clean-network window
  should go 116/116; not masked with harness tweaks (no suite reduction,
  no skips).
- Pinned-build note: results above are Gecko 159 (v1572 binary) driven
  by the repo's Playwright 1.64.1, because the pinned v1555 binary cannot
  launch on this host. Re-run on a host where v1555 starts to confirm
  parity.
- Same NOT-TESTED as Chromium baseline: helpdesk ticket create — no
  helpdesk feature exists in `frontend/src` and no spec covers it.

## 6. Chromium regression (spec edits)

- `frontend-truth.spec.ts` (desktop): 6/6 passed (21.9s), exit 0
- responsive skip link (responsive project, 4 widths): 4/4 passed (15.4s), exit 0
- `redesign-e2e` tenant-branding (desktop): passed (2.0s) — pre-edit file,
  confirms font blip is Firefox-run-specific.

## 7. Cleanup

- Deleted scratch: `frontend/playwright.firefox1572.config.ts`,
  `frontend/.e2e/ffprobe.mjs`, `zz-*.spec.ts`, probe logs/screenshots,
  extracted trace dirs. `frontend/.e2e/` (git-ignored) left with only the
  suite DB.
- Servers: suite webServers shut down with the runs; verified no
  `e2e_server`/`vite preview` processes remain and ports 8010/4173 closed.
- `git status`: only `frontend/playwright.config.ts`,
  `frontend/e2e/frontend-truth.spec.ts`,
  `frontend/e2e/responsive.spec.ts` modified + this new report file.

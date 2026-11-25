# i18n keys inventory (India-first foundation)

Single source of truth for the locale/timezone/currency keys the frontend
formats with. No new runtime dependency; no migration; no payroll math.

## Defaults

| Key        | Default        | Defined in                  |
| ---------- | -------------- | --------------------------- |
| `locale`   | `en-IN`        | `src/lib/format.ts` (`DEFAULT_LOCALE`) |
| `timezone` | `Asia/Kolkata` | `src/lib/format.ts` (`DEFAULT_TIME_ZONE`) |
| `currency` | `INR`          | `src/lib/format.ts` (`DEFAULT_CURRENCY`) |

`en-IN` gives lakh digit grouping (`1,00,000`); `Asia/Kolkata` is the
default timestamp zone; `INR` renders `₹`.

## Wrappers (`src/lib/format.ts`)

All never throw — bad locale/currency/timezone or bad input falls back to
safe defaults, then to the raw value / `—`.

| Helper           | Purpose                                              |
| ---------------- | ---------------------------------------------------- |
| `formatNumber`   | grouped number, optional fraction digits             |
| `formatCurrency` | money with symbol; unknown currency → INR            |
| `formatDate`     | date-only stays on its calendar day (no TZ shift)    |
| `formatDateTime` | timestamp in the tenant timezone                     |

Tests: `src/lib/format.test.ts` (lakh grouping, invalid input, currency /
locale fallback, date handling).

## Tenant settings (`TenantContext`)

`TenantInfo` carries `locale`, `timezone`, `currency`, populated from
`GET /onboarding-portal/clients/by-slug/:slug` and defaulted to the table
above when the server omits them. Consumers: `useTenant()` →
`tenant?.locale / tenant?.timezone / tenant?.currency`.

## Consumers

| Screen                                   | Uses                                              |
| ---------------------------------------- | ------------------------------------------------- |
| `pages/Reports.tsx`                      | labour-cost + total via `formatCurrency` (tenant currency); audit timestamps via tenant locale/timezone |
| `pages/Recruiting.tsx`                   | offer salary via `formatCurrency` (tenant currency) |
| `pages/payroll/shared.tsx`               | `money`/`hours`/`days`/`fmtDate`/`fmtDateTime` delegate to `format.ts`; `moneyIn(value, currency)` adds the symbol |
| `pages/payroll/PayRuns.tsx`              | create-form currency defaults INR; run list shows `run.currency ?? tenant ?? INR` |
| `pages/payroll/PayRunDetail.tsx`         | rule-pack/currency line shows `run.currency ?? tenant ?? INR` |
| `pages/ClientOnboarding.tsx`             | new-client defaults `en-IN`/`Asia/Kolkata`/`INR`; profile has editable Currency (PUT `currency`) |

## Server contract (already exists, unchanged)

`Client` (`backend/app/models/client_onboarding.py`) stores `locale`,
`timezone`, `currency` (ISO 4217), `date_format`, `working_week`;
`ClientCreate`/`ClientUpdate` accept them; seeds set tenant-level
`currency`/`timezone`/`locale`.

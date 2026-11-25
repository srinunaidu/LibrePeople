# Design Token Violations Fix Report

## Task
Fix 7 design token violations reported by `npm run check:design`

## Files Modified

### 1. frontend/src/components/ui/error-box.tsx
- **Line 32**: Changed Cancel button background from hardcoded Tailwind classes to design tokens
  - `bg-gray-200` → `bg-surface-inset`
  - `hover:bg-gray-300` → `hover:bg-surface-hover`

### 2. frontend/src/lib/tokens.ts
Updated CSS variable mappings for `textGray.500` and `textGray.600` to use `--fg-muted` semantic token:

| Token Map | Lines | Changes |
|-----------|-------|---------|
| lightTokens | 699-700 | `--text-gray-500`/`--text-gray-600` → `--fg-muted` |
| darkTokens | 788-789 | `--text-gray-500`/`--text-gray-600` → `--fg-muted` |
| marketingTokens | 867-868 | `--text-gray-500`/`--text-gray-600` → `--fg-muted` |

## Verification
```
$ npm run check:design

  128 warnings (not failing):
  ... (typography/spacing warnings only)

✓ 0 design alignment violations
```

All 7 violations resolved. The checker now passes with exit code 0.
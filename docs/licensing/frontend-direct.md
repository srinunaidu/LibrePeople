# Frontend direct dependencies — licensing SBOM

Source: `frontend/package.json` (`dependencies` + `devDependencies`).
Resolved versions and licence fields are taken from `frontend/package-lock.json`
(`packages["node_modules/<name>"].license`) and are **citable to the lock file**.
Entries showing UNVERIFIED have no `license` field in the lock entry.

## dependencies (24)

| Package | Range | Lock-resolved | Lock licence |
|---|---|---|---|
| @radix-ui/react-checkbox | ^1.4.1 | 1.4.1 | MIT |
| @radix-ui/react-dialog | ^1.3.1 | 1.3.1 | MIT |
| @radix-ui/react-dropdown-menu | ^2.2.1 | 2.2.1 | MIT |
| @radix-ui/react-label | ^2.1.17 | 2.1.17 | MIT |
| @radix-ui/react-popover | ^1.3.1 | 1.3.1 | MIT |
| @radix-ui/react-progress | ^1.2.1 | 1.2.1 | MIT |
| @radix-ui/react-slot | ^1.5.0 | 1.5.0 | MIT |
| @radix-ui/react-switch | ^1.4.1 | 1.4.1 | MIT |
| @radix-ui/react-tabs | ^1.2.1 | 1.2.1 | MIT |
| @radix-ui/react-tooltip | ^1.4.1 | 1.4.1 | MIT |
| @tanstack/react-query | ^5.59.0 | 5.104.4 | MIT |
| @tanstack/react-table | ^8.21.3 | 8.21.3 | MIT |
| @tanstack/react-virtual | ^3.14.21 | 3.14.21 | MIT |
| axios | ^1.7.7 | 1.20.0 | MIT |
| class-variance-authority | ^0.7.1 | 0.7.1 | Apache-2.0 |
| clsx | ^2.1.1 | 2.1.1 | MIT |
| cmdk | ^1.1.1 | 1.1.1 | MIT |
| date-fns | ^4.4.0 | 4.4.0 | MIT |
| lucide-react | ^1.59.0 | 1.59.0 | ISC |
| react | ^18.3.1 | 18.3.1 | MIT |
| react-dom | ^18.3.1 | 18.3.1 | MIT |
| react-router-dom | ^6.26.2 | 6.30.6 | MIT |
| sonner | ^2.0.8 | 2.0.8 | MIT |
| tailwind-merge | ^2.5.2 | 2.6.1 | MIT |

## devDependencies (19)

| Package | Range | Lock-resolved | Lock licence |
|---|---|---|---|
| @axe-core/playwright | ^4.14.0 | 4.14.0 | MPL-2.0 |
| @playwright/test | ^1.64.1 | 1.64.1 | Apache-2.0 |
| @testing-library/jest-dom | ^7.0.1 | 7.0.1 | MIT |
| @testing-library/react | ^16.3.3 | 16.3.3 | MIT |
| @types/react | ^18.3.11 | 18.3.31 | MIT |
| @types/react-dom | ^18.3.1 | 18.3.7 | MIT |
| @typescript-eslint/eslint-plugin | ^8.72.2 | 8.72.2 | MIT |
| @typescript-eslint/parser | ^8.72.2 | 8.72.2 | MIT |
| @vitejs/plugin-react | ^4.3.2 | 4.7.0 | MIT |
| autoprefixer | ^10.4.20 | 10.6.1 | MIT |
| eslint | ^9.39.5 | 9.39.5 | MIT |
| eslint-plugin-react | ^7.37.5 | 7.37.5 | MIT |
| eslint-plugin-react-hooks | ^5.2.0 | 5.2.0 | MIT |
| happy-dom | ^21.0.4 | 21.0.4 | MIT |
| postcss | ^8.4.47 | 8.5.30 | MIT |
| tailwindcss | ^3.4.14 | 3.4.19 | MIT |
| typescript | ^5.6.3 | 5.9.3 | Apache-2.0 |
| vite | ^5.4.10 | 5.4.21 | MIT |
| vitest | ^2.1.9 | 2.1.9 | MIT |

Note: `lucide-react` is ISC, `@axe-core/playwright` is MPL-2.0 (test-only,
not shipped). No LICENSE/NOTICE file is published by this document.

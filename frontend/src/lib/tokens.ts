/**
 * Unified Design Token Contract
 * Single source of truth for all design tokens across the application shell
 * and marketing pages. Both CSS files should reference this contract.
 *
 * @packageDocumentation
 */

/* ============================================================================
 * RAW COLOR SCALES
 * These are the base color ramps. Semantic tokens reference these.
 * ========================================================================== */

export const colorScales = {
  /** Primary brand blue */
  brand: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
    950: '#172554',
  },

  /** Teal/cyan accent */
  teal: {
    50: '#ecfeff',
    100: '#cffafe',
    200: '#a5f3fc',
    300: '#67e8f9',
    400: '#22d3ee',
    500: '#06b6d4',
    600: '#0891b2',
    700: '#0e7490',
  },

  /** Growth/success green */
  green: {
    50: '#ecfdf5',
    100: '#d1fae5',
    200: '#a7f3d0',
    300: '#6ee7b7',
    400: '#34d399',
    500: '#10b981',
    600: '#059669',
    700: '#047857',
  },

  /** Intelligence violet */
  violet: {
    50: '#f5f3ff',
    100: '#ede9fe',
    200: '#ddd6fe',
    300: '#c4b5fd',
    400: '#a78bfa',
    500: '#8b5cf6',
    600: '#7c3aed',
    700: '#6d28d9',
  },

  /** Neutral gray scale (light-theme oriented) */
  gray: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
    950: '#020617',
  },

  /** Marketing-specific dark navy scale (tinted, not slate) */
  marketingGray: {
    50: '#0a1122',
    100: '#101a30',
    200: '#1a2540',
    300: '#2b3a5c',
    400: '#55658a',
    500: '#7e8db0',
    600: '#a3b0cc',
    700: '#c2cde4',
    800: '#dbe2f2',
    900: '#0b1224',
    950: '#060b16',
  },

  /** Status colors */
  status: {
    error: '#b91c1c',
    errorLight: '#fef2f2',
    errorBorder: '#fecaca',
    errorText: '#b91c1c',
    warning: '#d97706',
    warningLight: '#fffbeb',
    warningBorder: '#fde68a',
    warningText: '#92400e',
    success: '#10b981',
    successLight: '#ecfdf5',
    successBorder: '#a7f3d0',
    successText: '#047857',
    info: '#2563eb',
    infoLight: '#eff6ff',
    infoBorder: '#bfdbfe',
  },

  /** Marketing-specific status tints (dark) */
  marketingStatus: {
    errorLight: '#2a1216',
    errorBorder: '#5c1d24',
    successLight: '#052e22',
    successBorder: '#0a5c3f',
    warningLight: '#2b1c04',
    warningBorder: '#6b4a0a',
    infoLight: '#0d1a38',
    infoBorder: '#1b3a7e',
  },
} as const;

/* ============================================================================
 * SEMANTIC TOKENS — LIGHT THEME (App Shell)
 * ========================================================================== */

export const lightSemantic = {
  /* Surfaces */
  surface: '#ffffff',
  surfaceRaised: '#ffffff',
  surfaceSunken: '#f1f5f9',
  surfaceInset: '#f1f5f9',
  surfaceHover: '#f1f5f9',

  /* Table-specific surfaces (light) */
  tableHeaderBg: '#c7d2e4',
  tableStripedBg: '#c7d2e4',
  tableHoverBg: '#bcc9e2',

  /* Brand surfaces */
  brandSoft: '#eff6ff',
  brandSoftFg: '#1d4ed8',
  brandText: '#2563eb',

  /* Foregrounds */
  fg: '#111827',
  fgMuted: '#475569',
  fgSubtle: '#475569',
  fgInverse: '#ffffff',
  fgOnBrand: '#ffffff',
  fgLink: '#2563eb',

  /* Borders */
  borderSubtle: '#c0cddf',
  borderDefault: '#c0cddf',
  borderStrong: '#475569',

  /* Focus */
  focusRing: '#2563eb',
  focusRingOffset: '#ffffff',

  /* Text aliases (map to gray scale for light theme) */
  textGray: {
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
  },
  textSlate: {
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
  },

  /* Status text (readable on light) */
  errorText: '#b91c1c',
  successText: '#047857',
  tealText: '#0e7490',
  greenText: '#047857',
  violetText: '#6d28d9',
  warningText: '#92400e',

  /* Status surfaces (light) */
  errorLight: '#fef2f2',
  errorBorder: '#fecaca',
  successLight: '#ecfdf5',
  successBorder: '#a7f3d0',
  warningLight: '#fffbeb',
  warningBorder: '#fde68a',
  infoLight: '#eff6ff',
  infoBorder: '#bfdbfe',

  /* Ring */
  ringSubtle: '0 0 0 1px rgba(15, 23, 42, 0.06)',

  /* Color scheme */
  colorScheme: 'light' as const,
} as const;

/* ============================================================================
 * SEMANTIC TOKENS — DARK THEME (App Shell)
 * ========================================================================== */

export const darkSemantic = {
  /* Surfaces — TradeMarkk obsidian */
  surface: '#15151C',
  surfaceRaised: '#1C1C26',
  surfaceSunken: '#0B0B0F',
  surfaceInset: '#0F0F14',
  surfaceHover: '#1C1C26',

  /* Table-specific surfaces (dark) */
  tableHeaderBg: '#15151C',
  tableStripedBg: '#121217',
  tableHoverBg: '#1C1C26',

  /* Brand surfaces — purple accent tint */
  brandSoft: 'rgba(124, 92, 255, 0.14)',
  brandSoftFg: '#C4B5FD',
  brandText: '#C4B5FD',

  /* Foregrounds */
  fg: '#F1F5F9',
  fgMuted: '#94A3B8',
  fgSubtle: '#94A3B8',
  fgInverse: '#0B0B0F',
  fgOnBrand: '#ffffff',
  fgLink: '#A78BFA',

  /* Borders */
  borderSubtle: '#1F1F27',
  borderDefault: '#1F1F27',
  borderStrong: '#2A2A35',

  /* Focus */
  focusRing: '#7C5CFF',
  focusRingOffset: '#0B0B0F',

  /* Text aliases (remapped for dark) */
  textGray: {
    400: '#94a3b8',
    500: '#94a3b8',
    600: '#94a3b8',
    700: '#f1f5f9',
    800: '#f1f5f9',
    900: '#f1f5f9',
  },
  textSlate: {
    400: '#94a3b8',
    500: '#94a3b8',
    600: '#94a3b8',
    700: '#f1f5f9',
  },

  /* Status text (readable on dark) */
  errorText: '#fca5a5',
  successText: '#6ee7b7',
  tealText: '#67e8f9',
  greenText: '#6ee7b7',
  violetText: '#c4b5fd',
  warningText: '#fcd34d',

  /* Status surfaces (dark) — 14% tints of the TradeMarkk status fills */
  errorLight: 'rgba(248, 113, 113, 0.14)',
  errorBorder: 'rgba(248, 113, 113, 0.28)',
  successLight: 'rgba(52, 211, 153, 0.14)',
  successBorder: 'rgba(52, 211, 153, 0.28)',
  warningLight: 'rgba(251, 191, 36, 0.14)',
  warningBorder: 'rgba(251, 191, 36, 0.28)',
  infoLight: '#0B2545',
  infoBorder: '#1D4ED8',

  /* Ring */
  ringSubtle: '0 0 0 1px rgba(148, 163, 184, 0.07)',

  /* Color scheme */
  colorScheme: 'dark' as const,
} as const;

/* ============================================================================
 * SEMANTIC TOKENS — MARKETING (Dark-first, Premium)
 * ========================================================================== */

export const marketingSemantic = {
  /* Brand ramps (marketing-specific deep tints) */
  brand: {
    50: '#0d1a38',
    100: '#142a58',
    200: '#1b3a7e',
    300: '#93c5fd', // inherited from base brand-300 for text
    400: '#bfdbfe',
    500: '#dbeafe',
    600: '#eff6ff',
    700: '#f0f7ff',
    800: '#f7fafd',
    900: '#fbfdff',
    950: '#feffff',
  },
  teal: {
    50: '#062230',
    100: '#073042',
    200: '#0a4a5c',
    300: '#67e8f9', // inherited from base teal-300 for text
    400: '#a5f3fc',
    500: '#cffafe',
    600: '#ecfeff',
    700: '#f0fdff',
    800: '#f7feff',
    900: '#fbfeff',
    950: '#feffff',
  },
  green: {
    50: '#052e22',
    100: '#073527',
    200: '#0a4a36',
    300: '#6ee7b7', // inherited from base green-300 for text
    400: '#a7f3d0',
    500: '#d1fae5',
    600: '#ecfdf5',
    700: '#f0fdf7',
    800: '#f7fdf9',
    900: '#fbfdfd',
    950: '#feffff',
  },
  violet: {
    50: '#221047',
    100: '#2a1656',
    200: '#3d1f7a',
    300: '#c4b5fd', // inherited from base violet-300 for text
    400: '#ddd6fe',
    500: '#ede9fe',
    600: '#f5f3ff',
    700: '#f8f6ff',
    800: '#fbf8ff',
    900: '#fdfcff',
    950: '#feffff',
  },

  /* Text-safe aliases */
  tealText: '#67e8f9',
  greenText: '#6ee7b7',
  violetText: '#c4b5fd',
  warningText: '#fcd34d',
  successText: '#34d399',

  /* Neutrals (tinted navy) */
  gray: {
    50: '#0a1122',
    100: '#101a30',
    200: '#1a2540',
    300: '#2b3a5c',
    400: '#55658a',
    500: '#7e8db0',
    600: '#a3b0cc',
    700: '#c2cde4',
    800: '#dbe2f2',
    900: '#0b1224',
    950: '#060b16',
  },

  /* Text aliases */
  textGray: {
    400: '#55658a',
    500: '#7e8db0',
    600: '#a3b0cc',
    700: '#c2cde4',
    800: '#dbe2f2',
    900: '#dbe2f2',
  },
  textSlate: {
    400: '#55658a',
    500: '#7e8db0',
    600: '#a3b0cc',
    700: '#c2cde4',
  },

  /* Status tints (dark) */
  errorLight: '#2a1216',
  errorBorder: '#5c1d24',
  successLight: '#052e22',
  successBorder: '#0a5c3f',
  warningLight: '#2b1c04',
  warningBorder: '#6b4a0a',
  infoLight: '#0d1a38',
  infoBorder: '#1b3a7e',

  /* Semantic surfaces */
  surface: '#0d1526',
  surfaceRaised: '#111b31',
  surfaceSunken: '#070c18',
  surfaceInset: '#0a1224',
  surfaceHover: '#131e36',

  /* Brand surfaces */
  brandSoft: '#142a58',
  brandSoftFg: '#bfdbfe',
  brandText: '#93c5fd',

  /* Foregrounds */
  fg: '#e9eefb',
  fgMuted: '#9fadc9',
  fgSubtle: '#7d8bab',
  fgInverse: '#0d1526',
  fgLink: '#6ea5ff',

  /* Borders (glass-and-ring idiom) */
  borderSubtle: 'rgba(148, 163, 184, 0.12)',
  borderDefault: 'rgba(148, 163, 184, 0.18)',
  borderStrong: 'rgba(148, 163, 184, 0.30)',

  /* Focus */
  focusRing: '#3b82f6',
  focusRingOffset: '#0d1526',

  /* Ring */
  ringSubtle: '0 0 0 1px rgba(148, 163, 184, 0.07)',

  /* Color scheme */
  colorScheme: 'dark' as const,
} as const;

/* ============================================================================
 * TYPOGRAPHY TOKENS
 * ========================================================================== */

export const typography = {
  fontFamilies: {
    sans: 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif',
    mono: '"JetBrains Mono", "Fira Code", monospace',
    display: '"Space Grotesk", Inter, system-ui, -apple-system, "Segoe UI", sans-serif',
  },

  fontSizes: {
    xs: '0.75rem',     // 12px
    sm: '0.8125rem',   // 13px
    base: '0.875rem',  // 14px
    lg: '0.9375rem',   // 15px
    xl: '1rem',        // 16px
    '2xl': '1.125rem', // 18px
    '3xl': '1.25rem',  // 20px
    '4xl': '1.5rem',   // 24px
    '5xl': '1.875rem', // 30px
    '6xl': '2.25rem',  // 36px
    '7xl': '3rem',     // 48px
    '8xl': '3.75rem',  // 60px
    '9xl': '4.5rem',   // 72px
  },

  fontWeights: {
    normal: '400',
    medium: '500',
    semibold: '550',  // Custom weight used in design
    bold: '600',
    extrabold: '700',
    black: '750',     // Custom weight used in design
  },

  lineHeights: {
    tight: '1.02',
    snug: '1.1',
    normal: '1.5',
    relaxed: '1.625',
  },

  letterSpacing: {
    tighter: '-0.035em',
    tight: '-0.03em',
    normal: '-0.01em',
    wide: '0.02em',
    wider: '0.06em',
    widest: '0.18em',
  },
} as const;

/* ============================================================================
 * SPACING TOKENS
 * Based on 4px base unit
 * ========================================================================== */

export const spacing = {
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  7: '1.75rem',   // 28px
  8: '2rem',      // 32px
  9: '2.25rem',   // 36px
  10: '2.5rem',   // 40px
  11: '2.75rem',  // 44px
  12: '3rem',     // 48px
  14: '3.5rem',   // 56px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
  28: '7rem',     // 112px
  32: '8rem',     // 128px
} as const;

/* ============================================================================
 * RADIUS TOKENS
 * ========================================================================== */

export const radius = {
  none: '0',
  sm: '8px',
  md: '8px',
  lg: '16px',
  xl: '20px',
  '2xl': '24px',
  full: '9999px',
  card: '18px',        // Marketing card radius
  window: '20px',      // Marketing window mockup radius
} as const;

/* ============================================================================
 * SHADOW TOKENS
 * ========================================================================== */

export const shadows = {
  /** Light theme shadows — soft, diffused, ring-based */
  light: {
    ringSubtle: '0 0 0 1px rgba(15, 23, 42, 0.06)',
    sm: '0 1px 3px rgba(15, 23, 42, 0.06), 0 4px 12px rgba(15, 23, 42, 0.04), 0 0 0 1px rgba(15, 23, 42, 0.06)',
    md: '0 4px 16px rgba(15, 23, 42, 0.07), 0 12px 32px -8px rgba(15, 23, 42, 0.08), 0 0 0 1px rgba(15, 23, 42, 0.06)',
    lg: '0 8px 24px rgba(15, 23, 42, 0.08), 0 16px 48px -12px rgba(15, 23, 42, 0.10), 0 0 0 1px rgba(15, 23, 42, 0.06)',
    xl: '0 16px 40px rgba(15, 23, 42, 0.10), 0 24px 64px -16px rgba(15, 23, 42, 0.12), 0 0 0 1px rgba(15, 23, 42, 0.06)',
  },

  /** Dark theme shadows (app shell) */
  dark: {
    ringSubtle: '0 0 0 1px rgba(148, 163, 184, 0.07)',
    sm: '0 1px 2px rgba(2, 6, 16, 0.5), 0 4px 16px rgba(2, 6, 16, 0.35), 0 0 0 1px rgba(148, 163, 184, 0.07)',
    md: '0 4px 14px rgba(2, 6, 16, 0.55), 0 12px 36px -10px rgba(2, 6, 16, 0.55), 0 0 0 1px rgba(148, 163, 184, 0.07)',
    lg: '0 8px 24px rgba(2, 6, 16, 0.6), 0 24px 64px -16px rgba(2, 6, 16, 0.6), 0 0 0 1px rgba(148, 163, 184, 0.07)',
    xl: '0 16px 44px rgba(2, 6, 16, 0.65), 0 40px 90px -20px rgba(2, 6, 16, 0.65), 0 0 0 1px rgba(148, 163, 184, 0.07)',
  },

  /** Marketing shadows — deeper, more dramatic */
  marketing: {
    ringSubtle: '0 0 0 1px rgba(148, 163, 184, 0.07)',
    sm: '0 1px 2px rgba(2, 6, 16, 0.5), 0 4px 16px rgba(2, 6, 16, 0.35), 0 0 0 1px rgba(148, 163, 184, 0.07)',
    md: '0 4px 14px rgba(2, 6, 16, 0.55), 0 12px 36px -10px rgba(2, 6, 16, 0.55), 0 0 0 1px rgba(148, 163, 184, 0.07)',
    lg: '0 8px 24px rgba(2, 6, 16, 0.6), 0 24px 64px -16px rgba(2, 6, 16, 0.6), 0 0 0 1px rgba(148, 163, 184, 0.07)',
    xl: '0 16px 44px rgba(2, 6, 16, 0.65), 0 40px 90px -20px rgba(2, 6, 16, 0.65), 0 0 0 1px rgba(148, 163, 184, 0.07)',
    // Marketing-specific glow shadows
    glowPrimary: '0 1px 2px rgba(2, 6, 16, 0.4), 0 8px 28px -6px rgba(37, 99, 235, 0.55)',
    glowPrimaryHover: '0 12px 46px -6px rgba(37, 99, 235, 0.85)',
    cardHover: '0 12px 34px rgba(2, 6, 16, 0.6), 0 22px 60px -18px rgba(37, 99, 235, 0.45)',
    window: '0 0 0 1px rgba(37, 99, 235, 0.10), 0 24px 80px -20px rgba(37, 99, 235, 0.45), 0 40px 120px -30px rgba(2, 6, 16, 0.8)',
    cta: '0 1px 2px rgba(2, 6, 16, 0.5), 0 10px 36px -8px rgba(37, 99, 235, 0.75), inset 0 1px 0 rgba(255, 255, 255, 0.22)',
    ctaHover: '0 12px 46px -6px rgba(37, 99, 235, 0.85)',
    pulse: '0 0 8px rgba(96, 165, 250, 0.9)',
  },
} as const;

/* ============================================================================
 * CHART PALETTE
 * ========================================================================== */

export const charts = {
  palette: [
    '#2563eb', // chart-1: brand blue
    '#06b6d4', // chart-2: teal
    '#8b5cf6', // chart-3: violet
    '#10b981', // chart-4: green
    '#d97706', // chart-5: amber/warning
    '#dc2626', // chart-6: red/error
  ],

  // Semantic chart colors
  semantic: {
    primary: '#2563eb',
    secondary: '#06b6d4',
    tertiary: '#8b5cf6',
    success: '#10b981',
    warning: '#d97706',
    danger: '#dc2626',
  },
} as const;

/* ============================================================================
 * TENANT THEME TOKENS
 * Runtime-overridable via CSS variables set by TenantProvider
 * ========================================================================== */

export const tenant = {
  // Default values (fall back to brand tokens)
  primary: '#2563eb',        // var(--brand-600)
  primaryDark: '#1d4ed8',    // var(--brand-700)
  primaryLight: '#eff6ff',   // var(--brand-50)
  primaryText: '#2563eb',    // var(--brand-600)
  primaryContrast: '#ffffff',
  secondary: '#0f172a',      // var(--gray-900)
} as const;

/* ============================================================================
 * SHELL GEOMETRY TOKENS — TradeMarkk obsidian redesign
 * ========================================================================== */

export const shell = {
  sidebarWidth: '220px',   // var(--sidebar-width)
  topbarHeight: '48px',    // var(--topbar-height)
  accent: '#7C5CFF',       // var(--accent)
  accentHover: '#6A48F5',  // var(--accent-hover)
  accentTint: 'rgba(124, 92, 255, 0.14)', // var(--accent-tint)
} as const;


/* ============================================================================
 * COMPOSITE TOKEN OBJECT
 * ========================================================================== */

export const tokens = {
  colors: colorScales,
  semantic: {
    light: lightSemantic,
    dark: darkSemantic,
    marketing: marketingSemantic,
  },
  typography,
  spacing,
  radius,
  shadows,
  charts,
  tenant,
  shell,
} as const;

/* ============================================================================
 * CSS VARIABLE MAPPINGS
 * These objects map token paths to CSS variable names for programmatic use
 * (e.g., injecting via TenantProvider, generating Tailwind config, etc.)
 * ========================================================================== */

type TokenMap = Record<string, string>;

export const lightTokens: TokenMap = {
  // Brand
  'colors.brand.50': '--brand-50',
  'colors.brand.100': '--brand-100',
  'colors.brand.200': '--brand-200',
  'colors.brand.300': '--brand-300',
  'colors.brand.400': '--brand-400',
  'colors.brand.500': '--brand-500',
  'colors.brand.600': '--brand-600',
  'colors.brand.700': '--brand-700',
  'colors.brand.800': '--brand-800',
  'colors.brand.900': '--brand-900',
  'colors.brand.950': '--brand-950',

  // Teal
  'colors.teal.50': '--teal-50',
  'colors.teal.100': '--teal-100',
  'colors.teal.200': '--teal-200',
  'colors.teal.300': '--teal-300',
  'colors.teal.400': '--teal-400',
  'colors.teal.500': '--teal-500',
  'colors.teal.600': '--teal-600',
  'colors.teal.700': '--teal-700',

  // Green
  'colors.green.50': '--green-50',
  'colors.green.100': '--green-100',
  'colors.green.200': '--green-200',
  'colors.green.300': '--green-300',
  'colors.green.400': '--green-400',
  'colors.green.500': '--green-500',
  'colors.green.600': '--green-600',
  'colors.green.700': '--green-700',

  // Violet
  'colors.violet.50': '--violet-50',
  'colors.violet.100': '--violet-100',
  'colors.violet.200': '--violet-200',
  'colors.violet.300': '--violet-300',
  'colors.violet.400': '--violet-400',
  'colors.violet.500': '--violet-500',
  'colors.violet.600': '--violet-600',
  'colors.violet.700': '--violet-700',

  // Gray
  'colors.gray.50': '--gray-50',
  'colors.gray.100': '--gray-100',
  'colors.gray.200': '--gray-200',
  'colors.gray.300': '--gray-300',
  'colors.gray.400': '--gray-400',
  'colors.gray.500': '--gray-500',
  'colors.gray.600': '--gray-600',
  'colors.gray.700': '--gray-700',
  'colors.gray.800': '--gray-800',
  'colors.gray.900': '--gray-900',
  'colors.gray.950': '--gray-950',

  // Status
  'colors.status.error': '--error',
  'colors.status.errorLight': '--error-light',
  'colors.status.errorBorder': '--error-border',
  'colors.status.errorText': '--error-text',
  'colors.status.warning': '--warning',
  'colors.status.warningLight': '--warning-light',
  'colors.status.warningBorder': '--warning-border',
  'colors.status.warningText': '--warning-text',
  'colors.status.success': '--success',
  'colors.status.successLight': '--success-light',
  'colors.status.successBorder': '--success-border',
  'colors.status.successText': '--success-text',
  'colors.status.info': '--info',
  'colors.status.infoLight': '--info-light',
  'colors.status.infoBorder': '--info-border',

  // Semantic surfaces
  'semantic.light.surface': '--surface',
  'semantic.light.surfaceRaised': '--surface-raised',
  'semantic.light.surfaceSunken': '--surface-sunken',
  'semantic.light.surfaceInset': '--surface-inset',
  'semantic.light.surfaceHover': '--surface-hover',
  'semantic.light.tableHeaderBg': '--table-header-bg',
  'semantic.light.tableStripedBg': '--table-striped-bg',
  'semantic.light.tableHoverBg': '--table-hover-bg',
  'semantic.light.brandSoft': '--brand-soft',
  'semantic.light.brandSoftFg': '--brand-soft-fg',
  'semantic.light.brandText': '--brand-text',

  // Semantic foregrounds
  'semantic.light.fg': '--fg',
  'semantic.light.fgMuted': '--fg-muted',
  'semantic.light.fgSubtle': '--fg-subtle',
  'semantic.light.fgInverse': '--fg-inverse',
  'semantic.light.fgOnBrand': '--fg-on-brand',
  'semantic.light.fgLink': '--fg-link',

  // Semantic borders
  'semantic.light.borderSubtle': '--border-subtle',
  'semantic.light.borderDefault': '--border-default',
  'semantic.light.borderStrong': '--border-strong',

  // Focus
  'semantic.light.focusRing': '--focus-ring',
  'semantic.light.focusRingOffset': '--focus-ring-offset',

  // Text aliases
  'semantic.light.textGray.400': '--text-gray-400',
  'semantic.light.textGray.500': '--fg-muted',
  'semantic.light.textGray.600': '--fg-muted',
  'semantic.light.textGray.700': '--text-gray-700',
  'semantic.light.textGray.800': '--text-gray-800',
  'semantic.light.textGray.900': '--text-gray-900',
  'semantic.light.textSlate.400': '--text-slate-400',
  'semantic.light.textSlate.500': '--text-slate-500',
  'semantic.light.textSlate.600': '--text-slate-600',
  'semantic.light.textSlate.700': '--text-slate-700',

  // Status text
  'semantic.light.errorText': '--error-text',
  'semantic.light.successText': '--success-text',
  'semantic.light.tealText': '--teal-text',
  'semantic.light.greenText': '--green-text',
  'semantic.light.violetText': '--violet-text',
  'semantic.light.warningText': '--warning-text',

  // Ring
  'semantic.light.ringSubtle': '--ring-subtle',

  // Typography
  'typography.fontFamilies.sans': '--font-sans',
  'typography.fontFamilies.mono': '--font-mono',
  'typography.fontSizes.xs': '--font-size-xs',
  'typography.fontSizes.sm': '--font-size-sm',
  'typography.fontSizes.base': '--font-size-base',
  'typography.fontSizes.lg': '--font-size-lg',
  'typography.fontSizes.xl': '--font-size-xl',
  'typography.fontSizes.2xl': '--font-size-2xl',
  'typography.fontSizes.3xl': '--font-size-3xl',
  'typography.fontSizes.4xl': '--font-size-4xl',
  'typography.fontSizes.5xl': '--font-size-5xl',
  'typography.fontSizes.6xl': '--font-size-6xl',
  'typography.fontSizes.7xl': '--font-size-7xl',
  'typography.fontSizes.8xl': '--font-size-8xl',
  'typography.fontSizes.9xl': '--font-size-9xl',

  // Radius
  'radius.sm': '--radius-sm',
  'radius.md': '--radius-md',
  'radius.lg': '--radius-lg',
  'radius.xl': '--radius-xl',
  'radius.2xl': '--radius-2xl',

  // Shadows
  'shadows.light.ringSubtle': '--ring-subtle',
  'shadows.light.sm': '--shadow-sm',
  'shadows.light.md': '--shadow-md',
  'shadows.light.lg': '--shadow-lg',
  'shadows.light.xl': '--shadow-xl',

  // Charts
  'charts.palette.0': '--chart-1',
  'charts.palette.1': '--chart-2',
  'charts.palette.2': '--chart-3',
  'charts.palette.3': '--chart-4',
  'charts.palette.4': '--chart-5',
  'charts.palette.5': '--chart-6',

  // Tenant
  'tenant.primary': '--tenant-primary',
  'tenant.primaryDark': '--tenant-primary-dark',
  'tenant.primaryLight': '--tenant-primary-light',
  'tenant.primaryText': '--tenant-primary-text',
  'tenant.primaryContrast': '--tenant-primary-contrast',
  'tenant.secondary': '--tenant-secondary',

  // Color scheme
  'semantic.light.colorScheme': 'color-scheme',
} as const;

export const darkTokens: TokenMap = {
  // Semantic surfaces (dark overrides)
  'semantic.dark.surface': '--surface',
  'semantic.dark.surfaceRaised': '--surface-raised',
  'semantic.dark.surfaceSunken': '--surface-sunken',
  'semantic.dark.surfaceInset': '--surface-inset',
  'semantic.dark.surfaceHover': '--surface-hover',
  'semantic.dark.brandSoft': '--brand-soft',
  'semantic.dark.brandSoftFg': '--brand-soft-fg',
  'semantic.dark.brandText': '--brand-text',

  // Semantic foregrounds
  'semantic.dark.fg': '--fg',
  'semantic.dark.fgMuted': '--fg-muted',
  'semantic.dark.fgSubtle': '--fg-subtle',
  'semantic.dark.fgInverse': '--fg-inverse',
  'semantic.dark.fgOnBrand': '--fg-on-brand',
  'semantic.dark.fgLink': '--fg-link',

  // Semantic borders
  'semantic.dark.borderSubtle': '--border-subtle',
  'semantic.dark.borderDefault': '--border-default',
  'semantic.dark.borderStrong': '--border-strong',

  // Focus
  'semantic.dark.focusRing': '--focus-ring',
  'semantic.dark.focusRingOffset': '--focus-ring-offset',

  // Text aliases (remapped)
  'semantic.dark.textGray.400': '--text-gray-400',
  'semantic.dark.textGray.500': '--fg-muted',
  'semantic.dark.textGray.600': '--fg-muted',
  'semantic.dark.textGray.700': '--text-gray-700',
  'semantic.dark.textGray.800': '--text-gray-800',
  'semantic.dark.textGray.900': '--text-gray-900',
  'semantic.dark.textSlate.400': '--text-slate-400',
  'semantic.dark.textSlate.500': '--text-slate-500',
  'semantic.dark.textSlate.600': '--text-slate-600',
  'semantic.dark.textSlate.700': '--text-slate-700',

  // Status text (dark)
  'semantic.dark.errorText': '--error-text',
  'semantic.dark.successText': '--success-text',
  'semantic.dark.tealText': '--teal-text',
  'semantic.dark.greenText': '--green-text',
  'semantic.dark.violetText': '--violet-text',
  'semantic.dark.warningText': '--warning-text',

  // Status surfaces (dark)
  'semantic.dark.errorLight': '--error-light',
  'semantic.dark.errorBorder': '--error-border',
  'semantic.dark.successLight': '--success-light',
  'semantic.dark.successBorder': '--success-border',
  'semantic.dark.warningLight': '--warning-light',
  'semantic.dark.warningBorder': '--warning-border',
  'semantic.dark.infoLight': '--info-light',
  'semantic.dark.infoBorder': '--info-border',

  // Ring
  'semantic.dark.ringSubtle': '--ring-subtle',

  // Color scheme
  'semantic.dark.colorScheme': 'color-scheme',

  // Typography
  'typography.fontSizes.xs': '--font-size-xs',
  'typography.fontSizes.sm': '--font-size-sm',
  'typography.fontSizes.base': '--font-size-base',
  'typography.fontSizes.lg': '--font-size-lg',
  'typography.fontSizes.xl': '--font-size-xl',
  'typography.fontSizes.2xl': '--font-size-2xl',
  'typography.fontSizes.3xl': '--font-size-3xl',
  'typography.fontSizes.4xl': '--font-size-4xl',
  'typography.fontSizes.5xl': '--font-size-5xl',
  'typography.fontSizes.6xl': '--font-size-6xl',
  'typography.fontSizes.7xl': '--font-size-7xl',
  'typography.fontSizes.8xl': '--font-size-8xl',
  'typography.fontSizes.9xl': '--font-size-9xl',
} as const;

export const marketingTokens: TokenMap = {
  // Marketing brand ramps
  'semantic.marketing.brand.50': '--brand-50',
  'semantic.marketing.brand.100': '--brand-100',
  'semantic.marketing.brand.200': '--brand-200',
  'semantic.marketing.brand.300': '--brand-300',

  'semantic.marketing.teal.50': '--teal-50',
  'semantic.marketing.teal.100': '--teal-100',
  'semantic.marketing.teal.200': '--teal-200',
  'semantic.marketing.teal.300': '--teal-300',

  'semantic.marketing.green.50': '--green-50',
  'semantic.marketing.green.100': '--green-100',
  'semantic.marketing.green.200': '--green-200',
  'semantic.marketing.green.300': '--green-300',

  'semantic.marketing.violet.50': '--violet-50',
  'semantic.marketing.violet.100': '--violet-100',
  'semantic.marketing.violet.200': '--violet-200',
  'semantic.marketing.violet.300': '--violet-300',

  // Text aliases
  'semantic.marketing.tealText': '--teal-text',
  'semantic.marketing.greenText': '--green-text',
  'semantic.marketing.violetText': '--violet-text',
  'semantic.marketing.warningText': '--warning-text',
  'semantic.marketing.successText': '--success-text',

  // Marketing grays
  'semantic.marketing.gray.50': '--gray-50',
  'semantic.marketing.gray.100': '--gray-100',
  'semantic.marketing.gray.200': '--gray-200',
  'semantic.marketing.gray.300': '--gray-300',
  'semantic.marketing.gray.400': '--gray-400',
  'semantic.marketing.gray.500': '--gray-500',
  'semantic.marketing.gray.600': '--gray-600',
  'semantic.marketing.gray.700': '--gray-700',
  'semantic.marketing.gray.800': '--gray-800',
  'semantic.marketing.gray.900': '--gray-900',
  'semantic.marketing.gray.950': '--gray-950',

  // Text aliases
  'semantic.marketing.textGray.400': '--text-gray-400',
  'semantic.marketing.textGray.500': '--fg-muted',
  'semantic.marketing.textGray.600': '--fg-muted',
  'semantic.marketing.textGray.700': '--text-gray-700',
  'semantic.marketing.textGray.800': '--text-gray-800',
  'semantic.marketing.textGray.900': '--text-gray-900',
  'semantic.marketing.textSlate.400': '--text-slate-400',
  'semantic.marketing.textSlate.500': '--text-slate-500',
  'semantic.marketing.textSlate.600': '--text-slate-600',
  'semantic.marketing.textSlate.700': '--text-slate-700',

  // Status tints
  'semantic.marketing.errorLight': '--error-light',
  'semantic.marketing.errorBorder': '--error-border',
  'semantic.marketing.successLight': '--success-light',
  'semantic.marketing.successBorder': '--success-border',
  'semantic.marketing.warningLight': '--warning-light',
  'semantic.marketing.warningBorder': '--warning-border',
  'semantic.marketing.infoLight': '--info-light',
  'semantic.marketing.infoBorder': '--info-border',

  // Semantic surfaces
  'semantic.marketing.surface': '--surface',
  'semantic.marketing.surfaceRaised': '--surface-raised',
  'semantic.marketing.surfaceSunken': '--surface-sunken',
  'semantic.marketing.surfaceInset': '--surface-inset',
  'semantic.marketing.surfaceHover': '--surface-hover',
  'semantic.marketing.brandSoft': '--brand-soft',
  'semantic.marketing.brandSoftFg': '--brand-soft-fg',
  'semantic.marketing.brandText': '--brand-text',

  // Foregrounds
  'semantic.marketing.fg': '--fg',
  'semantic.marketing.fgMuted': '--fg-muted',
  'semantic.marketing.fgSubtle': '--fg-subtle',
  'semantic.marketing.fgInverse': '--fg-inverse',
  'semantic.marketing.fgLink': '--fg-link',

  // Borders
  'semantic.marketing.borderSubtle': '--border-subtle',
  'semantic.marketing.borderDefault': '--border-default',
  'semantic.marketing.borderStrong': '--border-strong',

  // Focus
  'semantic.marketing.focusRing': '--focus-ring',
  'semantic.marketing.focusRingOffset': '--focus-ring-offset',

  // Ring
  'semantic.marketing.ringSubtle': '--ring-subtle',

  // Typography
  'typography.fontFamilies.display': '--font-display',

  // Color scheme
  'semantic.marketing.colorScheme': 'color-scheme',
} as const;

/* ============================================================================
 * USAGE NOTES
 * ============================================================================
 *
 * 1. TOKEN STRUCTURE
 *    All tokens are exported as `const` assertions for maximum type safety.
 *    Access via: tokens.colors.brand[500], tokens.semantic.light.fg, etc.
 *
 * 2. CSS VARIABLE MAPPINGS
 *    lightTokens, darkTokens, marketingTokens map token paths to CSS variable
 *    names. Use these for:
 *    - Generating Tailwind theme config
 *    - Runtime token injection (TenantProvider)
 *    - Build-time CSS variable generation
 *    - Documentation tooling
 *
 * 3. THEME SCOPING
 *    - App shell light: :root, .light-surface  → lightTokens
 *    - App shell dark: .dark                   → darkTokens (overrides light)
 *    - Marketing: .mkt-root                    → marketingTokens (complete set)
 *
 * 4. TENANT THEMING
 *    Tenant tokens (tenant.*) are runtime-overridable CSS variables.
 *    Default values fall back to brand tokens. TenantProvider sets them
 *    via element.style.setProperty() on the document root.
 *
 * 5. MARKETING DIFFERENCES
 *    Marketing uses a distinct dark-first palette (tinted navy grays,
 *    deeper brand ramps, glass-and-ring shadows, Space Grotesk display font).
 *    These are NOT mere overrides — they're a parallel token set scoped to .mkt-root.
 *
 * 6. SYNCING WITH CSS
 *    When modifying tokens, update BOTH this file AND the corresponding CSS:
 *    - index.css lines 22-199 (light) + 202-268 (dark)
 *    - marketing.css lines 26-119 (.mkt-root)
 *    This file is the contract; CSS is the implementation.
 */

// Type helpers for consumers
export type ColorScales = typeof colorScales;
export type LightSemantic = typeof lightSemantic;
export type DarkSemantic = typeof darkSemantic;
export type MarketingSemantic = typeof marketingSemantic;
export type Typography = typeof typography;
export type Spacing = typeof spacing;
export type Radius = typeof radius;
export type Shadows = typeof shadows;
export type Charts = typeof charts;
export type Tenant = typeof tenant;
export type Shell = typeof shell;
export type Tokens = typeof tokens;
export type LightTokens = typeof lightTokens;
export type DarkTokens = typeof darkTokens;
export type MarketingTokens = typeof marketingTokens;
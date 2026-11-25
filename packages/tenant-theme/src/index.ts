import Color from "color"

export interface TenantBrandInput {
  primary: string
  secondary?: string
  logoUrl?: string
  name: string
}

export interface TenantTheme {
  primary: string
  primaryDark: string
  primaryLight: string
  primaryText: string
  primaryContrast: string
  secondary: string
  cssVariables: Record<string, string>
  warnings: string[]
}

const WCAG_AA_NORMAL = 4.5
const WCAG_AA_LARGE = 3.0

function luminance(hex: string): number {
  const rgb = Color(hex).rgb().array().map((v) => v / 255)
  return rgb.map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))).reduce((a, b) => a * 0.2126 + b * 0.7152 + 0.0722, 0)
}

function contrastRatio(color1: string, color2: string): number {
  const l1 = luminance(color1)
  const l2 = luminance(color2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

function findAccessibleTextColor(bgColor: string, targetRatio = WCAG_AA_NORMAL): { color: string; ratio: number } {
  const whiteRatio = contrastRatio(bgColor, "#FFFFFF")
  const blackRatio = contrastRatio(bgColor, "#000000")

  if (whiteRatio >= targetRatio && blackRatio >= targetRatio) {
    return { color: whiteRatio > blackRatio ? "#FFFFFF" : "#000000", ratio: Math.max(whiteRatio, blackRatio) }
  }
  if (whiteRatio >= targetRatio) {
    return { color: "#FFFFFF", ratio: whiteRatio }
  }
  if (blackRatio >= targetRatio) {
    return { color: "#000000", ratio: blackRatio }
  }

  let currentColor = Color(bgColor)
  let bestRatio = 0
  let bestColor = "#FFFFFF"

  for (let i = 0; i < 100; i++) {
    const lighter = currentColor.lighten(0.01 * i).hex()
    const darker = currentColor.darken(0.01 * i).hex()

    const lightRatio = contrastRatio(bgColor, lighter)
    const darkRatio = contrastRatio(bgColor, darker)

    if (lightRatio >= targetRatio && lightRatio > bestRatio) {
      bestRatio = lightRatio
      bestColor = lighter
    }
    if (darkRatio >= targetRatio && darkRatio > bestRatio) {
      bestRatio = darkRatio
      bestColor = darker
    }
  }

  return { color: bestColor, ratio: bestRatio }
}

function findAccessibleBgColor(textColor: string, targetRatio = WCAG_AA_NORMAL): { color: string; ratio: number } {
  const baseColor = Color(textColor)
  let bestRatio = 0
  let bestColor = "#FFFFFF"

  for (let lightness = 0; lightness <= 100; lightness += 1) {
    const testColor = baseColor.lightness(lightness / 100).hex()
    const ratio = contrastRatio(testColor, textColor)

    if (ratio >= targetRatio && ratio > bestRatio) {
      bestRatio = ratio
      bestColor = testColor
    }
  }

  return { color: bestColor, ratio: bestRatio }
}

export function deriveTheme(input: TenantBrandInput): TenantTheme {
  const warnings: string[] = []

  const primary = input.primary
  const secondary = input.secondary || "#0F172A"

  const primaryColor = Color(primary)
  const primaryDark = primaryColor.darken(0.1).hex()
  const primaryLight = primaryColor.lighten(0.85).hex()

  const whiteOnPrimary = contrastRatio(primary, "#FFFFFF")
  const blackOnPrimary = contrastRatio(primary, "#000000")

  let primaryContrast: string
  let primaryText: string

  if (whiteOnPrimary >= WCAG_AA_NORMAL) {
    primaryContrast = "#FFFFFF"
    primaryText = primary
  } else if (blackOnPrimary >= WCAG_AA_NORMAL) {
    primaryContrast = "#000000"
    primaryText = primary
  } else {
    const accessible = findAccessibleTextColor(primary, WCAG_AA_NORMAL)
    primaryContrast = accessible.color
    primaryText = accessible.color === "#FFFFFF" ? primary : "#FFFFFF"

    warnings.push(
      `Primary color ${primary} fails WCAG AA contrast (${whiteOnPrimary.toFixed(2)}:1 on white, ${blackOnPrimary.toFixed(2)}:1 on black). Using ${accessible.color} for on-brand text (${accessible.ratio.toFixed(2)}:1).`
    )
  }

  const whiteOnSecondary = contrastRatio(secondary, "#FFFFFF")
  const blackOnSecondary = contrastRatio(secondary, "#000000")

  if (whiteOnSecondary < WCAG_AA_NORMAL && blackOnSecondary < WCAG_AA_NORMAL) {
    warnings.push(
      `Secondary color ${secondary} fails WCAG AA contrast on both white and black. Consider a darker or lighter shade.`
    )
  }

  const darkSurface = "#0F172A"
  const whiteOnDarkSurface = contrastRatio(darkSurface, "#FFFFFF")
  if (whiteOnDarkSurface < WCAG_AA_NORMAL) {
    warnings.push(`Dark surface ${darkSurface} fails WCAG AA for white text.`)
  }

  const cssVariables: Record<string, string> = {
    "--tenant-primary": primary,
    "--tenant-primary-dark": primaryDark,
    "--tenant-primary-light": primaryLight,
    "--tenant-primary-text": primaryText,
    "--tenant-primary-contrast": primaryContrast,
    "--tenant-secondary": secondary,
  }

  return {
    primary,
    primaryDark,
    primaryLight,
    primaryText,
    primaryContrast,
    secondary,
    cssVariables,
    warnings,
  }
}

export function applyTenantTheme(theme: TenantTheme, element: HTMLElement = document.documentElement): void {
  Object.entries(theme.cssVariables).forEach(([key, value]) => {
    element.style.setProperty(key, value)
  })
  element.dataset.tenant = "true"
}

export function removeTenantTheme(element: HTMLElement = document.documentElement): void {
  Object.keys({
    "--tenant-primary": "",
    "--tenant-primary-dark": "",
    "--tenant-primary-light": "",
    "--tenant-primary-text": "",
    "--tenant-primary-contrast": "",
    "--tenant-secondary": "",
  }).forEach((key) => {
    element.style.removeProperty(key)
  })
  delete element.dataset.tenant
}

export function validateTheme(theme: TenantTheme): { valid: boolean; issues: string[] } {
  const issues: string[] = []

  const whiteOnPrimary = contrastRatio(theme.primary, "#FFFFFF")
  const blackOnPrimary = contrastRatio(theme.primary, "#000000")

  if (whiteOnPrimary < WCAG_AA_NORMAL && blackOnPrimary < WCAG_AA_NORMAL) {
    issues.push(`Primary color ${theme.primary} does not meet WCAG AA on white or black`)
  }

  const whiteOnPrimaryText = contrastRatio(theme.primary, theme.primaryContrast)
  if (whiteOnPrimaryText < WCAG_AA_NORMAL) {
    issues.push(`Primary contrast color ${theme.primaryContrast} does not meet WCAG AA on primary`)
  }

  return { valid: issues.length === 0, issues }
}
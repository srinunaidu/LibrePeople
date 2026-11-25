/** @type {import('tailwindcss').Config} */
import defaultTheme from "tailwindcss/defaultTheme"

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      /* ---- map semantic tokens into the theme ---- */
      colors: {
        // ---- legacy aliases: existing pages use these names ----
        // They point at the same CSS variables as the semantic tokens, so a
        // tenant theme change propagates regardless of which name a page uses.
        primary: {
          DEFAULT: "var(--brand-600)",
          50:  "var(--brand-50)",
          100: "var(--brand-100)",
          200: "var(--brand-200)",
          300: "var(--brand-300)",
          400: "var(--brand-400)",
          500: "var(--brand-500)",
          600: "var(--brand-600)",
          700: "var(--brand-700)",
          800: "var(--brand-800)",
          900: "var(--brand-900)",
        },
        /*
         * `navy` is the foreground ink: it follows the theme so headings
         * stay legible in dark mode. A fixed dark navy was invisible
         * against the dark surfaces. For a dark *surface* use
         * `bg-gray-900`, which is a fixed colour.
         */
        navy: "var(--fg)",
        blue: {
          50:  "var(--brand-50)",
          100: "var(--brand-100)",
          200: "var(--brand-200)",
          300: "var(--brand-300)",
          400: "var(--brand-400)",
          500: "var(--brand-500)",
          600: "var(--brand-600)",
          700: "var(--brand-700)",
          800: "var(--brand-800)",
        },
        red: {
          50:  "var(--error-light)",
          100: "var(--error-light)",
          200: "var(--error-border)",
          // `error-text` is #b91c1c on a light surface and #fca5a5 on a dark
          // one. A fixed #991b1b was dark-red on the dark error surface —
          // 1.84:1 on /mfa's "Disabled" chip.
          500: "var(--error-text)",
          600: "var(--error-text)",
          700: "var(--error-text)",
        },
        rose: {
          50:  "var(--error-light)",
          100: "var(--error-light)",
          600: "var(--error)",
        },
        amber: {
          100: "var(--warning-light)",
          400: "var(--warning)",
          500: "var(--warning)",
          600: "var(--warning)",
        },
        cyan: {
          100: "var(--teal-100)",
          500: "var(--teal-500)",
          600: "var(--teal-600)",
        },
        sky: {
          50:  "var(--brand-50)",
          100: "var(--brand-100)",
          500: "var(--brand-500)",
          600: "var(--brand-600)",
        },
        indigo: {
          50:  "var(--violet-50)",
          100: "var(--violet-100)",
          500: "var(--violet-500)",
          600: "var(--violet-600)",
        },
        slate: {
          100: "var(--gray-100)",
          200: "var(--gray-200)",
          300: "var(--gray-300)",
          400: "var(--gray-400)",
          500: "var(--gray-500)",
          600: "var(--gray-600)",
          700: "var(--gray-700)",
          800: "var(--gray-800)",
          900: "var(--gray-900)",
        },
        teal: {
          50:  "var(--teal-50)",
          100: "var(--teal-100)",
          200: "var(--teal-200)",
          300: "var(--teal-300)",
          400: "var(--teal-400)",
          500: "var(--teal-500)",
          600: "var(--teal-600)",
          700: "var(--teal-700)",
        },

        // ---- semantic tokens ----
        brand: {
          50:  "var(--brand-50)",
          100: "var(--brand-100)",
          200: "var(--brand-200)",
          300: "var(--brand-300)",
          400: "var(--brand-400)",
          500: "var(--brand-500)",
          600: "var(--brand-600)",
          700: "var(--brand-700)",
          800: "var(--brand-800)",
          900: "var(--brand-900)",
          950: "var(--brand-950)",
        },
        teal: {
          50:  "var(--teal-50)",
          100: "var(--teal-100)",
          200: "var(--teal-200)",
          300: "var(--teal-300)",
          400: "var(--teal-400)",
          500: "var(--teal-500)",
          600: "var(--teal-600)",
          700: "var(--teal-700)",
        },
        green: {
          50:  "var(--green-50)",
          100: "var(--green-100)",
          200: "var(--green-200)",
          300: "var(--green-300)",
          400: "var(--green-400)",
          500: "var(--green-500)",
          600: "var(--green-600)",
          700: "var(--green-700)",
        },
        violet: {
          50:  "var(--violet-50)",
          100: "var(--violet-100)",
          200: "var(--violet-200)",
          300: "var(--violet-300)",
          400: "var(--violet-400)",
          500: "var(--violet-500)",
          600: "var(--violet-600)",
          700: "var(--violet-700)",
        },
        gray: {
          50:  "var(--gray-50)",
          100: "var(--gray-100)",
          200: "var(--gray-200)",
          300: "var(--gray-300)",
          400: "var(--gray-400)",
          500: "var(--gray-500)",
          600: "var(--gray-600)",
          700: "var(--gray-700)",
          800: "var(--gray-800)",
          900: "var(--gray-900)",
          950: "var(--gray-950)",
        },
        surface: "var(--surface)",
        "surface-raised": "var(--surface-raised)",
        "surface-sunken": "var(--surface-sunken)",
        "surface-inset": "var(--surface-inset)",
        // The page background, behind the app shell.
        page: "var(--surface-sunken)",
        fg: "var(--fg)",
        "fg-muted": "var(--fg-muted)",
        "fg-subtle": "var(--fg-subtle)",
        "fg-inverse": "var(--fg-inverse)",
        "fg-link": "var(--fg-link)",
        // The default border, used as `border-border`.
        border: "var(--border-default)",
        "border-subtle": "var(--border-subtle)",
        "border-default": "var(--border-default)",
        "border-strong": "var(--border-strong)",
        "focus-ring": "var(--focus-ring)",
        error: "var(--error)",
        "error-text": "var(--error-text)",
        "error-light": "var(--error-light)",
        "error-bg": "var(--error-light)",
        "error-border": "var(--error-border)",
        warning: "var(--warning)",
        "warning-light": "var(--warning-light)",
        "warning-text": "var(--warning-text)",
        success: "var(--success)",
        "success-text": "var(--success-text)",
        "success-light": "var(--success-light)",
        "success-bg": "var(--success-light)",
        "success-border": "var(--success-border)",
        // Secondary text, used as `text-text-secondary`.
        text: {
          secondary: "var(--fg-muted)",
        },
        chart: {
          1: "var(--chart-1)",
          2: "var(--chart-2)",
          3: "var(--chart-3)",
          4: "var(--chart-4)",
          5: "var(--chart-5)",
          6: "var(--chart-6)",
        },
      },

      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },

      /* ---- typography scale ----
         Marketing uses display/h1-large. The app uses the smaller app-scale
         so dense data screens stay readable. Both map here. */
      fontSize: {
        // marketing scale
        "display": ["56px", { lineHeight: "64px", fontWeight: "700", letterSpacing: "-0.02em" }],
        "h1": ["44px", { lineHeight: "52px", fontWeight: "700", letterSpacing: "-0.02em" }],
        "h2": ["32px", { lineHeight: "40px", fontWeight: "600", letterSpacing: "-0.01em" }],
        "h3": ["24px", { lineHeight: "32px", fontWeight: "600", letterSpacing: "-0.01em" }],
        // app scale — modern: bolder, tighter tracking (Linear idiom)
        "h1-app": ["28px", { lineHeight: "36px", fontWeight: "700", letterSpacing: "-0.03em" }],
        "h2-app": ["20px", { lineHeight: "28px", fontWeight: "650", letterSpacing: "-0.02em" }],
        "h3-app": ["16px", { lineHeight: "24px", fontWeight: "650", letterSpacing: "-0.015em" }],
        body: ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "body-sm": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        caption: ["12px", { lineHeight: "16px", fontWeight: "500" }],
      },

      /* ---- spacing (4px base) ---- */
      spacing: {
        4.5: "18px",
        5.25: "21px",
        15: "3.75rem",
        18: "4.5rem",
        88: "22rem",
      },

      /* ---- radius ---- */
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        "2xl": "var(--radius-2xl)",
      },

      /* ---- shadows ---- */
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
      },

      /* ---- container ---- */
      maxWidth: {
        container: "1280px",
      },

      /* ---- z-index scale ---- */
      zIndex: {
        base: 0,
        raised: 10,
        dropdown: 1000,
        sticky: 1100,
        overlay: 1300,
        modal: 1400,
        toast: 1700,
        tooltip: 1800,
      },

      /* ---- animation ---- */
      animation: {
        "fade-in": "fade-in 150ms ease-out",
        "slide-in": "slide-in 150ms ease-out",
        "scale-in": "scale-in 100ms ease-out",
        "shimmer": "shimmer 1.5s ease-in-out infinite",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-in": { from: { transform: "translateX(-8px)", opacity: "0" }, to: { transform: "translateX(0)", opacity: "1" } },
        "scale-in": { from: { transform: "scale(0.96)", opacity: "0" }, to: { transform: "scale(1)", opacity: "1" } },
        "shimmer": { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
      },
    },
  },
  plugins: [],
}
import type { Config } from "tailwindcss";

/**
 * Tokens are defined once as CSS variables in `src/app/globals.css` and given
 * readable names here. Change a hex in globals.css; the name below stays put.
 * This is why you write `bg-panel` / `text-up` / `border-line` in components
 * instead of raw hex values.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Channel vars + <alpha-value> so `bg-up/40` etc. compose correctly.
        ink: "rgb(var(--ink) / <alpha-value>)",
        panel: "rgb(var(--panel) / <alpha-value>)",
        "panel-2": "rgb(var(--panel-2) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        "line-2": "rgb(var(--line-2) / <alpha-value>)",
        fg: "rgb(var(--fg) / <alpha-value>)",
        "fg-dim": "rgb(var(--fg-dim) / <alpha-value>)",
        "fg-mute": "rgb(var(--fg-mute) / <alpha-value>)",
        up: "rgb(var(--up) / <alpha-value>)",
        down: "rgb(var(--down) / <alpha-value>)",
        hold: "rgb(var(--hold) / <alpha-value>)",
        warn: "rgb(var(--warn) / <alpha-value>)",
        ring: "rgb(var(--ring) / <alpha-value>)",
      },
      fontFamily: {
        // Wired to next/font CSS variables set in layout.tsx.
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        // A deliberate scale — see DESIGN.md §2.
        micro: ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.08em" }],
        "2xs": ["0.75rem", { lineHeight: "1rem" }],
        xs: ["0.8125rem", { lineHeight: "1.15rem" }],
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        base: ["1rem", { lineHeight: "1.5rem" }],
        lg: ["1.25rem", { lineHeight: "1.4rem" }],
        xl: ["1.75rem", { lineHeight: "1.1" }],
        "2xl": ["2.5rem", { lineHeight: "1.05" }],
        "3xl": ["3.5rem", { lineHeight: "1.02" }],
      },
      borderRadius: {
        // Machined, not pill-soft. Never rounded-2xl.
        none: "0",
        sm: "2px",
        DEFAULT: "3px",
        md: "4px",
        lg: "6px",
      },
      spacing: {
        rail: "13.5rem", // left nav width
        strip: "2.75rem", // status strip height
      },
      keyframes: {
        "count-in": {
          from: { opacity: "0", transform: "translateY(2px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "count-in": "count-in 240ms ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;

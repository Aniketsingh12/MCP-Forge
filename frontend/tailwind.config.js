/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Near-black slate canvas — a "forge" workshop feel.
        ink: {
          950: "#0a0b0f",
          900: "#0e1017",
          800: "#151824",
          700: "#1c2030",
          600: "#262b3d",
          500: "#3a4157",
        },
        // Warm amber accent = molten metal / forge fire.
        forge: {
          300: "#fcd9a3",
          400: "#f9b767",
          500: "#f59e0b",
          600: "#d97706",
          700: "#b45309",
        },
        line: "#242a3a",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["Space Grotesk", "Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(245,158,11,0.25), 0 8px 30px -8px rgba(245,158,11,0.25)",
      },
    },
  },
  plugins: [],
};

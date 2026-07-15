import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Institutional-analyst palette: deep slate-navy ledger, not a generic dark theme.
        ink: {
          0: "#0d1117", // page background
          1: "#141a23", // panel surface
          2: "#1b232f", // raised surface / hover
          border: "#2a333f",
        },
        parchment: "#EDEAE1", // primary text — warm off-white, not pure white
        muted: "#8B93A1",
        ledger: {
          DEFAULT: "#2FA89A", // restrained teal accent — used sparingly, as a signal color
          dim: "#1E6B62",
        },
        signal: {
          up: "#4E9E6B",
          down: "#C0604A",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        body: ["var(--font-body)", "sans-serif"],
        data: ["var(--font-data)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;

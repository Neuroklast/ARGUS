import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0E11",
        card: "#141A22",
        accent: "#00B4D8",
        danger: "#C0392B",
        success: "#2ECC71",
        warning: "#F1C40F",
      },
      fontFamily: {
        mono: ["'Roboto Mono'", "monospace"],
      },
    },
  },
};

export default config;

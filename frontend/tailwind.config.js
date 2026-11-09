/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Sora", "Inter", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        // Near-black canvas with Emplay's subtle plum/aubergine undertone
        base: {
          950: "#0A090C",
          900: "#0E0C12",
          850: "#141019",
          800: "#1A1522",
          700: "#241C2F",
        },
        // Emplay brand — muted lavender-purple (restrained, desaturated)
        brand: {
          50: "#f4f1fa",
          100: "#e8e2f5",
          200: "#d4c9ec",
          300: "#c3b6e6",
          400: "#a890d4",
          500: "#8a78c8",
          600: "#7866b8",
          700: "#6557a0",
          800: "#4e4178",
          900: "#352a4e",
        },
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 24px 48px -28px rgba(0,0,0,0.8)",
        glow: "0 0 0 1px rgba(168,144,212,0.16), 0 18px 48px -18px rgba(138,120,200,0.5)",
        "glow-sm": "0 8px 24px -12px rgba(138,120,200,0.55)",
      },
      backgroundImage: {
        // Emplay soft periwinkle-lavender button gradient
        "brand-gradient": "linear-gradient(135deg, #7e6fc0 0%, #9a8ad4 55%, #b0a3e6 100%)",
        "grid-faint":
          "linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(52,211,153,0.5)" },
          "70%": { boxShadow: "0 0 0 6px rgba(52,211,153,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(52,211,153,0)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.16,1,0.3,1) both",
        "fade-in": "fade-in 0.4s ease both",
        shimmer: "shimmer 1.6s infinite",
        "pulse-ring": "pulse-ring 2s cubic-bezier(0.4,0,0.6,1) infinite",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

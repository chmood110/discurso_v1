/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // ===== Design tokens =====
      // Sky / Slate scale comes from Tailwind defaults — we use them as-is.
      // The "brand" palette is preserved from v1 but is no longer the primary accent.
      colors: {
        brand: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          400: "#38bdf8",   // sky-400
          500: "#0ea5e9",   // sky-500 — primary accent
          600: "#0284c7",
          700: "#0369a1",
          900: "#0c4a6e",
        },
        ink: {
          // The deep navy used as the application background.
          DEFAULT: "#020617",
          soft: "#0f172a",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Outfit", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "Plus Jakarta Sans", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "Plus Jakarta Sans", "system-ui", "sans-serif"],
      },
      letterSpacing: {
        // Used by the Section/Eyebrow labels everywhere.
        eyebrow: "0.3em",
        eyebrow_xs: "0.2em",
      },
      keyframes: {
        auroraPan: {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        pulseCore: {
          "0%": { transform: "scale(0.95)", opacity: "0.8" },
          "100%": { transform: "scale(1.05)", opacity: "1" },
        },
        rotate: {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideInBottom: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "aurora-pan": "auroraPan 30s ease-in-out infinite",
        "pulse-core": "pulseCore 2s ease-in-out infinite alternate",
        "spin-slow": "rotate 25s linear infinite",
        "spin-mid": "rotate 15s linear infinite reverse",
        "spin-fast": "rotate 10s linear infinite",
        "fade-in": "fadeIn 700ms ease-out both",
        "fade-in-slow": "fadeIn 1000ms ease-out both",
        "slide-in-bottom": "slideInBottom 700ms cubic-bezier(0.16, 1, 0.3, 1) both",
      },
      backgroundImage: {
        "aurora-navy":
          "linear-gradient(-45deg, #020617, #082f49, #020617, #0f172a)",
        "soft-radial":
          "radial-gradient(circle at 50% -20%, #0f172a 0%, #020617 80%)",
      },
      backgroundSize: {
        "300": "300% 300%",
      },
    },
  },
  plugins: [],
};

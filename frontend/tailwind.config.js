
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      animation: {
        riseFadeOut: "riseFadeOut 2s ease-in-out forwards",
        smoothScaleFadeIn: "smoothScaleFadeIn 0.8s ease forwards",
        shineMove: "shineMove 2.5s linear infinite",
        borderMove: "borderMove 3s linear infinite", // <== added
      },
      keyframes: {
        riseFadeOut: {
          "0%": { transform: "scale(0.6) translateY(0)", opacity: "0.2" },
          "100%": { transform: "scale(3) translateY(-10px)", opacity: "0" },
        },
        smoothScaleFadeIn: {
          "0%": { opacity: "0", transform: "scale(1.05)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shineMove: {
          "0%": { left: "-75%" },
          "100%": { left: "125%" },
        },
        borderMove: {  // <== added keyframes
          "0%, 100%": { borderColor: "#ec4899" }, // pink-500
          "25%": { borderColor: "#fbbf24" },      // yellow-400
          "50%": { borderColor: "#22c55e" },      // green-500
          "75%": { borderColor: "#3b82f6" },      // blue-500
        },
      },
    },
  },
  plugins: [],
};
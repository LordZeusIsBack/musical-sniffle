/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        cream: {
          50: "#FDF8F3",
          100: "#FAF5F0",
          150: "#F7F0E8",
          200: "#F0E8DD",
          300: "#E5DACB",
          400: "#D4C4B0",
        },
        sage: {
          50: "#EAF3EE",
          100: "#D1E5D9",
          200: "#A3CBB3",
          300: "#7BA88F",
          400: "#6B9A7D",
          500: "#5B8C6B",
          600: "#4A7C59",
          700: "#3A6648",
          800: "#2D5239",
        },
        clay: {
          200: "#EDDDD0",
          300: "#E0C4A8",
          400: "#D4A574",
          500: "#C99765",
          600: "#B8824E",
        },
        sky: {
          100: "#E0EDF4",
          200: "#C5DCE8",
          300: "#A3C4D6",
          400: "#8BB8D0",
          500: "#6FA6C2",
        },
        rose: {
          300: "#E8A99E",
          400: "#D4796A",
          500: "#C85D4B",
        },
        charcoal: "#2D2B2A",
        "warm-gray": "#9C928C",
        "warm-gray-light": "#B8AFA9",
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        blob: "30% 70% 70% 30% / 30% 30% 70% 70%",
      },
      animation: {
        "float-slow": "float 8s ease-in-out infinite",
        "pulse-soft": "pulseSoft 4s ease-in-out infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "0.8" },
        },
      },
    },
  },
  plugins: [],
};
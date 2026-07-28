/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7f9", 100: "#eceef2", 200: "#d5d9e2",
          300: "#b0b8c9", 400: "#8591aa", 500: "#647090",
          600: "#4f5977", 700: "#414960", 800: "#383e51",
          900: "#0f1420",
        },
        brand: {
          50: "#eef4ff", 100: "#d9e6ff", 200: "#bcd3ff",
          300: "#8eb6ff", 400: "#598dff", 500: "#3366ff",
          600: "#1f47e6", 700: "#1a37c4", 800: "#1c319f",
          900: "#1c2f7d",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

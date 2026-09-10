/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#7C3AED",
        "on-primary": "#FFFFFF",
        secondary: "#6366F1",
        accent: "#0891B2",
        background: "#0F172A",
        foreground: "#FFFFFF",
        muted: "#171939",
        danger: "#DC2626",
      },
      fontFamily: {
        heading: ["Poppins", "Segoe UI", "sans-serif"],
        body: ["Open Sans", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(124, 58, 237, 0.35)",
      },
    },
  },
  plugins: [],
};

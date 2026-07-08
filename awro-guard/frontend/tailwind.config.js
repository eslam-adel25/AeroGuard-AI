/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        "ag-dark": "#0F172A", // Dark Blue (Main Background)
        "ag-card": "#1E293B", // Card Background
        "ag-primary": "#F8FAFC", // White (Text)
        "ag-success": "#22C55E", // Green (Online)
        "ag-warning": "#EAB308", // Yellow (Medium)
        "ag-danger": "#EF4444", // Red (Critical)
      },
    },
  },
  plugins: [],
};

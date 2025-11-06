/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./backend/templates/**/*.html",
    "./backend/core/templates/**/*.html",
    "./backend/**/*.js",
  ],
  theme: {
    extend: {},
  },
  safelist: [
    {
      pattern: /.*/, // include all classes (for dev only)
    },
  ],
  plugins: [],
}
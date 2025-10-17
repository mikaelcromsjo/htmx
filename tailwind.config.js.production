const defaultTheme = require('tailwindcss/defaultTheme');




module.exports = {
  content: [
    "./backend/templates/**/*.html",
    "./backend/core/templates/**/*.html",
    "./backend/**/*.js",
  ],
  safelist: [
    'bg-red-600',
    'bg-red-700',
    'text-white',
  ],
  theme: {
    extend: {
      colors: {
        primary: "#5B21B6",
        secondary: "#F59E0B",
        accent: "#EC4899",
      },
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
        heading: ['Poppins', ...defaultTheme.fontFamily.sans],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};

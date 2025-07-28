// postcss.config.js
const tailwindcss = require('@tailwindcss/postcss');

module.exports = {
  plugins: [
    require('postcss-import'),
    tailwindcss(),  // Use as a function in Tailwind v4+
    require('autoprefixer'),
  ],
};

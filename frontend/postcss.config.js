// module.exports = {
//   plugins: [
//     require('postcss-import'),
//     require('tailwindcss'),
//     require('autoprefixer'),
//   ],
// };
// const tailwindcss = require('@tailwindcss/postcss');

// module.exports = {
//   plugins: [
//     require('postcss-import'),
//     tailwindcss(),
//     require('autoprefixer'),
//   ],
// };
module.exports = {
  plugins: {
    'postcss-import': {},
    'tailwindcss': {},
    'autoprefixer': {},
  },
};

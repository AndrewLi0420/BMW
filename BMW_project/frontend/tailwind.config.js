/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bmw: {
          blue: '#1c69d4',
          dark: '#0a2d6e',
        },
      },
    },
  },
  plugins: [],
}

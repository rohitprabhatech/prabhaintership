/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#202623',
        muted: '#6f7772',
        canvas: '#f5f6f4',
        line: '#e4e8e4',
        orange: {
          50: '#fff4eb',
          100: '#ffe4d0',
          500: '#e96c27',
          600: '#cf5515',
          700: '#a84414',
        },
      },
      fontFamily: {
        sans: ['DM Sans', 'sans-serif'],
        display: ['Newsreader', 'serif'],
      },
      boxShadow: {
        soft: '0 12px 36px rgba(32, 38, 35, 0.07)',
      },
    },
  },
  plugins: [],
}
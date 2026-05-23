/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#06070f',
        bg2: 'rgba(15,17,32,0.85)',
        accent: '#6366f1',
        accent2: '#8b5cf6',
        text: '#e2e8f0',
        muted: '#94a3b8',
        green: '#6ee7b7',
        red: '#f87171',
      }
    },
  },
  plugins: [],
}

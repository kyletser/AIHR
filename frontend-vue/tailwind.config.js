/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
        display: ['"PingFang SC"', '"Microsoft YaHei"', 'serif'],
      },
      colors: {
        navy: '#0f172a',
        amber: '#f59e0b',
        emerald: '#10b981',
        slate: '#64748b',
        cream: '#fafaf9',
      },
    },
  },
  plugins: [],
}

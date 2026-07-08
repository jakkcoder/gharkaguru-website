/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        tn: {
          primary: '#007BFF',
          primaryDark: '#005FCC',
          success: '#16A34A',
          warning: '#F59E0B',
          error: '#DC2626',
          text: '#111827',
          muted: '#6B7280',
          bg: '#F7F8FA',
          card: '#FFFFFF',
          border: '#E5E7EB',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Roboto', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 1px 2px rgba(0,0,0,0.06), 0 6px 18px rgba(0,0,0,0.06)',
      },
    },
  },
  plugins: [],
}


/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        owner: '#4F46E5',
        tenant: '#0D9488',
        saffron: '#F59E0B',
        success: '#10B981',
        danger: '#E11D48',
        page: '#F6F7FB',
      },
      fontFamily: {
        display: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        soft: '0 8px 30px rgba(15,23,42,.08)',
        'soft-lg': '0 16px 48px rgba(15,23,42,.12)',
      },
      backgroundImage: {
        brand: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #D946EF 100%)',
        'brand-r': 'linear-gradient(to right, #4F46E5, #7C3AED, #D946EF)',
      },
      animation: {
        shimmer: 'shimmer 1.5s infinite',
        'pulse-slow': 'pulse 2.5s cubic-bezier(0.4,0,0.6,1) infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}

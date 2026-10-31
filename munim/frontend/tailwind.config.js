/** Munim design tokens, taken from Paytm's own product: cool grey page, flat white panels, black type,
 * Paytm navy for actions, Paytm sky for highlights. One family (Mukta) for Hindi and English. */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: '#002E6E', 2: '#0A4596', ink: '#001B44' },
        sky: { DEFAULT: '#00BAF2', ink: '#0079C2', soft: '#E5F7FE', softer: '#F2FBFF' },
        gold: { DEFAULT: '#FFC72C', soft: '#FFF5D6', ink: '#7A5300' },
        good: { DEFAULT: '#0E8A4F', soft: '#E3F6EC' },
        bad: { DEFAULT: '#C8262E', solid: '#EF4444', soft: '#FDECEC' },
        ink: '#000000', body: '#2E3440', muted: '#5F6878', faint: '#8F97A6', page: '#F5F7FA', tint: '#F0F3F7', line: '#E4E8EF',
      },
      fontFamily: { sans: ['Mukta', 'system-ui', 'sans-serif'] },
      boxShadow: { card: '0 1px 2px rgba(0,46,110,.05)', lift: '0 10px 28px rgba(0,46,110,.16)' },
      borderRadius: { xl2: '24px' },
    },
  },
  plugins: [],
};

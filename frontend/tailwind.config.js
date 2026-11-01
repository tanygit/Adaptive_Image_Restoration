/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          base: '#fbf8f3',
          card: '#ffffff',
          warm: '#f4ede2',
          muted: '#e8decb',
          border: '#e2d5c3',
        },
        ink: {
          dark: '#141416',
          body: '#2c2d30',
          muted: '#52545b',
          faint: '#5e6168', // Adjusted to meet WCAG AA contrast (≥ 4.5:1 on light paper)
        },
        pop: {
          cyan: '#0062ff',
          magenta: '#ff2d78',
          yellow: '#ffb703',
          green: '#059669',
          amber: '#fb8500',
          violet: '#7c3aed',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'pop': '4px 4px 0px 0px #141416',
        'pop-lg': '6px 6px 0px 0px #141416',
        'pop-sm': '2px 2px 0px 0px #141416',
        'pop-cyan': '4px 4px 0px 0px #0062ff',
        'pop-magenta': '4px 4px 0px 0px #ff2d78',
        'soft': '0 10px 25px -5px rgba(20, 20, 22, 0.06), 0 8px 10px -6px rgba(20, 20, 22, 0.04)',
      }
    },
  },
  plugins: [],
}

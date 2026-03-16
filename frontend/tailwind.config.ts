import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#05070d',
          900: '#0b0f17',
          800: '#111827',
          700: '#1f2937',
          600: '#374151',
          500: '#4b5563',
        },
        nexora: {
          50:  '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
        },
        neon: {
          blue:   '#38bdf8',
          purple: '#a78bfa',
          cyan:   '#22d3ee',
          green:  '#4ade80',
          pink:   '#f472b6',
          orange: '#fb923c',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-blue':   '0 0 20px rgba(56,189,248,0.25), 0 0 40px rgba(56,189,248,0.1)',
        'glow-purple': '0 0 20px rgba(167,139,250,0.25), 0 0 40px rgba(167,139,250,0.1)',
        'glow-cyan':   '0 0 20px rgba(34,211,238,0.25), 0 0 40px rgba(34,211,238,0.1)',
        'glow-green':  '0 0 20px rgba(74,222,128,0.25), 0 0 40px rgba(74,222,128,0.1)',
        'glow-pink':   '0 0 20px rgba(244,114,182,0.25), 0 0 40px rgba(244,114,182,0.1)',
        'card':        '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
      },
      backgroundImage: {
        'dark-gradient': 'linear-gradient(135deg, #05070d 0%, #0b0f17 50%, #111827 100%)',
        'card-gradient': 'linear-gradient(135deg, #0b0f17 0%, #111827 100%)',
        'glow-radial-blue':   'radial-gradient(ellipse at top, rgba(56,189,248,0.12) 0%, transparent 70%)',
        'glow-radial-purple': 'radial-gradient(ellipse at top, rgba(167,139,250,0.12) 0%, transparent 70%)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          from: { boxShadow: '0 0 5px rgba(167,139,250,0.3)' },
          to:   { boxShadow: '0 0 20px rgba(167,139,250,0.6), 0 0 40px rgba(167,139,250,0.2)' },
        },
      },
    },
  },
  plugins: [],
}

export default config

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Sidebar colors
        sidebar: {
          bg: '#1a1a1a',
          hover: '#2a2a2a',
          active: '#333333',
          text: '#ffffff',
          muted: '#888888',
          border: '#333333',
        },
        // Main content
        content: {
          bg: '#ffffff',
          bgAlt: '#f5f5f5',
          bgCard: '#fafafa',
          border: '#e5e5e5',
        },
        // Status badges
        status: {
          complete: '#10B981',
          working: '#3B82F6',
          ready: '#14B8A6',
          draft: '#6B7280',
          error: '#EF4444',
        },
        // Entity type colors (from Figma)
        entity: {
          risk: '#EC4899',
          event: '#EF4444',
          association: '#10B981',
          company: '#14B8A6',
          law: '#3B82F6',
          regulator: '#EC4899',
          official: '#10B981',
        },
        // Hero gradient colors
        hero: {
          from: '#8B5CF6',
          via: '#A855F7',
          to: '#EC4899',
        },
        // Brand accent
        accent: {
          primary: '#8B5CF6',
          secondary: '#EC4899',
        },
      },
      backgroundImage: {
        'hero-gradient': 'linear-gradient(135deg, #8B5CF6 0%, #A855F7 50%, #EC4899 100%)',
      },
    },
  },
  plugins: [],
}

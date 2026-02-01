# EOM Hub Frontend

This directory contains the React+Vite frontend for EOM Hub.

## Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run development server:
   ```bash
   npm run dev
   ```

3. Build for production:
   ```bash
   npm run build
   ```

## Structure

- `src/main.tsx` - Entry point
- `src/App.tsx` - Main application component
- `src/design-system.css` - Core design tokens and global styles
- `src/styles.css` - Component-specific styles
- `src/components/` - Reusable UI components
- `src/types.ts` - TypeScript definitions

## Integration

The frontend is built into the `dist` folder, which is then served by the Python backend (Eel).
The `window.eel` object is used to communicate with the Python backend.

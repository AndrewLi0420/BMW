# Frontend — BMW Battery Pipeline

React SPA for running the pipeline and downloading results. Single main component in `src/App.jsx`.

## Tech Stack

React 18, Vite 5, Tailwind CSS 3
BMW brand colors: `#1c69d4` (blue), `#0a2d6e` (dark blue)

## Commands

```bash
npm run dev    # Dev server → http://localhost:5173 (proxies /api → localhost:8000)
npm run build  # Production build → dist/
npm run preview # Preview production build locally
```

## Structure

```
src/
  App.jsx       # Entire UI — segment selector, run button, download CSV
  main.jsx      # React entry point
  index.css     # Global styles + Tailwind directives
index.html
vite.config.js  # React plugin + /api proxy to :8000
tailwind.config.js
```

## Key Notes

- All API calls go to `/api/*` — Vite proxies to `http://localhost:8000` in dev; in prod, serve both from same origin or update the proxy config.
- The segment list in `App.jsx` must match the 15 segments in `server.py` — update both if segments change.
- No routing library — single page only.
- No state management library — local React state only.

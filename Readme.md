# Personal Website

- Favicon source: https://favicon.io/favicon-generator/
- Font: Assistant

## Getting Started

```
npm install
npm run dev
```

The dev server runs on http://localhost:3000 and hot-reloads changes in `pages/`, `components/`, and `public/`.

## Content

- Home page content lives in `public/data/home.md`.
- Published posts live in `public/data/blogs/*.md`; update `public/data/blogs/index.json` to adjust the list page metadata.
- Draft or private pieces are under `public/data/unpublished_blogs/`.

## Build & Deploy

```
npm run build
```

The build step runs `next build` (configured for static export) and writes the static site to `out/`, then regenerates the sitemap. Deployments run via the GitHub Actions workflow in `.github/workflows/deploy.yml`, or locally via:

```
npm run deploy
```

If the website is not updated in Google Search, request re-indexing from Google Search Console → URL Inspection.

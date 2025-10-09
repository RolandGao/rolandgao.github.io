# Personal Website

- Favicon source: https://favicon.io/favicon-generator/
- Font: Assistant

## Getting Started

```
npm install
npm start
```

The dev server runs on http://localhost:3000 and hot-reloads changes in `src/` and `public/`.

## Content

- Home page content lives in `public/data/home.md`.
- Published posts live in `public/data/blogs/*.md`; update `public/data/blogs/index.json` to adjust the list page metadata.
- Draft or private pieces are under `public/data/unpublished_blogs/`.

## Build & Deploy

```
npm run build
```

The build step emits to `build/` and automatically regenerates the sitemap. Deployments run via the GitHub Actions workflow in `.github/workflows/deploy.yml`.

If the website is not updated in Google Search, request re-indexing from Google Search Console → URL Inspection.

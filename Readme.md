# Personal Website

- Favicon source: https://favicon.io/favicon-generator/
- Font: Assistant
- Canonical URLs have trailing slashes to be most compatible with Github Pages
- Uses Next.js for SSG (Server-side generation) to be SEO-friendly
- Uses Chrome's Lighthouse to verify SEO friendliness
- Uses Google Search Console and URL Inspection to request re-indexing

## Getting Started

```
npm install
npm run dev
```

The dev server runs on http://localhost:3000 and hot-reloads changes in `pages/`, `components/`, and `public/`.

## Content

- Home page content lives in `content/home.md`.
- Published posts live in `content/blogs/*.md`; update `content/blogs/index.json` to adjust the list page metadata. Set `updated` in `YYYY-MM-DD` format whenever a post changes; blog lists are sorted by this field.
- Local-only drafts live in `draft_blogs/*.md`. They are listed at `/blog/`
  during `npm run dev` and served from `/blog/drafts/<filename>/`. Draft routes
  and source files are excluded from production output. Optional display titles
  can be added to `draft_blogs/index.json`.
- Legacy unpublished pieces remain under `unpublished_blogs/`. They stay in the
  repository but are neither routed nor copied into the production site.

## Build & Deploy

```
npm run build
```

The build step runs `next build` (configured for static export) and writes the static site to `out/`, then regenerates the sitemap. Deployments run via the GitHub Actions workflow in `.github/workflows/deploy.yml`, or locally via:

```
npm run deploy
```

If the website is not updated in Google Search, request re-indexing from Google Search Console → URL Inspection.

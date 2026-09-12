# Personal Website

- Favicon source: https://favicon.io/favicon-generator/
- Font: Assistant
- Hosted at https://rolandgao.com on Cloudflare Workers Static Assets
- Canonical URLs have trailing slashes, matching Next.js exports and Cloudflare's HTML handling
- Uses Next.js for SSG (static site generation) so page content and metadata are present in the initial HTML
- Uses Chrome's Lighthouse to verify SEO friendliness
- Uses Google Search Console and URL Inspection to request re-indexing

## Getting Started

Use Node.js 22 or newer (required by the Cloudflare deployment tools).

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

The build step runs `next build` (configured for static export), writes the static site to `out/`, and regenerates `sitemap.xml` and its compatibility alias `sitemap2.xml`. Cloudflare publishes `out/` using `wrangler.jsonc`, which preserves trailing slashes and returns a real 404 for missing pages. `public/_redirects` supplies permanent redirects for renamed articles.

Production builds disable Turbopack's persistent filesystem cache in `next.config.js`. This avoids build failures when Cloudflare partially restores a cached `.next/cache/turbopack` database (for example, `block header truncated` errors in `.sst` files). Production compilation starts fresh each time; development caching keeps its default behavior.

After building, run `npm start` to preview the exported site with Cloudflare's local runtime at http://localhost:8787, including redirect and 404 behavior. A static export cannot be served with `next start`.

For Cloudflare's Git integration, use `npm run build` as the build command and `npx wrangler deploy` as the deploy command. To build and deploy locally with a Cloudflare account authorized for this Worker:

```
npm run deploy
```

`npm run deploy` runs the build first, then deploys to Cloudflare. The GitHub Actions workflow in `.github/workflows/deploy.yml` separately maintains the old GitHub Pages site using `out-github-redirects/`. Keep the GitHub Pages custom domain set to `rolandgao.com` so `rolandgao.github.io` continues to issue native 301 redirects, including deep links. Its hostname-specific JavaScript redirect is only a fallback.

## Domain migration and SEO

- The canonical origin is `https://rolandgao.com`. Page metadata and structured data use `lib/site.js`; the sitemap generator, `public/robots.txt`, and GitHub redirect generator also contain that origin.
- In Cloudflare, add a Single Redirect rule matching `http.host eq "www.rolandgao.com"`, with dynamic destination `concat("https://rolandgao.com", http.request.uri.path)`, status **301**, and **Preserve query string** enabled. Both hostnames currently serve content; this rule consolidates them on the canonical hostname. Workers Static Assets `_redirects` does not support domain-level source matching.
- Keep HTTP → HTTPS redirection enabled and keep the old GitHub Pages domain redirecting for at least a year, preferably indefinitely.
- Verify the old GitHub Pages property and the new domain in Google Search Console, submit the **Change of Address** for the old property, and submit `https://rolandgao.com/sitemap.xml` on the new property. Use URL Inspection to check Google's selected canonical and request indexing when needed.
- After deploying, check that `/robots.txt` includes the sitemap URL, published pages are indexable, `/blog/unsaturated_evals_before_gpt5/` returns a 301, and an unknown URL returns a 404. Drafts and error pages are excluded from the sitemap.
- Cloudflare may add managed AI crawler rules to `robots.txt`. Check the live response as well as the repository file; Google Search crawling should remain allowed.

References: [Google's site migration guide](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes), [Cloudflare static asset redirects](https://developers.cloudflare.com/workers/static-assets/redirects/).

# Legacy website redirect

This repository keeps `https://rolandgao.github.io` redirecting to `https://rolandgao.com`.

GitHub Pages must stay enabled, with its custom domain set to `rolandgao.com`. GitHub supplies the server-side permanent redirect, preserving URL paths. The minimal HTML files provide a browser fallback if the native redirect is temporarily unavailable.

The Pages workflow publishes only `site/`. Website content is maintained separately and deployed to Cloudflare.

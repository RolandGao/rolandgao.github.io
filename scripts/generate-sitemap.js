const fs = require('fs');
const path = require('path');

const domain = 'https://rolandgao.github.io';
const buildPath = path.join(__dirname, '../build');

const pages = [
  '',
  '/blogs',
  '/blog/path_to_agi',
  '/blog/path_tunsaturated_evals_before_gpt5o_agi',
  // Add paths to your blog posts here
];

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemap.org/schemas/sitemap/0.9">
${pages
  .map(
    page => `
  <url>
    <loc>${domain}${page}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`
  )
  .join('\n')}
</urlset>`;

fs.writeFileSync(path.join(buildPath, 'sitemap.xml'), sitemap);
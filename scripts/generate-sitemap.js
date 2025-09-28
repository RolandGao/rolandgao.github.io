const fs = require('fs');
const path = require('path');

const domain = 'https://rolandgao.github.io';
const buildPath = path.join(__dirname, '../build');
const blogDirectory = path.join(__dirname, '../public/data/blogs');

const blogPages = fs.existsSync(blogDirectory)
  ? fs
      .readdirSync(blogDirectory)
      .filter(fileName => path.extname(fileName) === '.md')
      .map(fileName => `/blog/${path.basename(fileName, '.md')}`)
  : [];

const pages = Array.from(
  new Set([
    '/',
    '/blog',
    ...blogPages,
  ])
);

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${pages
  .map(
    page => `
  <url>
    <loc>${domain}${page === '/' ? '/' : page}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`
  )
  .join('\n')}
</urlset>`;

fs.writeFileSync(path.join(buildPath, 'sitemap.xml'), sitemap);

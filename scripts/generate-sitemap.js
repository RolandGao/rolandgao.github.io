const fs = require('fs');
const path = require('path');

const domain = 'https://rolandgao.github.io';
const outputPath = path.join(__dirname, '../out');
const publicPath = path.join(__dirname, '../public');
const blogDirectory = path.join(publicPath, 'data/blogs');
const blogIndexPath = path.join(blogDirectory, 'index.json');

const ensureCanonicalPath = route => {
  if (!route) {
    return '/';
  }

  const looksLikeFile = /\.[a-zA-Z0-9]+$/.test(route);
  if (looksLikeFile) {
    return route;
  }

  const trimmed = route.replace(/\/+$/, '');
  if (!trimmed) {
    return '/';
  }

  const normalized = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
  return `${normalized}/`;
};

const loadBlogPages = () => {
  if (fs.existsSync(blogIndexPath)) {
    try {
      const rawIndex = fs.readFileSync(blogIndexPath, 'utf8');
      const { posts = [] } = JSON.parse(rawIndex);

      return posts
        .map(post => post.path || (post.id ? `/blog/${post.id}/` : null))
        .filter(Boolean);
    } catch (error) {
      console.error('Unable to parse blog index:', error);
    }
  }

  if (fs.existsSync(blogDirectory)) {
    return fs
      .readdirSync(blogDirectory)
      .filter(fileName => path.extname(fileName) === '.md')
      .map(fileName => `/blog/${path.basename(fileName, '.md')}/`);
  }

  return [];
};

const blogPages = loadBlogPages().map(ensureCanonicalPath);
const pages = Array.from(
  new Set([
    ensureCanonicalPath('/'),
    ensureCanonicalPath('/blog/'),
    ...blogPages,
  ])
);

if (!fs.existsSync(outputPath)) {
  console.warn('Skipping sitemap generation because out/ is missing.');
  process.exitCode = 0;
} else {
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${pages
  .map(page => {
    const canonicalPath = ensureCanonicalPath(page);
    const canonicalUrl = canonicalPath === '/' ? `${domain}/` : `${domain}${canonicalPath}`;

    return `
  <url>
    <loc>${canonicalUrl}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`;
  })
  .join('\n')}
</urlset>`;

  fs.writeFileSync(path.join(outputPath, 'sitemap.xml'), sitemap);
}

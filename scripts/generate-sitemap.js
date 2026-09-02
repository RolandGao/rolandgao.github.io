const fs = require('fs');
const path = require('path');

const domain = 'https://rolandgao.github.io';
const outputPath = path.join(__dirname, '../out');
const contentPath = path.join(__dirname, '../content');
const blogDirectory = path.join(contentPath, 'blogs');
const blogIndexPath = path.join(blogDirectory, 'index.json');

const normalizeLastmod = value => {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return null;
  }

  const parsedDate = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(parsedDate.getTime()) ? null : value;
};

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
        .map(post => ({
          route: post.path || (post.id ? `/blog/${post.id}/` : null),
          lastmod: normalizeLastmod(post.updated || post.date),
        }))
        .filter(page => Boolean(page.route));
    } catch (error) {
      console.error('Unable to parse blog index:', error);
    }
  }

  if (fs.existsSync(blogDirectory)) {
    return fs
      .readdirSync(blogDirectory)
      .filter(fileName => path.extname(fileName) === '.md')
      .map(fileName => ({
        route: `/blog/${path.basename(fileName, '.md')}/`,
        lastmod: null,
      }));
  }

  return [];
};

const blogPages = loadBlogPages().map(page => ({
  ...page,
  route: ensureCanonicalPath(page.route),
}));
const latestPostUpdate = blogPages.reduce((latest, page) => {
  if (!page.lastmod || (latest && page.lastmod <= latest)) {
    return latest;
  }

  return page.lastmod;
}, null);
const pagesByRoute = new Map();

[
  { route: ensureCanonicalPath('/'), lastmod: latestPostUpdate },
  { route: ensureCanonicalPath('/blog/'), lastmod: latestPostUpdate },
  ...blogPages,
].forEach(page => {
  if (!pagesByRoute.has(page.route)) {
    pagesByRoute.set(page.route, page);
  }
});

const pages = Array.from(pagesByRoute.values());

if (!fs.existsSync(outputPath)) {
  console.warn('Skipping sitemap generation because out/ is missing.');
  process.exitCode = 0;
} else {
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${pages
  .map(page => {
    const canonicalPath = ensureCanonicalPath(page.route);
    const canonicalUrl = canonicalPath === '/' ? `${domain}/` : `${domain}${canonicalPath}`;
    const lastmod = page.lastmod
      ? `\n    <lastmod>${page.lastmod}</lastmod>`
      : '';

    return `
  <url>
    <loc>${canonicalUrl}</loc>${lastmod}
  </url>`;
  })
  .join('\n')}
</urlset>`;

  fs.writeFileSync(path.join(outputPath, 'sitemap.xml'), sitemap);
  // Some consumers expect sitemap2.xml, so keep it in sync with sitemap.xml.
  fs.writeFileSync(path.join(outputPath, 'sitemap2.xml'), sitemap);
}

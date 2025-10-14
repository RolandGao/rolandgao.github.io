const fs = require('fs');
const path = require('path');

const domain = 'https://rolandgao.github.io';
const buildPath = path.join(__dirname, '../build');
const publicPath = path.join(__dirname, '../public');
const blogDirectory = path.join(publicPath, 'data/blogs');
const blogIndexPath = path.join(blogDirectory, 'index.json');

const loadBlogPages = () => {
  if (fs.existsSync(blogIndexPath)) {
    try {
      const rawIndex = fs.readFileSync(blogIndexPath, 'utf8');
      const { posts = [] } = JSON.parse(rawIndex);

      return posts
        .map(post => post.path || (post.id ? `/blog/${post.id}` : null))
        .filter(Boolean);
    } catch (error) {
      console.error('Unable to parse blog index:', error);
    }
  }

  if (fs.existsSync(blogDirectory)) {
    return fs
      .readdirSync(blogDirectory)
      .filter(fileName => path.extname(fileName) === '.md')
      .map(fileName => `/blog/${path.basename(fileName, '.md')}`);
  }

  return [];
};

const blogPages = loadBlogPages();
const extraSpaRoutes = ['/blog/unsaturated_evals_before_gpt5'];

const pages = Array.from(
  new Set([
    '/',
    '/blog',
    ...blogPages,
  ])
);

if (!fs.existsSync(buildPath)) {
  console.warn('Skipping sitemap generation because build/ is missing.');
  process.exitCode = 0;
} else {
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${pages
  .map(
    page => {
      const looksLikeFile = /\.[a-zA-Z0-9]+$/.test(page);
      const canonicalPath =
        page === '/' || looksLikeFile
          ? page
          : `${page.replace(/\/+$/, '')}/`;
      return `
  <url>
    <loc>${domain}${canonicalPath}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`;
    }
  )
  .join('\n')}
</urlset>`;

  fs.writeFileSync(path.join(buildPath, 'sitemap.xml'), sitemap);

  const ensureSpaFallbacks = routes => {
    const indexHtmlPath = path.join(buildPath, 'index.html');

    if (!fs.existsSync(indexHtmlPath)) {
      console.warn('Skipping SPA fallback creation because build/index.html is missing.');
      return;
    }

    Array.from(new Set(routes))
      .filter(route => route !== '/')
      .forEach(route => {
        const trimmed = route.replace(/^\//, '');

        if (!trimmed) {
          return;
        }

        const targetDir = path.join(buildPath, trimmed);
        const destination = path.join(targetDir, 'index.html');

        fs.mkdirSync(targetDir, { recursive: true });
        fs.copyFileSync(indexHtmlPath, destination);
      });
  };

  ensureSpaFallbacks([...pages, ...extraSpaRoutes]);
}

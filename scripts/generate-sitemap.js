const fs = require('fs');
const path = require('path');

const domain = 'https://rolandgao.github.io';
const buildPath = path.join(__dirname, '../build');
const blogDirectory = path.join(__dirname, '../public/data/blogs');
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

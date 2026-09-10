const fs = require('node:fs');
const path = require('node:path');

const sourceDirectory = path.join(__dirname, '../out');
const redirectDirectory = path.join(__dirname, '../out-github-redirects');
const destinationOrigin = 'https://rolandgao.com';

if (!fs.existsSync(path.join(sourceDirectory, 'index.html'))) {
  throw new Error('Build the static site before generating GitHub Pages redirects.');
}

const escapeHtml = value => value.replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[character]));

const redirectDocument = relativePath => {
  const route = `/${relativePath.split(path.sep).join('/')}`.replace(/index\.html$/, '');
  const destination = `${destinationOrigin}${route}`;
  const escapedDestination = escapeHtml(destination);

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Moved to Roland Gao's new website</title>
  <link rel="canonical" href="${escapedDestination}">
  <script>
    // Preserve the complete old link, including query parameters and fragments.
    // Concatenating with a fixed origin keeps even //-prefixed paths on our domain.
    window.location.replace(${JSON.stringify(destinationOrigin)} + window.location.pathname + window.location.search + window.location.hash);
  </script>
  <meta http-equiv="refresh" content="0; url=${escapedDestination}">
</head>
<body>
  <p>This page has moved to <a href="${escapedDestination}">${escapedDestination}</a>.</p>
</body>
</html>
`;
};

fs.rmSync(redirectDirectory, { recursive: true, force: true });
fs.mkdirSync(redirectDirectory, { recursive: true });
let count = 0;

const visit = directory => {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const sourcePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      visit(sourcePath);
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      const relativePath = path.relative(sourceDirectory, sourcePath);
      const outputPath = path.join(redirectDirectory, relativePath);
      fs.mkdirSync(path.dirname(outputPath), { recursive: true });
      // Search Console must still read the original ownership verification file.
      if (/^google[a-z0-9]+\.html$/.test(relativePath)) {
        fs.copyFileSync(sourcePath, outputPath);
        continue;
      }
      fs.writeFileSync(outputPath, redirectDocument(relativePath));
      count += 1;
    }
  }
};

visit(sourceDirectory);
// GitHub Pages uses this document for old paths absent from the current build.
if (!fs.existsSync(path.join(redirectDirectory, '404.html'))) {
  fs.writeFileSync(path.join(redirectDirectory, '404.html'), redirectDocument('404.html'));
}
fs.writeFileSync(path.join(redirectDirectory, '.nojekyll'), '');
fs.writeFileSync(path.join(redirectDirectory, 'robots.txt'), `User-agent: *\nAllow: /\n\nSitemap: ${destinationOrigin}/sitemap.xml\n`);
console.log(`Generated ${count} HTML redirects for GitHub Pages.`);

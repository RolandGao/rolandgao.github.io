const fs = require('node:fs');
const path = require('node:path');

const sourceDirectory = path.join(__dirname, '../out');
const redirectDirectory = path.join(__dirname, '../out-github-redirects');
const destinationOrigin = 'https://rolandgao.com';

if (!fs.existsSync(path.join(sourceDirectory, 'index.html'))) {
  throw new Error('Build the static site before generating GitHub Pages redirects.');
}

// Keep a complete site behind GitHub's native custom-domain 301 redirect.
// This lets the custom domain serve real content during certificate provisioning.
fs.rmSync(redirectDirectory, { recursive: true, force: true });
fs.cpSync(sourceDirectory, redirectDirectory, { recursive: true });

const fallbackRedirect = `<script>
  // GitHub normally redirects this hostname at the server. This fallback also
  // works while its custom-domain configuration is being refreshed.
  if (window.location.hostname === 'rolandgao.github.io') {
    window.location.replace(${JSON.stringify(destinationOrigin)} + window.location.pathname + window.location.search + window.location.hash);
  }
</script>`;
let count = 0;

const visit = directory => {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const outputPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      visit(outputPath);
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      const relativePath = path.relative(redirectDirectory, outputPath);
      if (/^google[a-z0-9]+\.html$/.test(relativePath)) continue;
      const html = fs.readFileSync(outputPath, 'utf8');
      if (!html.includes('<head>')) throw new Error(`Missing head in ${relativePath}`);
      fs.writeFileSync(outputPath, html.replace('<head>', `<head>${fallbackRedirect}`));
      count += 1;
    }
  }
};

visit(redirectDirectory);
fs.writeFileSync(path.join(redirectDirectory, '.nojekyll'), '');
console.log(`Prepared ${count} pages with hostname-specific GitHub redirect fallbacks.`);

import fs from 'fs';
import path from 'path';

const DATA_ROOT = path.join(process.cwd(), 'public', 'data');
const BLOG_DIR = path.join(DATA_ROOT, 'blogs');
const BLOG_INDEX_PATH = path.join(BLOG_DIR, 'index.json');

const LEGACY_SLUG_MAP = {
  unsaturated_evals_before_gpt5: 'finding_unsaturated_evals',
};

const removeHtmlComments = markdown =>
  markdown.replace(/<!--[\s\S]*?-->/g, '');

const readFileIfExists = absolutePath => {
  if (!fs.existsSync(absolutePath)) {
    return null;
  }

  return fs.readFileSync(absolutePath, 'utf8');
};

export const resolvePostId = slug => LEGACY_SLUG_MAP[slug] ?? slug;

export const loadBlogIndex = () => {
  const raw = readFileIfExists(BLOG_INDEX_PATH);
  if (!raw) {
    return [];
  }

  try {
    const { posts = [] } = JSON.parse(raw);
    return posts.map(post => ({
      ...post,
      path: post.path || `/blog/${post.id}/`,
    }));
  } catch (error) {
    console.error('Unable to parse blog index:', error);
    return [];
  }
};

export const loadBlogContent = postId => {
  const fullPath = path.join(BLOG_DIR, `${postId}.md`);
  const raw = readFileIfExists(fullPath);

  if (!raw) {
    return null;
  }

  return removeHtmlComments(raw);
};

export const getAllPosts = () => {
  const posts = loadBlogIndex();

  return posts
    .slice()
    .sort((a, b) => {
      if (!a.date || !b.date || a.date === b.date) {
        return a.title.localeCompare(b.title);
      }

      return a.date < b.date ? 1 : -1;
    });
};

export const getPostBySlug = slug => {
  const postId = resolvePostId(slug);
  const allPosts = getAllPosts();
  const metadata = allPosts.find(post => post.id === postId);

  if (!metadata) {
    return null;
  }

  const content = loadBlogContent(postId);

  if (content === null) {
    return null;
  }

  const canonicalPath = metadata.path || `/blog/${postId}/`;
  const isLegacySlug = postId !== slug;

  return {
    slug,
    postId,
    metadata,
    canonicalPath,
    isLegacySlug,
    content,
  };
};

export const loadMarkdownPage = relativePath => {
  const fullPath = path.join(DATA_ROOT, relativePath);
  const raw = readFileIfExists(fullPath);
  return raw ? removeHtmlComments(raw) : null;
};

export const getAllSlugs = () => {
  const fromPosts = getAllPosts().map(post => post.id);
  const legacy = Object.keys(LEGACY_SLUG_MAP);

  return Array.from(new Set([...fromPosts, ...legacy]));
};

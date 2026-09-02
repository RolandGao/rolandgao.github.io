import fs from 'fs';
import path from 'path';

const CONTENT_ROOT = path.join(process.cwd(), 'content');
const BLOG_DIR = path.join(CONTENT_ROOT, 'blogs');
const BLOG_INDEX_PATH = path.join(BLOG_DIR, 'index.json');
const DRAFT_DIR = path.join(process.cwd(), 'draft_blogs');
const DRAFT_INDEX_PATH = path.join(DRAFT_DIR, 'index.json');

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

const titleFromId = id =>
  id
    .split(/[-_]+/)
    .filter(Boolean)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

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
      updated: post.updated || post.date,
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
      if (!a.updated || !b.updated || a.updated === b.updated) {
        return a.title.localeCompare(b.title);
      }

      return a.updated < b.updated ? 1 : -1;
    });
};

export const loadDraftIndex = () => {
  const raw = readFileIfExists(DRAFT_INDEX_PATH);
  if (!raw) {
    return [];
  }

  try {
    const { drafts = [] } = JSON.parse(raw);
    return drafts;
  } catch (error) {
    console.error('Unable to parse draft index:', error);
    return [];
  }
};

export const getAllDrafts = () => {
  if (!fs.existsSync(DRAFT_DIR)) {
    return [];
  }

  const metadataById = new Map(
    loadDraftIndex().map(draft => [draft.id, draft]),
  );

  return fs
    .readdirSync(DRAFT_DIR, { withFileTypes: true })
    .filter(entry => entry.isFile() && entry.name.endsWith('.md'))
    .map(entry => {
      const id = entry.name.replace(/\.md$/, '');
      const metadata = metadataById.get(id) || {};

      return {
        ...metadata,
        id,
        title: metadata.title || titleFromId(id),
        path: `/blog/drafts/${id}/`,
      };
    })
    .sort((a, b) => a.title.localeCompare(b.title));
};

export const getDraftBySlug = slug => {
  const metadata = getAllDrafts().find(draft => draft.id === slug);
  if (!metadata) {
    return null;
  }

  const raw = readFileIfExists(path.join(DRAFT_DIR, `${metadata.id}.md`));
  if (raw === null) {
    return null;
  }

  return {
    metadata,
    content: removeHtmlComments(raw),
  };
};

export const getAllDraftSlugs = () => getAllDrafts().map(draft => draft.id);

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
  const fullPath = path.join(CONTENT_ROOT, relativePath);
  const raw = readFileIfExists(fullPath);
  return raw ? removeHtmlComments(raw) : null;
};

export const getAllSlugs = () => {
  const fromPosts = getAllPosts().map(post => post.id);
  const legacy = Object.keys(LEGACY_SLUG_MAP);

  return Array.from(new Set([...fromPosts, ...legacy]));
};

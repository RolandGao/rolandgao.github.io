import Link from 'next/link';
import Layout from '../../components/Layout';
import { formatPacificDate } from '../../lib/dates';
import { getAllDrafts, getAllPosts } from '../../lib/posts';

export const getStaticProps = () => {
  const posts = getAllPosts().map(post => ({
    ...post,
    updatedDisplay: formatPacificDate(post.updated),
  }));
  const drafts = process.env.NODE_ENV === 'development' ? getAllDrafts() : [];

  return {
    props: {
      posts,
      drafts,
    },
  };
};

const BlogIndexPage = ({ posts, drafts }) => {
  return (
    <Layout
      title="Blog | Roland Gao"
      description="Posts by Roland Gao on AI, alignment, and engineering."
      canonicalPath="/blog/"
    >
      <h1>My Blog</h1>
      <ul className="blog-list">
        {posts.map(post => (
          <li key={post.id}>
            <Link href={post.path}>
              <h2>{post.title}</h2>
              {post.updatedDisplay ? (
                <p className="post-date">Updated: {post.updatedDisplay}</p>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
      {drafts.length ? (
        <section className="draft-blog-section">
          <p className="draft-blog-label">Local development only</p>
          <h2>Drafts</h2>
          <ul className="blog-list draft-blog-list">
            {drafts.map(draft => (
              <li key={draft.id}>
                <Link href={draft.path}>
                  <h3>{draft.title}</h3>
                  <p className="post-date">Unpublished draft</p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </Layout>
  );
};

export default BlogIndexPage;

import Link from 'next/link';
import Layout from '../../components/Layout';
import { formatPacificDate } from '../../lib/dates';
import { getAllPosts } from '../../lib/posts';

export const getStaticProps = () => {
  const posts = getAllPosts().map(post => ({
    ...post,
    dateDisplay: post.dateDisplay || formatPacificDate(post.date),
  }));

  return {
    props: {
      posts,
    },
  };
};

const BlogIndexPage = ({ posts }) => {
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
              {post.dateDisplay ? (
                <p className="post-date">
                  Date: {post.dateDisplay} | Author: Roland Gao
                </p>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </Layout>
  );
};

export default BlogIndexPage;

import Image from 'next/image';
import Link from 'next/link';
import Layout from '../components/Layout';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { formatPacificDate } from '../lib/dates';
import { getAllPosts, loadMarkdownPage } from '../lib/posts';

export const getStaticProps = () => {
  const content = loadMarkdownPage('home.md') || '';
  const posts = getAllPosts().map(post => ({
    ...post,
    dateDisplay: post.dateDisplay || formatPacificDate(post.date),
  }));

  return {
    props: {
      content,
      posts,
    },
  };
};

const HomePage = ({ content, posts }) => {
  return (
    <Layout
      title="Roland Gao"
      description="Personal site of Roland Gao."
      canonicalPath="/"
    >
      <div className="home-page">
        <div className="profile-header">
          <Image
            src="/profile_pic.png"
            alt="Profile"
            width={150}
            height={150}
            className="profile-pic"
            priority
          />
        </div>
        <MarkdownRenderer content={content} />
        {posts.length ? (
          <section className="home-blog-section">
            <MarkdownRenderer content="# Latest Posts" />
            <ul className="blog-list">
              {posts.map(post => (
                <li key={post.id}>
                  <Link href={post.path}>
                    <h3>{post.title}</h3>
                    {post.dateDisplay ? (
                      <p className="post-date">
                        Date: {post.dateDisplay} | Author: Roland Gao
                      </p>
                    ) : null}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </Layout>
  );
};

export default HomePage;

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
    updatedDisplay: formatPacificDate(post.updated),
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
      description="Independent AI researcher focused on safety alignment, adversarial training, long context, optimizers, and scalable reinforcement learning. Previously a Research Engineer at Meta Superintelligence Labs."
      canonicalPath="/"
    >
      <div className="home-page">
        <div className="profile-header">
          <Image
            src="/profile_pic.png"
            alt="Roland Gao"
            width={150}
            height={150}
            className="profile-pic"
            priority
          />
        </div>
        <MarkdownRenderer content={content} />
        {posts.length ? (
          <section className="home-blog-section">
            <MarkdownRenderer content="## Latest Posts" />
            <ul className="blog-list">
              {posts.map(post => (
                <li key={post.id}>
                  <Link href={post.path}>
                    <h3>{post.title}</h3>
                    {post.updatedDisplay ? (
                      <p className="post-date">
                        Updated: {post.updatedDisplay}
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

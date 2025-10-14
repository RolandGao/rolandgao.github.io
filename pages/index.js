import Image from 'next/image';
import Layout from '../components/Layout';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { loadMarkdownPage } from '../lib/posts';

export const getStaticProps = () => {
  const content = loadMarkdownPage('home.md') || '';

  return {
    props: {
      content,
    },
  };
};

const HomePage = ({ content }) => {
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
      </div>
    </Layout>
  );
};

export default HomePage;

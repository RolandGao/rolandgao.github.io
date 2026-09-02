import Image from 'next/image';
import Link from 'next/link';
import Layout from '../components/Layout';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { formatPacificDate } from '../lib/dates';
import { getAllPosts, loadMarkdownPage } from '../lib/posts';
import {
  PERSON_ID,
  SITE_NAME,
  SITE_URL,
  WEBSITE_ID,
} from '../lib/site';

const homepageStructuredData = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'WebSite',
      '@id': WEBSITE_ID,
      url: `${SITE_URL}/`,
      name: SITE_NAME,
      publisher: {
        '@id': PERSON_ID,
      },
    },
    {
      '@type': 'ProfilePage',
      '@id': `${SITE_URL}/#profile`,
      url: `${SITE_URL}/`,
      name: SITE_NAME,
      isPartOf: {
        '@id': WEBSITE_ID,
      },
      mainEntity: {
        '@id': PERSON_ID,
      },
    },
    {
      '@type': 'Person',
      '@id': PERSON_ID,
      name: SITE_NAME,
      url: `${SITE_URL}/`,
      image: `${SITE_URL}/profile_pic.png`,
      jobTitle: 'Independent AI Researcher',
      alumniOf: {
        '@type': 'CollegeOrUniversity',
        name: 'University of Toronto',
        sameAs: 'https://www.utoronto.ca/',
      },
      knowsAbout: [
        'AI safety alignment',
        'Adversarial training',
        'Long-context AI',
        'Optimization',
        'Scalable reinforcement learning',
      ],
      sameAs: [
        'https://www.linkedin.com/in/roland-gao/',
        'https://x.com/Roland65821498',
        'https://github.com/RolandGao',
        'https://scholar.google.ca/citations?user=gZWmCKYAAAAJ&hl=en',
      ],
    },
  ],
};

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
      structuredData={homepageStructuredData}
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
                        Updated:{' '}
                        <time dateTime={post.updated}>
                          {post.updatedDisplay}
                        </time>
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

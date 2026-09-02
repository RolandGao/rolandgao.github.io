import { useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import MarkdownRenderer from '../../components/MarkdownRenderer';
import { formatPacificDate } from '../../lib/dates';
import { getAllSlugs, getPostBySlug } from '../../lib/posts';
import {
  PERSON_ID,
  SITE_NAME,
  SITE_URL,
  SOCIAL_IMAGE_URL,
  WEBSITE_ID,
} from '../../lib/site';

export const getStaticPaths = () => {
  const slugs = getAllSlugs();

  return {
    paths: slugs.map(slug => ({ params: { slug } })),
    fallback: false,
  };
};

export const getStaticProps = ({ params }) => {
  const post = getPostBySlug(params.slug);

  if (!post) {
    return {
      notFound: true,
    };
  }

  const { metadata, content, canonicalPath, isLegacySlug } = post;
  const dateDisplay = metadata.dateDisplay || formatPacificDate(metadata.date);
  const updatedDisplay = formatPacificDate(metadata.updated);

  return {
    props: {
      metadata,
      content,
      canonicalPath,
      isLegacySlug,
      dateDisplay,
      updatedDisplay,
    },
  };
};

const BlogPostPage = ({
  metadata,
  content,
  canonicalPath,
  isLegacySlug,
  dateDisplay,
  updatedDisplay,
}) => {
  const router = useRouter();
  const featureClass = content.includes('<gobench')
    ? ' blog-post--gobench'
    : content.includes('<goplay')
      ? ' blog-post--goplay'
      : '';

  useEffect(() => {
    if (!isLegacySlug) {
      return;
    }

    router.replace(canonicalPath);
  }, [canonicalPath, isLegacySlug, router]);

  const pageTitle = `${metadata.title} | Roland Gao`;
  const pageDescription =
    metadata.description || `Read "${metadata.title}" by Roland Gao.`;
  const canonicalUrl = `${SITE_URL}${canonicalPath}`;
  const articleStructuredData = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    '@id': `${canonicalUrl}#article`,
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': canonicalUrl,
    },
    isPartOf: {
      '@id': WEBSITE_ID,
    },
    headline: metadata.title,
    description: pageDescription,
    image: SOCIAL_IMAGE_URL,
    datePublished: metadata.date,
    dateModified: metadata.updated || metadata.date,
    inLanguage: 'en',
    author: {
      '@type': 'Person',
      '@id': PERSON_ID,
      name: SITE_NAME,
      url: `${SITE_URL}/`,
    },
  };

  return (
    <Layout
      title={pageTitle}
      description={pageDescription}
      canonicalPath={canonicalPath}
      structuredData={isLegacySlug ? null : articleStructuredData}
    >
      {isLegacySlug ? (
        <Head>
          <meta httpEquiv="refresh" content={`0; url=${canonicalPath}`} />
        </Head>
      ) : null}
      <article className={`blog-post${featureClass}`}>
        <header>
          <h1>{metadata.title}</h1>
          <p className="post-date">
            {updatedDisplay ? (
              <>
                Updated:{' '}
                <time dateTime={metadata.updated}>{updatedDisplay}</time>
                {' | '}
              </>
            ) : null}
            {dateDisplay ? (
              <>
                Original:{' '}
                <time dateTime={metadata.date}>{dateDisplay}</time>
                {' | '}
              </>
            ) : null}
            Author: <Link href="/">Roland Gao</Link>
          </p>
        </header>
        <MarkdownRenderer content={content} />
      </article>
      <div className="back-link">
        <Link href="/blog/">← Back to all posts</Link>
      </div>
    </Layout>
  );
};

export default BlogPostPage;

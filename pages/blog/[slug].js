import { useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import MarkdownRenderer from '../../components/MarkdownRenderer';
import { formatPacificDate } from '../../lib/dates';
import { getAllSlugs, getPostBySlug } from '../../lib/posts';

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

  return {
    props: {
      metadata,
      content,
      canonicalPath,
      isLegacySlug,
      dateDisplay,
    },
  };
};

const BlogPostPage = ({
  metadata,
  content,
  canonicalPath,
  isLegacySlug,
  dateDisplay,
}) => {
  const router = useRouter();

  useEffect(() => {
    if (!isLegacySlug) {
      return;
    }

    router.replace(canonicalPath);
  }, [canonicalPath, isLegacySlug, router]);

  const pageTitle = `${metadata.title} | Roland Gao`;
  const pageDescription =
    metadata.description || `Read "${metadata.title}" by Roland Gao.`;

  return (
    <Layout
      title={pageTitle}
      description={pageDescription}
      canonicalPath={canonicalPath}
    >
      {isLegacySlug ? (
        <Head>
          <meta httpEquiv="refresh" content={`0; url=${canonicalPath}`} />
        </Head>
      ) : null}
      <article className="blog-post">
        <header>
          <h1>{metadata.title}</h1>
          {dateDisplay ? (
            <p className="post-date">
              Date: {dateDisplay} | Author: Roland Gao
            </p>
          ) : null}
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

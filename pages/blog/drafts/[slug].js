import Head from 'next/head';
import Layout from '../../../components/Layout';
import MarkdownRenderer from '../../../components/MarkdownRenderer';
import { getAllDraftSlugs, getDraftBySlug } from '../../../lib/posts';

export const getStaticPaths = () => ({
  paths:
    process.env.NODE_ENV === 'development'
      ? getAllDraftSlugs().map(slug => ({ params: { slug } }))
      : [],
  fallback: false,
});

export const getStaticProps = ({ params }) => {
  if (process.env.NODE_ENV !== 'development') {
    return {
      notFound: true,
    };
  }

  const draft = getDraftBySlug(params.slug);
  if (!draft) {
    return {
      notFound: true,
    };
  }

  return {
    props: draft,
  };
};

const DraftBlogPage = ({ metadata, content }) => {
  const featureClass = ['gobench', 'goplay'].includes(metadata.id)
    ? ` blog-post--${metadata.id}`
    : '';

  return (
    <Layout
      title={`${metadata.title} — Local Draft`}
      description={`Local preview of the unpublished “${metadata.title}” draft.`}
      canonicalPath={metadata.path}
    >
      <Head>
        <meta name="robots" content="noindex,nofollow" />
      </Head>
      <article className={`blog-post draft-blog-post${featureClass}`}>
        <header>
          <p className="draft-preview-notice">Local draft preview · not included in production</p>
          <h1>{metadata.title}</h1>
        </header>
        <MarkdownRenderer content={content} />
      </article>
    </Layout>
  );
};

export default DraftBlogPage;

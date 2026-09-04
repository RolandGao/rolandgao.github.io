import Head from 'next/head';
import Link from 'next/link';
import Layout from '../components/Layout';

const NotFoundPage = () => {
  return (
    <Layout
      title="Page Not Found | Roland Gao"
      description="The page you were looking for does not exist."
      canonicalPath="/404"
    >
      <Head>
        <meta name="robots" content="noindex,follow" />
      </Head>
      <h1>Page Not Found</h1>
      <p>The page you were looking for does not exist.</p>
      <p>
        <Link href="/">Return home</Link>
      </p>
    </Layout>
  );
};

export default NotFoundPage;

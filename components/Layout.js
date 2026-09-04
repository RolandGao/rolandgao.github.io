import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useMemo } from 'react';
import { SITE_URL, SOCIAL_IMAGE_URL } from '../lib/site';

const DEFAULT_DESCRIPTION =
  'Independent AI researcher exploring alignment, adversarial training, long-context systems, optimization, and scalable reinforcement learning. Formerly at Meta.';

const serializeStructuredData = data =>
  JSON.stringify(data).replace(/</g, '\\u003c');

const ensureCanonicalPath = path => {
  if (!path) {
    return '/';
  }

  const [withoutHash] = path.split('#');
  const [pathname] = withoutHash.split('?');
  const trimmed = pathname.trim();

  if (!trimmed) {
    return '/';
  }

  const withLeadingSlash = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
  const looksLikeFile = /\.[a-zA-Z0-9]+$/.test(withLeadingSlash);

  if (looksLikeFile) {
    return withLeadingSlash;
  }

  const noTrailing = withLeadingSlash.replace(/\/+$/, '');
  return noTrailing ? `${noTrailing}/` : '/';
};

const composeCanonicalUrl = path => {
  const canonicalPath = ensureCanonicalPath(path);
  if (canonicalPath === '/') {
    return `${SITE_URL}/`;
  }

  return `${SITE_URL}${canonicalPath}`;
};

const Layout = ({
  title = 'Roland Gao',
  description = DEFAULT_DESCRIPTION,
  canonicalPath,
  structuredData,
  children,
}) => {
  const router = useRouter();

  const canonicalUrl = useMemo(() => {
    if (canonicalPath) {
      return composeCanonicalUrl(canonicalPath);
    }

    return composeCanonicalUrl(router.asPath || '/');
  }, [canonicalPath, router.asPath]);

  return (
    <>
      <Head>
        <title>{title}</title>
        <meta name="description" content={description} />
        <link rel="canonical" href={canonicalUrl} />
        <meta property="og:url" content={canonicalUrl} />
        <meta property="og:title" content={title} />
        <meta property="og:description" content={description} />
        <meta property="og:image" content={SOCIAL_IMAGE_URL} />
        <meta property="og:image:alt" content="Roland Gao — Independent AI Researcher" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={title} />
        <meta name="twitter:description" content={description} />
        <meta name="twitter:image" content={SOCIAL_IMAGE_URL} />
        <meta name="twitter:image:alt" content="Roland Gao — Independent AI Researcher" />
        {structuredData ? (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{
              __html: serializeStructuredData(structuredData),
            }}
          />
        ) : null}
      </Head>
      <div className="layout">
        <nav>
          <ul className="navigation">
            <li>
              <Link href="/">Home</Link>
            </li>
            <li>
              <Link href="/blog/">Blog</Link>
            </li>
          </ul>
        </nav>
        <main>{children}</main>
      </div>
    </>
  );
};

export default Layout;

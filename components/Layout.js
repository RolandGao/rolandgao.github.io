import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useMemo } from 'react';

const SITE_URL = 'https://rolandgao.github.io';

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
  description = 'Personal site of Roland Gao',
  canonicalPath,
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

// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import BlogPage from './pages/BlogPage';
import BlogPost from './pages/BlogPost';

const CanonicalUpdater = () => {
  const location = useLocation();

  React.useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const { origin } = window.location;
    const { pathname } = location;
    const looksLikeFile = /\.[a-zA-Z0-9]+$/.test(pathname);
    let canonicalPath = pathname || '/';

    if (!looksLikeFile) {
      const trimmedPath = canonicalPath.replace(/\/+$/, '');
      canonicalPath = trimmedPath ? `${trimmedPath}/` : '/';
    }

    const canonicalUrl = canonicalPath === '/' ? `${origin}/` : `${origin}${canonicalPath}`;

    let canonicalLink = document.querySelector("link[rel='canonical']");
    if (!canonicalLink) {
      canonicalLink = document.createElement('link');
      canonicalLink.setAttribute('rel', 'canonical');
      document.head.appendChild(canonicalLink);
    }

    canonicalLink.setAttribute('href', canonicalUrl);

    const openGraphUrl = document.querySelector("meta[property='og:url']");
    if (openGraphUrl) {
      openGraphUrl.setAttribute('content', canonicalUrl);
    }
  }, [location.pathname]);

  return null;
};

const TrailingSlashRedirector = () => {
  const location = useLocation();
  const navigate = useNavigate();

  React.useEffect(() => {
    const { pathname, search, hash } = location;
    if (!pathname || pathname === '/') {
      return;
    }

    const looksLikeFile = /\.[a-zA-Z0-9]+$/.test(pathname);
    if (looksLikeFile) {
      return;
    }

    const normalizedPath = pathname.replace(/\/+$/, '');
    const targetPath = normalizedPath ? `${normalizedPath}/` : '/';

    if (pathname !== targetPath) {
      navigate(`${targetPath}${search}${hash}`, { replace: true });
    }
  }, [location, navigate]);

  return null;
};

function App() {
  return (
    <Router basename="/">
      <CanonicalUpdater />
      <TrailingSlashRedirector />
      <div className="app">
        <nav>
          <ul className="navigation">
            <li><Link to="/">Home</Link></li>
            <li><Link to="/blog/">Blog</Link></li>
          </ul>
        </nav>
        
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/blog" element={<Navigate to="/blog/" replace />} />
          <Route path="/blog/" element={<BlogPage />} />
          <Route
            path="/blog/unsaturated_evals_before_gpt5"
            element={<Navigate to="/blog/finding_unsaturated_evals/" replace />}
          />
          <Route path="/blog/:id/*" element={<BlogPost />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

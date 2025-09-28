// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import BlogPage from './pages/BlogPage';
import BlogPost from './pages/BlogPost';

function App() {
  return (
    <Router basename="/">
      <div className="app">
        <nav>
          <ul className="navigation">
            <li><Link to="/">Home</Link></li>
            <li><Link to="/blog">Blog</Link></li>
          </ul>
        </nav>
        
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/blog" element={<BlogPage />} />
          <Route
            path="/blog/unsaturated_evals_before_gpt5"
            element={<Navigate to="/blog/finding_unsaturated_evals" replace />}
          />
          <Route path="/blog/:id" element={<BlogPost />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

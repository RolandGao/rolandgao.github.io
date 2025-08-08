import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const BlogPage = () => {
  const [blogPosts, setBlogPosts] = useState([]);

  useEffect(() => {
    // In a real app, you'd fetch this from an API or import directly
    const posts = [
      { id: 'unsaturated_evals_before_gpt5', title: 'Unsaturated Evals in Aug 2025', date: '2025-08-07' },
      { id: 'path_to_agi', title: 'Path to AGI', date: '2025-06-01' },

    ];
    setBlogPosts(posts);
  }, []);

  return (
    <div className="blog-page">
      <h1>My Blog</h1>
      <ul className="blog-list">
        {blogPosts.map(post => (
          <li key={post.id}>
            <Link to={`/blog/${post.id}`}>
              <h2>{post.title}</h2>
              <p className="post-date">{new Date(post.date).toLocaleDateString()}</p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default BlogPage;
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const pacificFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/Los_Angeles',
  year: 'numeric',
  month: 'long',
  day: 'numeric',
});

const formatPacificDate = dateString => {
  if (!dateString) {
    return '';
  }

  const [year, month, day] = dateString.split('-').map(Number);
  if (![year, month, day].every(Number.isFinite)) {
    return dateString;
  }

  const utcMidday = new Date(Date.UTC(year, month - 1, day, 12));
  return pacificFormatter.format(utcMidday);
};

const BlogPage = () => {
  const [blogPosts, setBlogPosts] = useState([]);

  useEffect(() => {
    let isMounted = true;

    const loadBlogPosts = async () => {
      try {
        const response = await fetch(`${process.env.PUBLIC_URL}/data/blogs/index.json`);
        if (!response.ok) {
          throw new Error(`Unable to load blog index (${response.status})`);
        }

        const { posts = [] } = await response.json();
        const sortedPosts = posts
          .slice()
          .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
          .map(post => ({
            ...post,
            dateDisplay: post.dateDisplay || formatPacificDate(post.date),
          }));

        if (isMounted) {
          setBlogPosts(sortedPosts);
        }
      } catch (error) {
        console.error('Failed to load blog posts:', error);
        if (isMounted) {
          setBlogPosts([]);
        }
      }
    };

    loadBlogPosts();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="blog-page">
      <h1>My Blog</h1>
      <ul className="blog-list">
        {blogPosts.map(post => (
          <li key={post.id}>
            <Link to={`/blog/${post.id}/`}>
              <h2>{post.title}</h2>
              <p className="post-date">{post.dateDisplay || formatPacificDate(post.date)}</p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default BlogPage;

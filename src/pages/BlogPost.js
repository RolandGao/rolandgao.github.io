// src/pages/BlogPost.js
import { useParams, Link } from 'react-router-dom';
import MarkdownRenderer from '../components/MarkdownRenderer';

const BlogPost = () => {
  const { id } = useParams();
  
  return (
    <div className="blog-post">
      <MarkdownRenderer 
        filePath={`${process.env.PUBLIC_URL}/data/blogs/${id}.md`} 
      />
      <div className="back-link">
        <Link to="/blog/">← Back to all posts</Link>
      </div>
    </div>
  );
};

export default BlogPost;

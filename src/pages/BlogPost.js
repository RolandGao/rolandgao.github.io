// src/pages/BlogPost.js
import { useParams } from 'react-router-dom';
import MarkdownRenderer from '../components/MarkdownRenderer';

const BlogPost = () => {
  const { id } = useParams();
  
  return (
    <div className="blog-post">
      <MarkdownRenderer 
        filePath={`${process.env.PUBLIC_URL}/data/blogs/${id}.md`} 
      />
      <div className="back-link">
        <a href="/blogs">← Back to all posts</a>
      </div>
    </div>
  );
};

export default BlogPost;
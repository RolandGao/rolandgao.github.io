import React from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import 'github-markdown-css/github-markdown.css';



const MarkdownRenderer = ({ filePath }) => {
  const [content, setContent] = React.useState('');

  React.useEffect(() => {
    fetch(filePath)
      .then(response => response.text())
      .then(text => {
        // Remove HTML comments
        const noComments = text.replace(/<!--[\s\S]*?-->/g, '');
        setContent(noComments);
      });
  }, [filePath]);

  return (
    <div className="markdown-body">
      <Markdown remarkPlugins={[remarkGfm]}>
        {content}
      </Markdown>
    </div>
  );
};

export default MarkdownRenderer;
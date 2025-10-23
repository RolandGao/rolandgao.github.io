import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import 'github-markdown-css/github-markdown-light.css';

const MarkdownRenderer = ({ content = '' }) => {
  const markdownComponents = {
    a: ({ node, ...props }) => {
      const href = props.href || '';
      const isExternal = /^https?:\/\//i.test(href);

      if (isExternal) {
        return <a {...props} target="_blank" rel="noopener noreferrer" />;
      }

      return <a {...props} />;
    },
  };

  return (
    <div className="markdown-body">
      <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </Markdown>
    </div>
  );
};

export default MarkdownRenderer;

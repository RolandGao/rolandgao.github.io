import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
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

  const markdownSchema = {
    ...defaultSchema,
    attributes: {
      ...defaultSchema.attributes,
      img: [...(defaultSchema.attributes?.img || []), 'width', 'height'],
    },
  };

  return (
    <div className="markdown-body">
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, markdownSchema]]}
        components={markdownComponents}
      >
        {content}
      </Markdown>
    </div>
  );
};

export default MarkdownRenderer;

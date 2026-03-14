import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import 'github-markdown-css/github-markdown-light.css';
import 'katex/dist/katex.min.css';

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
      code: [
        ...(defaultSchema.attributes?.code || []),
        ['className', /^language-./, 'math-inline', 'math-display'],
      ],
      img: [...(defaultSchema.attributes?.img || []), 'width', 'height'],
    },
  };

  return (
    <div className="markdown-body">
      <Markdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[
          rehypeRaw,
          [rehypeSanitize, markdownSchema],
          rehypeKatex,
        ]}
        components={markdownComponents}
      >
        {content}
      </Markdown>
    </div>
  );
};

export default MarkdownRenderer;

import React from 'react';
import dynamic from 'next/dynamic';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import { GoBenchDataProvider } from './GoBenchData';
import 'github-markdown-css/github-markdown-light.css';
import 'katex/dist/katex.min.css';

const GoBench = dynamic(() => import('./GoBench'), {
  loading: () => (
    <div className="gobench-loading" role="status">
      <span />
      <p>Loading GoBench…</p>
    </div>
  ),
});

const GoPlay = dynamic(() => import('./GoPlay'), {
  loading: () => (
    <div className="goplay-loading goplay-loading--reserved" role="status">
      <span />
      <p>Loading GoPlay…</p>
    </div>
  ),
});

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
    gobench: () => <GoBench />,
    'gobench-api-chart': () => <GoBench section="api" />,
    'gobench-leaderboard': () => <GoBench section="leaderboard" />,
    'gobench-agentic-chart': () => <GoBench section="agentic" />,
    'gobench-replayer': () => <GoBench section="replayer" />,
    goplay: () => <GoPlay />,
  };

  const markdownSchema = {
    ...defaultSchema,
    tagNames: [
      ...(defaultSchema.tagNames || []),
      'gobench',
      'gobench-api-chart',
      'gobench-leaderboard',
      'gobench-agentic-chart',
      'gobench-replayer',
      'goplay',
    ],
    attributes: {
      ...defaultSchema.attributes,
      code: [
        ...(defaultSchema.attributes?.code || []),
        ['className', /^language-./, 'math-inline', 'math-display'],
      ],
      img: [...(defaultSchema.attributes?.img || []), 'width', 'height'],
    },
  };

  const renderedMarkdown = (
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
  );

  return (
    <div className="markdown-body">
      {content.includes('<gobench') ? (
        <GoBenchDataProvider>{renderedMarkdown}</GoBenchDataProvider>
      ) : renderedMarkdown}
    </div>
  );
};

export default MarkdownRenderer;

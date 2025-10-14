import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import 'github-markdown-css/github-markdown.css';

const MarkdownRenderer = ({ content = '' }) => (
  <div className="markdown-body">
    <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
  </div>
);

export default MarkdownRenderer;

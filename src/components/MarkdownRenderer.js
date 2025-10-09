import React from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import 'github-markdown-css/github-markdown.css';



const MarkdownRenderer = ({ filePath }) => {
  const [content, setContent] = React.useState('');
  const [error, setError] = React.useState('');

  React.useEffect(() => {
    const controller = new AbortController();

    const loadMarkdown = async () => {
      try {
        setError('');
        const response = await fetch(filePath, { signal: controller.signal });

        if (!response.ok) {
          throw new Error(`Failed to load markdown (${response.status})`);
        }

        const text = await response.text();
        // Remove HTML comments so the rendered markdown is cleaner
        const noComments = text.replace(/<!--[\s\S]*?-->/g, '');
        setContent(noComments);
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }

        console.error(`Unable to load markdown from ${filePath}:`, err);
        setError('This content is unavailable right now.');
        setContent('');
      }
    };

    loadMarkdown();

    return () => {
      controller.abort();
    };
  }, [filePath]);

  return (
    <div className="markdown-body">
      {error ? (
        <p>{error}</p>
      ) : (
        <Markdown remarkPlugins={[remarkGfm]}>
          {content}
        </Markdown>
      )}
    </div>
  );
};

export default MarkdownRenderer;

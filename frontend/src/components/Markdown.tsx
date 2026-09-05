import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { cn } from '../utils/cn';

interface MarkdownProps {
  content: string;
  className?: string;
}

const components = {
  code: ({ node, children, className: codeClassName, ...props }: any) => {
    const isBlock = node?.position?.start?.line !== node?.position?.end?.line
      || /language-/.test(codeClassName || '');
    const language = (codeClassName || '').replace('language-', '');

    if (isBlock) {
      return (
        <pre className={cn('rounded-lg bg-dark-100 dark:bg-dark-900 p-4 overflow-x-auto', props.className)}>
          <code className={cn('text-sm font-mono', language && `language-${language}`)}>
            {String(children).replace(/\n$/, '')}
          </code>
        </pre>
      );
    }

    return (
      <code className={cn('rounded bg-dark-100 dark:bg-dark-800 px-1.5 py-0.5 text-sm font-mono', props.className)}>
        {children}
      </code>
    );
  },
  blockquote: ({ children, ...props }: any) => (
    <blockquote className={cn('border-l-4 border-primary-500 pl-4 italic text-dark-600 dark:text-dark-400', props.className)}>
      {children}
    </blockquote>
  ),
  table: ({ children, ...props }: any) => (
    <div className={cn('overflow-x-auto', props.className)}>
      <table className={cn('min-w-full divide-y divide-dark-200 dark:divide-dark-700', props.className)}>
        {children}
      </table>
    </div>
  ),
  th: ({ children, ...props }: any) => (
    <th className={cn('px-4 py-3 text-left text-xs font-medium text-dark-500 dark:text-dark-400 uppercase tracking-wider bg-dark-100 dark:bg-dark-800', props.className)}>
      {children}
    </th>
  ),
  td: ({ children, ...props }: any) => (
    <td className={cn('px-4 py-3 text-sm text-dark-900 dark:text-dark-500', props.className)}>
      {children}
    </td>
  ),
  tr: ({ children, ...props }: any) => (
    <tr className={cn('hover:bg-dark-50 dark:hover:bg-dark-800', props.className)}>
      {children}
    </tr>
  ),
  ul: ({ children, ...props }: any) => (
    <ul className={cn('list-disc list-inside space-y-1', props.className)}>
      {children}
    </ul>
  ),
  ol: ({ children, ...props }: any) => (
    <ol className={cn('list-decimal list-inside space-y-1', props.className)}>
      {children}
    </ol>
  ),
  li: ({ children, ...props }: any) => (
    <li className={cn('ml-4', props.className)}>
      {children}
    </li>
  ),
  a: ({ children, href, ...props }: any) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className={cn('text-primary-600 hover:underline', props.className)}>
      {children}
    </a>
  ),
  h1: ({ children, ...props }: any) => (
    <h1 className={cn('text-2xl font-bold text-dark-900 dark:text-dark-50 mt-6 mb-3', props.className)}>
      {children}
    </h1>
  ),
  h2: ({ children, ...props }: any) => (
    <h2 className={cn('text-xl font-bold text-dark-900 dark:text-dark-50 mt-6 mb-3', props.className)}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }: any) => (
    <h3 className={cn('text-lg font-bold text-dark-900 dark:text-dark-50 mt-4 mb-2', props.className)}>
      {children}
    </h3>
  ),
  p: ({ children, ...props }: any) => (
    <p className={cn('text-dark-700 dark:text-dark-300 leading-relaxed mb-3', props.className)}>
      {children}
    </p>
  ),
  hr: ({ ...props }: any) => (
    <hr className={cn('border-dark-200 dark:border-dark-700 my-6', props.className)} />
  ),
};

export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={cn('prose prose-dark max-w-none', className)}>
      <ReactMarkdown
        components={components}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
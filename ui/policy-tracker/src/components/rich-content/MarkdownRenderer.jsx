import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ChartRenderer from './ChartRenderer'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataTableRow,
  DataTableHeaderCell,
  DataTableCell,
} from './DataTable'

/**
 * Centralized markdown rendering component with rich content support
 * - Detects chart code blocks and renders interactive charts
 * - Provides enhanced table styling
 * - Supports all standard markdown elements with custom styling
 */
function MarkdownRenderer({ content, className = '', variant = 'default' }) {
  // Variant-specific heading styles
  const headingStyles = {
    default: {
      h1: 'text-xl font-bold text-gray-900 mt-4 mb-3 first:mt-0',
      h2: 'text-lg font-semibold text-gray-800 mt-4 mb-2',
      h3: 'text-base font-medium text-gray-800 mt-3 mb-2',
    },
    report: {
      h1: 'text-2xl font-bold text-gray-900 mt-6 mb-4 first:mt-0',
      h2: 'text-xl font-semibold text-gray-800 mt-6 mb-3 border-b border-gray-200 pb-2',
      h3: 'text-lg font-medium text-gray-800 mt-4 mb-2',
    },
  }

  const styles = headingStyles[variant] || headingStyles.default

  return (
    <ReactMarkdown
      className={`prose prose-sm max-w-none ${className}`}
      remarkPlugins={[remarkGfm]}
      components={{
        // Custom code block handler for charts
        code: ({ node, inline, className: codeClassName, children, ...props }) => {
          const match = /language-(\w+)/.exec(codeClassName || '')
          const language = match ? match[1] : ''

          // Handle chart code blocks
          if (!inline && language === 'chart') {
            try {
              const chartSpec = JSON.parse(String(children).trim())
              return <ChartRenderer spec={chartSpec} />
            } catch (e) {
              console.error('Invalid chart specification:', e)
              return (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-600 text-sm font-medium mb-2">
                    Invalid chart specification
                  </p>
                  <pre className="text-xs text-red-500 overflow-x-auto">
                    {String(children)}
                  </pre>
                </div>
              )
            }
          }

          // Regular code blocks
          if (!inline) {
            return (
              <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto mb-4">
                <code className={`text-sm font-mono text-gray-800 ${codeClassName || ''}`} {...props}>
                  {children}
                </code>
              </pre>
            )
          }

          // Inline code
          return (
            <code
              className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800"
              {...props}
            >
              {children}
            </code>
          )
        },

        // Enhanced table components
        table: ({ children }) => <DataTable>{children}</DataTable>,
        thead: ({ children }) => <DataTableHead>{children}</DataTableHead>,
        tbody: ({ children }) => <DataTableBody>{children}</DataTableBody>,
        tr: ({ children }) => <DataTableRow>{children}</DataTableRow>,
        th: ({ children }) => <DataTableHeaderCell>{children}</DataTableHeaderCell>,
        td: ({ children }) => <DataTableCell>{children}</DataTableCell>,

        // Headings with variant-specific styles
        h1: ({ children }) => <h1 className={styles.h1}>{children}</h1>,
        h2: ({ children }) => <h2 className={styles.h2}>{children}</h2>,
        h3: ({ children }) => <h3 className={styles.h3}>{children}</h3>,
        h4: ({ children }) => (
          <h4 className="text-base font-medium text-gray-700 mt-3 mb-2">{children}</h4>
        ),

        // Paragraphs
        p: ({ children }) => <p className="text-gray-700 mb-4 leading-relaxed">{children}</p>,

        // Lists
        ul: ({ children }) => (
          <ul className="list-disc list-inside mb-4 space-y-1 text-gray-700">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-inside mb-4 space-y-1 text-gray-700">{children}</ol>
        ),
        li: ({ children }) => <li className="text-gray-700">{children}</li>,

        // Text formatting
        strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
        em: ({ children }) => <em className="italic text-gray-600">{children}</em>,

        // Blockquotes
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-accent-primary pl-4 my-4 italic text-gray-600">
            {children}
          </blockquote>
        ),

        // Horizontal rule
        hr: () => <hr className="my-6 border-gray-200" />,

        // Links
        a: ({ href, children }) => (
          <a
            href={href}
            className="text-accent-primary hover:text-accent-secondary underline transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

export default MarkdownRenderer

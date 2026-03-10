import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import SourceCard from "./SourceCard";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] ${
          isUser
            ? "bg-gray-800 text-white rounded-2xl rounded-br-md px-4 py-3"
            : "bg-transparent w-full"
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        ) : (
          <div>
            {/* Assistant text with markdown + HTML rendering */}
            {message.content && (
              <div className="assistant-message text-sm leading-relaxed text-gray-800 prose prose-sm max-w-none prose-headings:text-gray-900 prose-headings:font-semibold prose-h3:text-base prose-h4:text-sm prose-p:text-gray-700 prose-strong:text-gray-900 prose-li:text-gray-700 prose-a:text-blue-600 prose-hr:border-gray-200 prose-table:text-xs prose-th:bg-gray-50 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 prose-th:text-left prose-th:font-medium prose-th:text-gray-700">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )}

            {/* Loading indicator */}
            {!message.content && !message.error && (
              <div className="flex items-center gap-2 text-gray-400 py-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
                <span className="text-xs">Analizando fuentes...</span>
              </div>
            )}

            {/* Error state */}
            {message.error && (
              <div className="text-sm text-red-600 bg-red-50 rounded-xl px-4 py-3">
                {message.content}
              </div>
            )}

            {/* Sources */}
            {message.sources?.length > 0 && (
              <div className="mt-4">
                <SourceCard sources={message.sources} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
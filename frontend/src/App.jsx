import ChatWindow from "./components/ChatWindow";
import { useChat } from "./hooks/useChat";

export default function App() {
  const { messages, isLoading, sendMessage, clearChat } = useChat();

  return (
    <div className="h-screen flex flex-col bg-white">
      {/* Header */}
      <header className="border-b border-gray-100 bg-white">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gray-900 flex items-center justify-center">
              <span className="text-white text-xs font-bold tracking-wide">
                AI
              </span>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-gray-900 leading-none">
                AIPE
              </h1>
              <p className="text-[10px] text-gray-400 leading-none mt-0.5">
                Análisis Electoral Perú 2026
              </p>
            </div>
          </div>

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors flex items-center gap-1"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Nueva consulta
            </button>
          )}
        </div>
      </header>

      {/* Chat */}
      <main className="flex-1 overflow-hidden">
        <div className="max-w-3xl mx-auto h-full">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSend={sendMessage}
          />
        </div>
      </main>
    </div>
  );
}
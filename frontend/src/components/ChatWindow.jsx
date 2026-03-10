import { useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";

export default function ChatWindow({ messages, isLoading, onSend }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
              <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h3 className="text-base font-medium text-gray-700 mb-1">
              Pregunta sobre los candidatos
            </h3>
            <p className="text-sm text-gray-400 max-w-sm mb-6">
              Puedo analizar entrevistas y planes de gobierno de los candidatos presidenciales del Perú 2026.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {[
                "¿Qué propone López Aliaga sobre seguridad?",
                "¿Quién quiere aumentar el presupuesto de educación?",
                "¿Qué dice Keiko Fujimori sobre economía?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => onSend(q)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-5 max-w-2xl mx-auto">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-100 px-4 py-3 bg-white">
        <div className="max-w-2xl mx-auto">
          <ChatInput
            onSend={onSend}
            isLoading={isLoading}
            placeholder="Escribe tu pregunta sobre los candidatos..."
          />
        </div>
      </div>
    </div>
  );
}
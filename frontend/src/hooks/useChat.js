import { useState, useCallback } from "react";
import { sendMessageStream } from "../lib/api";

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isLoading) return;

      const userMsg = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      // Build conversation history (last 6 messages = 3 exchanges)
      const history = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Add placeholder for assistant response
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", sources: [], analysis: null },
      ]);

      try {
        await sendMessageStream({
          message: text,
          conversationHistory: history,
          onAnalysis: (analysis) => {
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                analysis,
              };
              return updated;
            });
          },
          onText: (chunk) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              updated[updated.length - 1] = {
                ...last,
                content: last.content + chunk,
              };
              return updated;
            });
          },
          onSources: (sources) => {
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                sources,
              };
              return updated;
            });
          },
          onDone: () => setIsLoading(false),
        });
      } catch {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content:
              "Lo siento, hubo un error al procesar tu pregunta. Intenta de nuevo.",
            error: true,
          };
          return updated;
        });
        setIsLoading(false);
      }
    },
    [messages, isLoading]
  );

  const clearChat = useCallback(() => setMessages([]), []);

  return { messages, isLoading, sendMessage, clearChat };
}
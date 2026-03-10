const API_BASE = import.meta.env.VITE_API_URL || "";

export async function sendMessageStream({ message, conversationHistory, onText, onSources, onAnalysis, onDone }) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory,
    }),
  });

  if (!res.ok) throw new Error("Request failed");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (data === "[DONE]") {
        onDone?.();
        return;
      }
      try {
        const parsed = JSON.parse(data);
        if (parsed.type === "text") onText?.(parsed.content);
        if (parsed.type === "sources") onSources?.(parsed.sources);
        if (parsed.type === "analysis") onAnalysis?.(parsed);
      } catch {}
    }
  }
  onDone?.();
}
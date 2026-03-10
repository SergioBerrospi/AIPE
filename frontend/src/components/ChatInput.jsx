import { useState } from "react";

export default function ChatInput({ onSend, isLoading, placeholder }) {
  const [text, setText] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSend(text.trim());
    setText("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <div className="flex-1 relative">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Escribe tu pregunta..."}
          rows={1}
          className="w-full resize-none rounded-xl border border-gray-200 bg-white px-4 py-3 pr-12 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:border-gray-300 focus:ring-1 focus:ring-gray-200 transition-colors"
          style={{
            minHeight: "44px",
            maxHeight: "120px",
          }}
          onInput={(e) => {
            e.target.style.height = "auto";
            e.target.style.height =
              Math.min(e.target.scrollHeight, 120) + "px";
          }}
          disabled={isLoading}
        />
      </div>
      <button
        type="submit"
        disabled={!text.trim() || isLoading}
        className="flex items-center justify-center w-11 h-11 rounded-xl bg-gray-800 text-white hover:bg-gray-700 disabled:bg-gray-200 disabled:text-gray-400 transition-colors flex-shrink-0"
      >
        {isLoading ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14m-7-7l7 7-7 7" />
          </svg>
        )}
      </button>
    </form>
  );
}
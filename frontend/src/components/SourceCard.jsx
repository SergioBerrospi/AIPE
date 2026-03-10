import { useState } from "react";

export default function SourceCard({ sources }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const visibleSources = sources.filter((s) => !s.is_context);
  const interviews = visibleSources.filter((s) => s.source_type === "interview");
  const plans = visibleSources.filter((s) => s.source_type === "government_plan");

  return (
    <div className="border border-gray-100 rounded-xl overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full px-4 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-xs font-medium text-gray-600">
            {visibleSources.length} fuentes
            {interviews.length > 0 && ` · ${interviews.length} entrevistas`}
            {plans.length > 0 && ` · ${plans.length} planes`}
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="divide-y divide-gray-50">
          {visibleSources.map((source, i) => (
            <div key={i} className="px-4 py-3">
              <div className="flex items-start gap-2">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 mt-0.5 ${
                    source.source_type === "interview"
                      ? "bg-blue-50 text-blue-700"
                      : "bg-emerald-50 text-emerald-700"
                  }`}
                >
                  {source.source_type === "interview"
                    ? "Entrevista"
                    : "Plan"}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-medium text-gray-700">
                    {source.candidate_name} — {source.party_name}
                  </div>
                  {source.source_type === "interview" && (
                    <div className="text-xs text-gray-500 mt-0.5">
                      {source.program_name}
                      {source.interview_date && ` · ${source.interview_date}`}
                      {source.youtube_link && (
                        <a
                          href={
                            source.youtube_link +
                            (source.start_time
                              ? `&t=${Math.floor(source.start_time)}`
                              : "")
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-1 text-blue-600 hover:underline"
                        >
                          Ver video ↗
                        </a>
                      )}
                    </div>
                  )}
                  {source.source_type === "government_plan" && (
                    <div className="text-xs text-gray-500 mt-0.5">
                      {source.page_number && `Página ${source.page_number}`}
                      {source.section_title && ` · ${source.section_title}`}
                    </div>
                  )}
                  <p className="text-xs text-gray-600 mt-1.5 line-clamp-2">
                    {source.chunk_text}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
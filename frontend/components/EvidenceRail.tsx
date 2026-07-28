"use client";

import { useState } from "react";
import type { Citation } from "@/lib/types";

/**
 * Retrieval made visible. The score bar is the point: you can see how confident the
 * retriever was, and after P3 you can watch the same question score better.
 */
export function EvidenceRail({
  citations,
  active,
}: {
  citations: Citation[];
  active: number | null;
}) {
  const [open, setOpen] = useState<number | null>(null);

  if (citations.length === 0) {
    return (
      <p className="font-mono text-xs leading-relaxed text-muted">
        Evidence appears here once you ask something. Every claim in an answer is traced back to the
        chunk it came from.
      </p>
    );
  }

  return (
    <ol className="flex flex-col gap-2">
      {citations.map((c) => {
        const isOpen = open === c.n;
        return (
          <li key={c.chunk_id}>
            <button
              onClick={() => setOpen(isOpen ? null : c.n)}
              aria-expanded={isOpen}
              className={`w-full cursor-pointer rounded-sm border p-2.5 text-left transition-colors duration-200 ${
                active === c.n
                  ? "border-teal bg-raised"
                  : "border-line bg-surface hover:border-muted/60"
              }`}
            >
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-[11px] text-teal">[{c.n}]</span>
                <span className="truncate font-mono text-[11px] text-paper">{c.source}</span>
              </div>

              <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-muted">
                {c.heading_path || "—"}
              </p>

              <div className="mt-2 flex items-center gap-2">
                <span
                  aria-hidden
                  className="h-1 flex-1 overflow-hidden rounded-full bg-line"
                  title={`similarity ${c.score}`}
                >
                  <span
                    className="block h-full bg-teal"
                    style={{ width: `${Math.round(c.score * 100)}%` }}
                  />
                </span>
                <span className="font-mono text-[10px] text-muted">{c.score.toFixed(3)}</span>
              </div>
            </button>

            {isOpen && (
              <pre className="mt-1 max-h-56 overflow-auto whitespace-pre-wrap rounded-sm border border-line bg-ink p-2.5 font-mono text-[11px] leading-relaxed text-muted">
                {c.text}
              </pre>
            )}
          </li>
        );
      })}
    </ol>
  );
}

import type { Entry } from "@/lib/types";
import { ApprovalCard } from "./ApprovalCard";
import { TraceStrip } from "./TraceStrip";

/** Renders **bold** and [n] citation chips. A markdown library is not worth the weight for two rules. */
function RichText({ text, onCite }: { text: string; onCite: (n: number | null) => void }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\[\d+\])/g);

  return (
    <>
      {parts.map((part, i) => {
        const cite = part.match(/^\[(\d+)\]$/);
        if (cite) {
          const n = Number(cite[1]);
          return (
            <button
              key={i}
              onMouseEnter={() => onCite(n)}
              onMouseLeave={() => onCite(null)}
              onFocus={() => onCite(n)}
              onBlur={() => onCite(null)}
              className="mx-0.5 cursor-pointer rounded-sm border border-teal/40 px-1 align-baseline font-mono text-[10px] text-teal transition-colors duration-200 hover:bg-teal hover:text-ink"
              aria-label={`Source ${n}`}
            >
              {n}
            </button>
          );
        }
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} className="font-semibold text-paper">
              {part.slice(2, -2)}
            </strong>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function Executed({ results }: { results: NonNullable<Entry["executed"]> }) {
  return (
    <ul className="mt-3 flex flex-col gap-1">
      {results.map((r, i) => (
        <li
          key={i}
          className="flex items-baseline gap-2 rounded-sm border border-line bg-surface px-2.5 py-1.5 font-mono text-[11px]"
        >
          <span className={r.ok ? "text-teal" : "text-danger"}>{r.ok ? "done" : "failed"}</span>
          <span className="text-paper">{r.tool}</span>
          {r.error && <span className="min-w-0 break-words text-danger">{r.error}</span>}
        </li>
      ))}
    </ul>
  );
}

export function LogEntry({
  entry,
  busy,
  onCite,
  onDecide,
}: {
  entry: Entry;
  busy: boolean;
  onCite: (n: number | null) => void;
  onDecide: (decision: "approve" | "reject") => void;
}) {
  const isYou = entry.role === "you";
  const streaming = (entry.nodes ?? []).some((n) => n.name === "respond" && n.state === "active");

  return (
    <article
      className="flex gap-3 border-l-2 pl-3 sm:gap-4"
      style={{ borderColor: isYou ? "var(--color-line)" : "var(--color-teal)" }}
    >
      <header className="hidden w-28 shrink-0 pt-0.5 sm:block">
        <time className="block font-mono text-[11px] text-muted">{entry.at}</time>
        <span className="font-mono text-[11px] uppercase tracking-widest text-muted">
          {entry.role}
        </span>
      </header>

      <div className="min-w-0 flex-1">
        <span className="mb-1 block font-mono text-[11px] uppercase tracking-widest text-muted sm:hidden">
          {entry.at} {entry.role}
        </span>

        {!isYou && (
          <TraceStrip
            nodes={entry.nodes}
            route={entry.route}
            topScore={entry.topScore}
            confident={entry.confident}
          />
        )}

        {entry.guardFlags && entry.guardFlags.length > 0 && (
          <p className="mb-3 rounded-sm border border-danger/50 bg-danger/10 px-2.5 py-1.5 font-mono text-[11px] text-danger">
            Injection-shaped text in retrieved sources: {entry.guardFlags.join("; ")}. Treated as
            data; any write still needs your approval.
          </p>
        )}

        {entry.error ? (
          <p className="rounded-sm border border-danger/50 bg-danger/10 p-2.5 text-sm text-danger">
            {entry.error}
          </p>
        ) : (
          entry.text && (
            <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
              <RichText text={entry.text} onCite={onCite} />
              {streaming && (
                <span aria-hidden className="ml-0.5 inline-block h-4 w-2 translate-y-0.5 bg-amber" />
              )}
            </p>
          )
        )}

        {entry.awaitingApproval && entry.pending && (
          <ApprovalCard pending={entry.pending} busy={busy} onDecide={onDecide} />
        )}

        {entry.decision === "reject" && !entry.awaitingApproval && (
          <p className="mt-3 rounded-sm border border-line bg-surface px-2.5 py-1.5 font-mono text-[11px] text-muted">
            Rejected. Nothing was written.
          </p>
        )}

        {entry.executed && entry.executed.length > 0 && <Executed results={entry.executed} />}
      </div>
    </article>
  );
}

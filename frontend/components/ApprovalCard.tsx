import type { ToolCall } from "@/lib/types";

/**
 * The pause. Rendered inline in the log rather than as a modal, because it is a turn in the
 * conversation and not an interruption of one — and because a modal would hide the evidence the
 * decision should be made against.
 *
 * Amber is spent here and nowhere else in the interface: it means a human is required.
 */
export function ApprovalCard({
  pending,
  busy,
  onDecide,
}: {
  pending: ToolCall[];
  busy: boolean;
  onDecide: (decision: "approve" | "reject") => void;
}) {
  return (
    <section
      aria-label="Action awaiting your approval"
      className="mt-3 rounded-sm border border-amber/60 bg-amber/5 p-3"
    >
      <h3 className="font-mono text-[11px] uppercase tracking-widest text-amber">
        Waiting on you
      </h3>
      <p className="mt-1.5 text-sm text-muted">
        {pending.length === 1
          ? "This will write to the ticketing system. Nothing has been saved yet."
          : `${pending.length} actions will write to the ticketing system. Nothing has been saved yet.`}
      </p>

      <ul className="mt-3 flex flex-col gap-2">
        {pending.map((call, i) => (
          <li key={i} className="rounded-sm border border-line bg-ink p-2.5">
            <p className="font-mono text-[12px] text-paper">{call.name}</p>
            <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              {Object.entries(call.arguments).map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="font-mono text-[11px] text-muted">{key}</dt>
                  <dd className="min-w-0 break-words text-[12px] text-paper">{String(value)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>

      <div className="mt-3 flex gap-2">
        <button
          onClick={() => onDecide("approve")}
          disabled={busy}
          className="h-9 cursor-pointer rounded-sm bg-amber px-4 text-sm font-medium text-ink transition-opacity duration-200 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Working…" : "Approve"}
        </button>
        <button
          onClick={() => onDecide("reject")}
          disabled={busy}
          className="h-9 cursor-pointer rounded-sm border border-line px-4 text-sm text-muted transition-colors duration-200 hover:border-danger hover:text-danger disabled:cursor-not-allowed disabled:opacity-40"
        >
          Reject
        </button>
      </div>
    </section>
  );
}

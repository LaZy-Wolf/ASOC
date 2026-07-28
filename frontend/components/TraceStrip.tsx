import type { Stage, StageState } from "@/lib/types";

const LABELS: Record<Stage, string> = { retrieve: "retrieve", answer: "answer" };

const TONE: Record<StageState, string> = {
  pending: "text-muted/50 border-line",
  active: "text-amber border-amber stage-active",
  done: "text-teal border-teal/60",
};

/**
 * The pipeline the answer went through. Two stages today; the P4 graph adds
 * route / grade / plan / approve / execute to the same strip.
 */
export function TraceStrip({ stages }: { stages: Record<Stage, StageState> }) {
  const order: Stage[] = ["retrieve", "answer"];

  return (
    <ol className="mb-3 flex items-center gap-1.5 font-mono text-[11px] tracking-wide">
      {order.map((stage, i) => (
        <li key={stage} className="flex items-center gap-1.5">
          {i > 0 && <span aria-hidden className="h-px w-4 bg-line" />}
          <span
            className={`rounded-sm border px-1.5 py-0.5 lowercase ${TONE[stages[stage]]}`}
            aria-label={`${LABELS[stage]}: ${stages[stage]}`}
          >
            {LABELS[stage]}
          </span>
        </li>
      ))}
    </ol>
  );
}

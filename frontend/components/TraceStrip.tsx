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
export function TraceStrip({
  stages,
  route,
  topScore,
  confident,
}: {
  stages: Record<Stage, StageState>;
  route?: string;
  topScore?: number | null;
  confident?: boolean;
}) {
  const order: Stage[] = ["retrieve", "answer"];
  const declined = confident === false;

  return (
    <ol className="mb-3 flex flex-wrap items-center gap-1.5 font-mono text-[11px] tracking-wide">
      {route && (
        <li className="flex items-center gap-1.5">
          <span className="rounded-sm border border-line px-1.5 py-0.5 lowercase text-muted">
            {route}
          </span>
          <span aria-hidden className="h-px w-4 bg-line" />
        </li>
      )}
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
      {topScore != null && (
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="h-px w-4 bg-line" />
          <span
            className={`rounded-sm border px-1.5 py-0.5 ${
              declined ? "border-amber text-amber" : "border-line text-muted"
            }`}
            title="top rerank score; below the confidence threshold the answer is declined"
          >
            {topScore > 0 ? "+" : ""}
            {topScore.toFixed(2)}
            {declined && " below threshold"}
          </span>
        </li>
      )}
    </ol>
  );
}

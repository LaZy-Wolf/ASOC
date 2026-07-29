import type { NodeName, NodeState } from "@/lib/types";

const TONE: Record<NodeState, string> = {
  active: "text-amber border-amber stage-active",
  done: "text-teal border-teal/60",
};

/**
 * The state machine, executing. Nodes appear as the graph visits them rather than being drawn
 * upfront, so the strip shows the path actually taken — a question stops at respond, an action
 * runs through plan, approve and execute.
 */
export function TraceStrip({
  nodes,
  route,
  topScore,
  confident,
}: {
  nodes?: { name: NodeName; state: NodeState }[];
  route?: string;
  topScore?: number | null;
  confident?: boolean;
}) {
  // an entry can predate this field across a hot reload; never take the whole log down for it
  const visited = nodes ?? [];
  const declined = confident === false;

  return (
    <ol className="mb-3 flex flex-wrap items-center gap-x-1.5 gap-y-1 font-mono text-[11px] tracking-wide">
      {route && (
        <li className="flex items-center gap-1.5">
          <span className="rounded-sm border border-line px-1.5 py-0.5 lowercase text-muted">
            {route}
          </span>
          <span aria-hidden className="h-px w-3 bg-line" />
        </li>
      )}

      {visited.map((node, i) => (
        <li key={`${node.name}-${i}`} className="flex items-center gap-1.5">
          {i > 0 && <span aria-hidden className="h-px w-3 bg-line" />}
          <span
            className={`rounded-sm border px-1.5 py-0.5 ${TONE[node.state]}`}
            aria-label={`${node.name}: ${node.state}`}
          >
            {node.name}
          </span>
        </li>
      ))}

      {topScore != null && (
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="h-px w-3 bg-line" />
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

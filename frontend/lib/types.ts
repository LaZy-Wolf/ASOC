export type Citation = {
  n: number;
  chunk_id: string;
  source: string;
  heading_path: string;
  doc_type: string;
  score: number;
  text: string;
};

/** Graph nodes, in the order the machine visits them. */
export type NodeName =
  | "router"
  | "retrieve"
  | "grade"
  | "plan"
  | "approve"
  | "execute"
  | "respond";

export type NodeState = "active" | "done";

export type ToolCall = { name: string; arguments: Record<string, unknown> };

export type ToolResult = {
  ok: boolean;
  tool: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  error?: string;
};

export type Entry = {
  id: string;
  role: "you" | "asoc";
  at: string; // HH:MM:SS
  text: string;
  citations: Citation[];
  nodes: { name: NodeName; state: NodeState }[];
  route?: string;
  topScore?: number | null;
  confident?: boolean;
  plan?: ToolCall[];
  pending?: ToolCall[];
  awaitingApproval?: boolean;
  decision?: "approve" | "reject";
  executed?: ToolResult[];
  guardFlags?: string[];
  blocked?: string[];
  error?: string;
};

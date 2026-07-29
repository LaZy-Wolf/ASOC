import type { Citation, NodeName, ToolCall, ToolResult } from "./types";

export type ServerEvent =
  | { type: "thread"; thread_id: string }
  | {
      type: "node";
      node: NodeName;
      route?: string;
      confident?: boolean;
      top_score?: number | null;
      pending?: ToolCall[];
      calls?: string[];
    }
  | { type: "citations"; citations: Citation[] }
  | { type: "plan"; calls: ToolCall[] }
  | { type: "guard"; flags?: string[]; blocked?: string[] }
  | { type: "executed"; results: ToolResult[] }
  | { type: "awaiting_approval"; payload: { pending: ToolCall[] } }
  | { type: "token"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8001";

async function* readEvents(res: Response): AsyncGenerator<ServerEvent> {
  if (!res.ok || !res.body) throw new Error(`request failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // events are separated by a blank line; the tail may be a partial event
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.trim();
      if (line.startsWith("data: ")) yield JSON.parse(line.slice(6)) as ServerEvent;
    }
  }
}

/** Start a turn. POST rules out EventSource, so we parse the SSE body ourselves. */
export async function* chatStream(message: string, signal: AbortSignal) {
  yield* readEvents(
    await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal,
    }),
  );
}

/** Resume a thread paused at the approval gate. The pause survived on the server's disk, so this
 *  works even if the backend restarted since the proposal was made. */
export async function* approveStream(
  threadId: string,
  decision: "approve" | "reject",
  signal: AbortSignal,
) {
  yield* readEvents(
    await fetch(`${API}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId, decision }),
      signal,
    }),
  );
}

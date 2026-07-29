type ServerEvent =
  | {
      type: "route";
      route: string;
      doc_type: string | null;
      top_score: number | null;
      confident: boolean;
    }
  | { type: "citations"; citations: import("./types").Citation[] }
  | { type: "token"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

/** Reads the /chat SSE response. POST rules out EventSource, so we parse the body ourselves. */
export async function* chatStream(message: string, signal: AbortSignal) {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });

  if (!res.ok || !res.body) throw new Error(`chat failed: ${res.status}`);

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

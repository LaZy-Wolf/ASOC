"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { EvidenceRail } from "@/components/EvidenceRail";
import { LogEntry } from "@/components/LogEntry";
import { approveStream, chatStream, type ServerEvent } from "@/lib/stream";
import type { Entry, NodeName } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8001";

const EXAMPLES = [
  "My VPN connects then drops after a minute. What now?",
  "What severity is a database host at 96% disk?",
  "Open a P3 hardware ticket for mira.kovac@example.com, her laptop will not power on.",
];

const now = () => new Date().toTimeString().slice(0, 8);

export default function Console() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const [qdrantUp, setQdrantUp] = useState<boolean | null>(null);

  const abort = useRef<AbortController | null>(null);
  const thread = useRef<string | null>(null);
  const tail = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((h) => setQdrantUp(h?.qdrant?.reachable === true))
      .catch(() => setQdrantUp(false));
  }, []);

  useEffect(() => {
    tail.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries]);

  const latest = [...entries].reverse().find((e) => e.citations.length > 0);

  /** Fold one server event into the assistant entry it belongs to. */
  const apply = useCallback((entry: Entry, event: ServerEvent): Entry => {
    switch (event.type) {
      case "node": {
        // the previously active node is finished once the next one reports in
        const nodes: Entry["nodes"] = entry.nodes.map((n) => ({ ...n, state: "done" }));
        // resuming re-enters the node it paused on; show it once, not twice
        if (nodes.at(-1)?.name !== event.node) {
          nodes.push({ name: event.node as NodeName, state: "active" });
        } else {
          nodes[nodes.length - 1] = { name: event.node as NodeName, state: "active" };
        }
        return {
          ...entry,
          nodes,
          route: event.route ?? entry.route,
          confident: event.confident ?? entry.confident,
          topScore: event.top_score !== undefined ? event.top_score : entry.topScore,
          pending: event.pending ?? entry.pending,
        };
      }
      case "citations":
        return { ...entry, citations: event.citations };
      case "plan":
        return { ...entry, plan: event.calls };
      case "guard":
        return {
          ...entry,
          guardFlags: event.flags ?? entry.guardFlags,
          blocked: event.blocked ?? entry.blocked,
        };
      case "awaiting_approval":
        return { ...entry, awaitingApproval: true, pending: event.payload.pending };
      case "executed":
        return { ...entry, executed: [...(entry.executed ?? []), ...event.results] };
      case "token":
        return { ...entry, text: entry.text + event.text };
      case "error":
        return { ...entry, error: event.message };
      default:
        return entry;
    }
  }, []);

  const consume = useCallback(
    async (
      id: string,
      events: AsyncGenerator<ServerEvent>,
      patch: (fn: (e: Entry) => Entry) => void,
    ) => {
      for await (const event of events) {
        if (event.type === "thread") {
          thread.current = event.thread_id;
          continue;
        }
        patch((e) => apply(e, event));
      }
      // whatever node was last active has now finished, unless we stopped to ask
      patch((e) => ({
        ...e,
        nodes: e.awaitingApproval
          ? e.nodes
          : e.nodes.map((n) => ({ ...n, state: "done" as const })),
      }));
    },
    [apply],
  );

  async function send(message: string) {
    const text = message.trim();
    if (!text || busy) return;

    const id = crypto.randomUUID();
    setDraft("");
    setBusy(true);
    setActiveCite(null);
    thread.current = null;
    setEntries((prev) => [
      ...prev,
      { id: `${id}-you`, role: "you", at: now(), text, citations: [], nodes: [] },
      { id, role: "asoc", at: now(), text: "", citations: [], nodes: [] },
    ]);

    const patch = (fn: (e: Entry) => Entry) =>
      setEntries((prev) => prev.map((e) => (e.id === id ? fn(e) : e)));

    abort.current = new AbortController();
    try {
      await consume(id, chatStream(text, abort.current.signal), patch);
    } catch (err) {
      const stopped = err instanceof DOMException && err.name === "AbortError";
      patch((e) => ({
        ...e,
        error: stopped ? undefined : "Backend unreachable. Is uvicorn running on port 8001?",
        text: stopped && e.text === "" ? "Stopped." : e.text,
        nodes: e.nodes.map((n) => ({ ...n, state: "done" as const })),
      }));
    } finally {
      setBusy(false);
      abort.current = null;
    }
  }

  async function decide(entryId: string, decision: "approve" | "reject") {
    const threadId = thread.current;
    if (!threadId || busy) return;

    setBusy(true);
    const patch = (fn: (e: Entry) => Entry) =>
      setEntries((prev) => prev.map((e) => (e.id === entryId ? fn(e) : e)));

    patch((e) => ({ ...e, awaitingApproval: false, decision }));

    abort.current = new AbortController();
    try {
      await consume(entryId, approveStream(threadId, decision, abort.current.signal), patch);
    } catch {
      patch((e) => ({ ...e, error: "Could not resume the approval. Is the backend running?" }));
    } finally {
      setBusy(false);
      abort.current = null;
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-10 flex items-center gap-4 border-b border-line bg-ink/90 px-4 py-3 backdrop-blur sm:px-6">
        <h1 className="font-mono text-sm font-medium tracking-[0.2em] text-paper">ASOC</h1>
        <p className="hidden text-xs text-muted sm:block">IT operations copilot</p>
        <span
          className="ml-auto flex items-center gap-2 font-mono text-[11px] text-muted"
          aria-live="polite"
        >
          <span
            aria-hidden
            className="h-1.5 w-1.5 rounded-full"
            style={{
              background:
                qdrantUp === null
                  ? "var(--color-muted)"
                  : qdrantUp
                    ? "var(--color-teal)"
                    : "var(--color-danger)",
            }}
          />
          {qdrantUp === null ? "checking" : qdrantUp ? "index ready" : "index unreachable"}
        </span>
      </header>

      <div className="mx-auto flex w-full max-w-6xl flex-1 gap-8 px-4 py-6 sm:px-6">
        <main className="flex min-w-0 flex-1 flex-col gap-6">
          {entries.length === 0 ? (
            <section className="max-w-xl">
              <h2 className="text-lg text-paper">Ask the runbooks. Or ask for something to be done.</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">
                Twenty operations documents are indexed. Every claim links to the chunk it came
                from, with its retrieval score. Anything that would write to the ticketing system
                stops and waits for you.
              </p>
              <ul className="mt-5 flex flex-col gap-2">
                {EXAMPLES.map((q) => (
                  <li key={q}>
                    <button
                      onClick={() => send(q)}
                      className="w-full cursor-pointer rounded-sm border border-line bg-surface px-3 py-2.5 text-left text-sm text-muted transition-colors duration-200 hover:border-muted/60 hover:text-paper"
                    >
                      {q}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <div className="flex flex-col gap-6">
              {entries.map((e) => (
                <LogEntry
                  key={e.id}
                  entry={e}
                  busy={busy}
                  onCite={setActiveCite}
                  onDecide={(decision) => decide(e.id, decision)}
                />
              ))}
            </div>
          )}
          <div ref={tail} />
        </main>

        <aside className="hidden w-[19rem] shrink-0 lg:block">
          <h2 className="mb-3 font-mono text-[11px] uppercase tracking-widest text-muted">
            Evidence
          </h2>
          <EvidenceRail citations={latest?.citations ?? []} active={activeCite} />
        </aside>
      </div>

      <footer className="sticky bottom-0 border-t border-line bg-ink/90 px-4 py-3 backdrop-blur sm:px-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(draft);
          }}
          className="mx-auto flex w-full max-w-6xl items-end gap-3"
        >
          <label htmlFor="ask" className="sr-only">
            Ask the runbooks
          </label>
          <textarea
            id="ask"
            rows={1}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(draft);
              }
            }}
            placeholder="Ask about a runbook, or ask to open a ticket"
            className="max-h-40 min-h-[2.75rem] flex-1 resize-y rounded-sm border border-line bg-surface px-3 py-2.5 text-[15px] text-paper placeholder:text-muted/70"
          />
          {busy ? (
            <button
              type="button"
              onClick={() => abort.current?.abort()}
              className="h-11 cursor-pointer rounded-sm border border-line px-4 text-sm text-muted transition-colors duration-200 hover:border-danger hover:text-danger"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!draft.trim()}
              className="h-11 cursor-pointer rounded-sm bg-amber px-5 text-sm font-medium text-ink transition-opacity duration-200 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Ask
            </button>
          )}
        </form>
      </footer>
    </div>
  );
}

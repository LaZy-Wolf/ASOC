"use client";

import { useEffect, useRef, useState } from "react";
import { EvidenceRail } from "@/components/EvidenceRail";
import { LogEntry } from "@/components/LogEntry";
import { chatStream } from "@/lib/stream";
import type { Entry } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

const EXAMPLES = [
  "My VPN connects then drops after a minute. What now?",
  "What severity is a database host at 96% disk?",
  "Who approves production write access, and for how long?",
];

const now = () => new Date().toTimeString().slice(0, 8);

export default function Console() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const [qdrantUp, setQdrantUp] = useState<boolean | null>(null);

  const abort = useRef<AbortController | null>(null);
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

  async function send(message: string) {
    const text = message.trim();
    if (!text || busy) return;

    const id = crypto.randomUUID();
    setDraft("");
    setBusy(true);
    setActiveCite(null);
    setEntries((prev) => [
      ...prev,
      {
        id: `${id}-you`,
        role: "you",
        at: now(),
        text,
        citations: [],
        stages: { retrieve: "pending", answer: "pending" },
      },
      {
        id,
        role: "asoc",
        at: now(),
        text: "",
        citations: [],
        stages: { retrieve: "active", answer: "pending" },
      },
    ]);

    const patch = (fn: (e: Entry) => Entry) =>
      setEntries((prev) => prev.map((e) => (e.id === id ? fn(e) : e)));

    abort.current = new AbortController();
    try {
      for await (const event of chatStream(text, abort.current.signal)) {
        if (event.type === "route") {
          patch((e) => ({
            ...e,
            route: event.route,
            topScore: event.top_score,
            confident: event.confident,
          }));
        } else if (event.type === "citations") {
          patch((e) => ({
            ...e,
            citations: event.citations,
            stages: { retrieve: "done", answer: "active" },
          }));
        } else if (event.type === "token") {
          patch((e) => ({ ...e, text: e.text + event.text }));
        } else if (event.type === "error") {
          patch((e) => ({ ...e, error: event.message, stages: { ...e.stages, answer: "done" } }));
        }
      }
      patch((e) => ({ ...e, stages: { retrieve: "done", answer: "done" } }));
    } catch (err) {
      const stopped = err instanceof DOMException && err.name === "AbortError";
      patch((e) => ({
        ...e,
        error: stopped ? undefined : "Backend unreachable. Is uvicorn running on port 8000?",
        text: stopped && e.text === "" ? "Stopped." : e.text,
        stages: { retrieve: "done", answer: "done" },
      }));
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
              <h2 className="text-lg text-paper">Ask the runbooks.</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">
                Twenty operations documents are indexed — runbooks, policies, guides, and
                postmortems. Every claim in an answer links to the chunk it came from, with the
                retrieval score shown.
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
                <LogEntry key={e.id} entry={e} onCite={setActiveCite} />
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
            placeholder="Ask about a runbook, policy, or past incident"
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

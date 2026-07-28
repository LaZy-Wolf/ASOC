export type Citation = {
  n: number;
  chunk_id: string;
  source: string;
  heading_path: string;
  doc_type: string;
  score: number;
  text: string;
};

export type Stage = "retrieve" | "answer";
export type StageState = "pending" | "active" | "done";

export type Entry = {
  id: string;
  role: "you" | "asoc";
  at: string; // HH:MM:SS
  text: string;
  citations: Citation[];
  stages: Record<Stage, StageState>;
  error?: string;
};

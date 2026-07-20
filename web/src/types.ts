// Hermes KB 前端类型定义

export interface Citation {
  id: number;
  doc_id: string;
  title: string;
  snippet: string;
  score: number;
  chunk_rowid: number;
}

export interface RAGAnswer {
  answer_id: string;
  query: string;
  answer: string;
  citations: Citation[];
  model_used: string;
  latency_ms: number;
  rejected: boolean;
  low_confidence: boolean;
}

export interface DocumentItem {
  doc_id: string;
  title: string;
  source_type: string;
  file_type: string;
  chunk_count: number;
  category: string;
  tags: TagInfo[];
  created_at: string | null;
}

export interface TagInfo {
  id: number;
  name: string;
  color: string;
  doc_count?: number;
}

export interface CategoryInfo {
  name: string;
  doc_count: number;
}

export interface ChunkInfo {
  rowid: number;
  idx: number;
  text: string;
  char_start: number;
  char_end: number;
}

export interface DocumentDetail {
  doc: {
    doc_id: string;
    title: string;
    source_type: string;
    file_type: string;
    chunk_count: number;
    category: string;
    content_length: number;
    created_at: string | null;
  };
  tags: TagInfo[];
  chunks: ChunkInfo[];
}

export interface BatchImportResult {
  total: number;
  imported: number;
  failed: number;
  results: Array<{
    filename: string;
    status: "imported" | "failed";
    doc_id?: string;
    chunk_count?: number;
    error?: string;
  }>;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  time?: string;
  doc_count: number;
  llm_provider: string;
  llm_available: boolean;
  embedding_provider: string;
  embedding_available: boolean;
  auth_enabled: boolean;
  age_gate_enabled: boolean;
}

export interface HistoryItem {
  id: number;
  query: string;
  answer: string;
  citations: Citation[];
  model_used: string;
  latency_ms: number;
  feedback: number;
  created_at: string | null;
}

export interface SeedResult {
  seeded: number;
  failed: number;
  items: Array<Record<string, unknown>>;
}

// SSE 流式事件
export type SSEEvent =
  | { type: "meta"; answer_id: string; citations: Citation[]; rejected: boolean; low_confidence: boolean; model_used: string }
  | { type: "delta"; content: string }
  | { type: "done"; latency_ms: number }
  | { type: "error"; message: string };

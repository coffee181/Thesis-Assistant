const API_BASE = "http://127.0.0.1:8765";

export type Paper = {
  id: number;
  title: string;
  year: number | null;
  doi: string | null;
  created_at: string;
};

export type Document = {
  id: number;
  paper_id: number;
  library_path: string;
  file_hash: string;
  page_count: number | null;
  parse_status: string;
  parse_error: string | null;
  created_at: string;
};

export type PapersResponse = {
  papers: Paper[];
};

export type HealthResponse = {
  status: string;
  service: string;
};

export type SearchHit = {
  paper_id: number;
  title: string;
  year: number | null;
  doi: string | null;
  document_id: number;
  chunk_id: number;
  page_number: number;
  snippet: string;
};

export type LocalSearchResponse = {
  query: string;
  hits: SearchHit[];
};

export type ReaderPage = {
  page_number: number;
  text: string;
};

export type ReaderContext = {
  paper: Paper;
  document: Document;
  pages: ReaderPage[];
};

export type ProviderSettings = {
  provider: string;
  base_url: string | null;
  model: string | null;
  outbound_context_policy: string;
  api_key_configured: boolean;
};

export type SaveProviderSettingsRequest = {
  provider: string;
  base_url: string | null;
  model: string | null;
  api_key: string | null;
  outbound_context_policy: string;
};

export type Citation = {
  chunk_id: number;
  paper_id: number;
  title: string;
  page_number: number;
  snippet: string;
  source_span: string;
};

export type AskPaperQuestionResponse = {
  answer: string;
  citations: Citation[];
  mode: string;
  provider: string;
  qna_id: number | null;
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error("Backend health check failed");
  return response.json();
}

export async function listPapers(): Promise<PapersResponse> {
  const response = await fetch(`${API_BASE}/api/papers`);
  if (!response.ok) throw new Error("Could not load papers");
  return response.json();
}

export async function importPdf(sourcePath: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/imports/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_path: sourcePath }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Import failed" }));
    throw new Error(payload.detail ?? "Import failed");
  }
}

export async function searchLocal(query: string): Promise<LocalSearchResponse> {
  const response = await fetch(`${API_BASE}/api/search/local?q=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error("Could not search library");
  return response.json();
}

export async function getReaderContext(paperId: number): Promise<ReaderContext> {
  const response = await fetch(`${API_BASE}/api/papers/${paperId}/reader-context`);
  if (!response.ok) throw new Error("Could not load paper context");
  return response.json();
}

export async function getProviderSettings(): Promise<ProviderSettings> {
  const response = await fetch(`${API_BASE}/api/settings/provider`);
  if (!response.ok) throw new Error("Could not load provider settings");
  return response.json();
}

export async function saveProviderSettings(
  settings: SaveProviderSettingsRequest,
): Promise<ProviderSettings> {
  const response = await fetch(`${API_BASE}/api/settings/provider`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!response.ok) throw new Error("Could not save provider settings");
  return response.json();
}

export async function askPaperQuestion(
  paperId: number,
  question: string,
): Promise<AskPaperQuestionResponse> {
  const response = await fetch(`${API_BASE}/api/papers/${paperId}/assistant/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Ask failed" }));
    throw new Error(payload.detail ?? "Ask failed");
  }
  return response.json();
}

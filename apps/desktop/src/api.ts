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

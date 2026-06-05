const API_BASE = "http://127.0.0.1:8765";

export type Paper = {
  id: number;
  title: string;
  authors: string | null;
  year: number | null;
  doi: string | null;
  venue: string | null;
  abstract: string | null;
  citation_key: string | null;
  arxiv_id: string | null;
  entry_type: string | null;
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

export type ImportBibliographyResponse = {
  format: string;
  imported_count: number;
  updated_count: number;
  papers: Paper[];
};

export type ExportBibliographyResponse = {
  format: string;
  content: string;
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

export type SearchResultRecord = {
  id: number;
  query: string;
  source: string;
  external_id: string;
  title: string;
  authors: string | null;
  year: number | null;
  doi: string | null;
  venue: string | null;
  abstract: string | null;
  arxiv_id: string | null;
  pdf_url: string | null;
  landing_url: string | null;
  created_at: string;
};

export type ExternalSearchResponse = {
  query: string;
  results: SearchResultRecord[];
};

export type OpenPdfDownloadResponse = {
  pending_path: string;
  result: SearchResultRecord;
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
  chunk_id: number | null;
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

export type Note = {
  id: number;
  paper_id: number;
  body: string;
  page_number: number | null;
  source_span: string | null;
  selected_text: string | null;
  note_type: string;
  qna_id: number | null;
  created_at: string;
  updated_at: string;
};

export type NotesResponse = {
  notes: Note[];
};

export type Highlight = {
  id: number;
  paper_id: number;
  page_number: number;
  source_span: string;
  selected_text: string;
  color: string;
  note_id: number | null;
  created_at: string;
};

export type HighlightsResponse = {
  highlights: Highlight[];
};

export type SelectedTextAction = "translate" | "explain" | "summarize";

export type AskSelectedTextRequest = {
  selected_text: string;
  page_number: number;
  source_span: string;
  action: SelectedTextAction;
  instruction?: string | null;
};

export type CreateNoteRequest = {
  paper_id: number;
  body: string;
  page_number: number | null;
  source_span: string | null;
  selected_text: string | null;
  note_type: "manual" | "assistant_answer" | "selection";
  qna_id: number | null;
};

export type CreateHighlightRequest = {
  paper_id: number;
  page_number: number;
  source_span: string;
  selected_text: string;
  color: string;
  note_id: number | null;
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

export async function importBibliography(
  sourcePath: string,
  format: string,
): Promise<ImportBibliographyResponse> {
  const response = await fetch(`${API_BASE}/api/imports/bibliography`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_path: sourcePath, format }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Bibliography import failed" }));
    throw new Error(payload.detail ?? "Bibliography import failed");
  }
  return response.json();
}

export async function exportBibliography(format: "bibtex" | "ris"): Promise<ExportBibliographyResponse> {
  const response = await fetch(`${API_BASE}/api/exports/bibliography?format=${format}`);
  if (!response.ok) throw new Error("Could not export bibliography");
  return response.json();
}

export async function searchLocal(query: string): Promise<LocalSearchResponse> {
  const response = await fetch(`${API_BASE}/api/search/local?q=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error("Could not search library");
  return response.json();
}

export async function searchExternal(query: string): Promise<ExternalSearchResponse> {
  const response = await fetch(`${API_BASE}/api/search/external?q=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error("Could not search external sources");
  return response.json();
}

export async function downloadOpenPdf(searchResultId: number): Promise<OpenPdfDownloadResponse> {
  const response = await fetch(`${API_BASE}/api/downloads/open-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ search_result_id: searchResultId }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Download failed" }));
    throw new Error(payload.detail ?? "Download failed");
  }
  return response.json();
}

export async function importPendingDownload(
  searchResultId: number,
  pendingPath: string,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/imports/pending-download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ search_result_id: searchResultId, pending_path: pendingPath }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Pending import failed" }));
    throw new Error(payload.detail ?? "Pending import failed");
  }
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

export async function askSelectedText(
  paperId: number,
  request: AskSelectedTextRequest,
): Promise<AskPaperQuestionResponse> {
  const response = await fetch(`${API_BASE}/api/papers/${paperId}/assistant/selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Selection ask failed" }));
    throw new Error(payload.detail ?? "Selection ask failed");
  }
  return response.json();
}

export async function createNote(request: CreateNoteRequest): Promise<Note> {
  const response = await fetch(`${API_BASE}/api/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Note save failed" }));
    throw new Error(payload.detail ?? "Note save failed");
  }
  return response.json();
}

export async function listNotes(paperId: number): Promise<NotesResponse> {
  const response = await fetch(`${API_BASE}/api/papers/${paperId}/notes`);
  if (!response.ok) throw new Error("Could not load notes");
  return response.json();
}

export async function createHighlight(request: CreateHighlightRequest): Promise<Highlight> {
  const response = await fetch(`${API_BASE}/api/highlights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Highlight save failed" }));
    throw new Error(payload.detail ?? "Highlight save failed");
  }
  return response.json();
}

export async function listHighlights(paperId: number): Promise<HighlightsResponse> {
  const response = await fetch(`${API_BASE}/api/papers/${paperId}/highlights`);
  if (!response.ok) throw new Error("Could not load highlights");
  return response.json();
}

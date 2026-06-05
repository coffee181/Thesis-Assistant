import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { ProviderSettings } from "./api";

const fetchMock = vi.fn();

const defaultProviderSettings: ProviderSettings = {
  provider: "none",
  base_url: null,
  model: null,
  outbound_context_policy: "snippets_only",
  api_key_configured: false,
};

const configuredProviderSettings: ProviderSettings = {
  provider: "openai_compatible",
  base_url: "https://api.example.test/v1",
  model: "research-model",
  outbound_context_policy: "snippets_only",
  api_key_configured: true,
};

const readerPaper = {
  id: 1,
  title: "Reader Paper",
  authors: null,
  year: null,
  doi: null,
  venue: null,
  abstract: null,
  citation_key: null,
  arxiv_id: null,
  entry_type: null,
  created_at: "now",
};

const readerContextPayload = {
  paper: readerPaper,
  document: {
    id: 4,
    paper_id: 1,
    library_path: "papers/reader/paper.pdf",
    file_hash: "hash",
    page_count: 2,
    parse_status: "parsed",
    parse_error: null,
    created_at: "now",
  },
  pages: [
    { page_number: 1, text: "Page one explains the research question." },
    { page_number: 2, text: "The method uses retrieval augmented generation." },
  ],
};

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

function queueInitialReaderLoad(settings: ProviderSettings = defaultProviderSettings) {
  fetchMock
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ papers: [readerPaper] }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => settings,
    });
}

function queueOpenReaderContext() {
  fetchMock
    .mockResolvedValueOnce({
      ok: true,
      json: async () => readerContextPayload,
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ notes: [] }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ highlights: [] }),
    });
}

async function openReaderPaper() {
  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: "Open Reader Paper" }));
  await screen.findByText("The method uses retrieval augmented generation.");
}

function selectReaderText(text: string) {
  vi.spyOn(window, "getSelection").mockReturnValue({
    toString: () => text,
  } as Selection);
  fireEvent.mouseUp(screen.getByText("The method uses retrieval augmented generation."));
}

function fetchCallBody(path: string) {
  const call = fetchMock.mock.calls.find(([url]) => String(url).includes(path));
  if (!call) throw new Error(`No fetch call matched ${path}`);
  return JSON.parse(String(call[1]?.body ?? "{}"));
}

describe("App", () => {
  it("loads backend status and papers", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [{ id: 1, title: "Paper A", year: null, doi: null, created_at: "now" }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      });

    render(<App />);

    expect(await screen.findByText("Backend: ok")).toBeInTheDocument();
    expect(await screen.findByText("Paper A")).toBeInTheDocument();
    expect(await screen.findByText("Provider: none")).toBeInTheDocument();
  });

  it("imports a PDF by source path", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ imported: true, paper: { id: 2, title: "Imported", year: null, doi: null, created_at: "now" }, document: { id: 1, paper_id: 2, library_path: "papers/imported/paper.pdf", file_hash: "abc", page_count: null, created_at: "now" } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [{ id: 2, title: "Imported", year: null, doi: null, created_at: "now" }] }),
      });

    render(<App />);
    await userEvent.type(screen.getByLabelText("PDF source path"), "F:\\papers\\imported.pdf");
    await userEvent.click(screen.getByRole("button", { name: "Import PDF" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/imports/pdf",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Imported")).toBeInTheDocument();
  });

  it("imports a bibliography file path and refreshes the library", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ format: "bibtex", imported_count: 1, updated_count: 0, papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          papers: [
            {
              id: 3,
              title: "Local Knowledge Agents",
              authors: "Jane Doe and John Smith",
              year: 2024,
              doi: "10.1234/local",
              venue: "Journal of Local Research",
              abstract: null,
              citation_key: "doe2024local",
              arxiv_id: null,
              entry_type: "article",
              created_at: "now",
            },
          ],
        }),
      });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("Bibliography source path"), "F:\\papers\\library.bib");
    await userEvent.selectOptions(screen.getByLabelText("Bibliography format"), "bibtex");
    await userEvent.click(screen.getByRole("button", { name: "Import bibliography" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/imports/bibliography",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Bibliography imported: 1 new, 0 updated")).toBeInTheDocument();
    expect(await screen.findByText("Local Knowledge Agents")).toBeInTheDocument();
  });

  it("displays paper author and year metadata when present", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          papers: [
            {
              id: 1,
              title: "Metadata Paper",
              authors: "Jane Doe and John Smith",
              year: 2024,
              doi: null,
              venue: null,
              abstract: null,
              citation_key: "doe2024metadata",
              arxiv_id: null,
              entry_type: "article",
              created_at: "now",
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      });

    render(<App />);

    expect(await screen.findByText("Metadata Paper")).toBeInTheDocument();
    expect(await screen.findByText("Jane Doe and John Smith · 2024")).toBeInTheDocument();
  });

  it("exports BibTeX and displays it in a preview area", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          format: "bibtex",
          content: "@article{doe2024local,\n  title = {Local Knowledge Agents}\n}",
        }),
      });

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Export BibTeX" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/exports/bibliography?format=bibtex",
      );
    });
    expect(await screen.findByLabelText("Bibliography export preview")).toHaveValue(
      "@article{doe2024local,\n  title = {Local Knowledge Agents}\n}",
    );
  });

  it("searches external papers and displays open PDF availability", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          query: "local rag",
          results: [
            {
              id: 8,
              query: "local rag",
              source: "openalex",
              external_id: "W123",
              title: "Local Knowledge Agents",
              authors: "Jane Doe",
              year: 2024,
              doi: "10.1234/local",
              venue: "Journal of Local Research",
              abstract: "Traceable assistants.",
              arxiv_id: null,
              pdf_url: "https://example.test/local.pdf",
              landing_url: "https://example.test/local",
              created_at: "now",
            },
          ],
        }),
      });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("External search"), "local rag");
    await userEvent.click(screen.getByRole("button", { name: "Search external" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/search/external?q=local%20rag",
      );
    });
    expect(await screen.findByText("Local Knowledge Agents")).toBeInTheDocument();
    expect(await screen.findByText("Jane Doe · 2024")).toBeInTheDocument();
    expect(await screen.findByText("openalex")).toBeInTheDocument();
    expect(await screen.findByText("Open PDF available")).toBeInTheDocument();
  });

  it("downloads an open PDF result and confirms import into the library", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          query: "local rag",
          results: [
            {
              id: 8,
              query: "local rag",
              source: "openalex",
              external_id: "W123",
              title: "Local Knowledge Agents",
              authors: "Jane Doe",
              year: 2024,
              doi: "10.1234/local",
              venue: "Journal of Local Research",
              abstract: "Traceable assistants.",
              arxiv_id: null,
              pdf_url: "https://example.test/local.pdf",
              landing_url: "https://example.test/local",
              created_at: "now",
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          pending_path: "F:\\knowledge-agent-library\\downloads\\pending\\8-local.pdf",
          result: {
            id: 8,
            query: "local rag",
            source: "openalex",
            external_id: "W123",
            title: "Local Knowledge Agents",
            authors: "Jane Doe",
            year: 2024,
            doi: "10.1234/local",
            venue: "Journal of Local Research",
            abstract: "Traceable assistants.",
            arxiv_id: null,
            pdf_url: "https://example.test/local.pdf",
            landing_url: "https://example.test/local",
            created_at: "now",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          imported: true,
          paper: {
            id: 9,
            title: "Local Knowledge Agents",
            authors: "Jane Doe",
            year: 2024,
            doi: "10.1234/local",
            venue: "Journal of Local Research",
            abstract: null,
            citation_key: null,
            arxiv_id: null,
            entry_type: "article",
            created_at: "now",
          },
          document: {
            id: 12,
            paper_id: 9,
            library_path: "papers/2024/local/paper.pdf",
            file_hash: "hash",
            page_count: null,
            parse_status: "failed",
            parse_error: null,
            created_at: "now",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          papers: [
            {
              id: 9,
              title: "Local Knowledge Agents",
              authors: "Jane Doe",
              year: 2024,
              doi: "10.1234/local",
              venue: "Journal of Local Research",
              abstract: null,
              citation_key: null,
              arxiv_id: null,
              entry_type: "article",
              created_at: "now",
            },
          ],
        }),
      });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("External search"), "local rag");
    await userEvent.click(screen.getByRole("button", { name: "Search external" }));
    await userEvent.click(await screen.findByRole("button", { name: "Download PDF" }));
    await userEvent.click(await screen.findByRole("button", { name: "Confirm import" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/imports/pending-download",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Downloaded paper imported")).toBeInTheDocument();
    expect((await screen.findAllByText("Local Knowledge Agents")).length).toBeGreaterThan(0);
  });

  it("shows needs access for external results without open PDF URLs", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          query: "closed paper",
          results: [
            {
              id: 10,
              query: "closed paper",
              source: "openalex",
              external_id: "W999",
              title: "Closed Access Paper",
              authors: null,
              year: 2023,
              doi: null,
              venue: null,
              abstract: null,
              arxiv_id: null,
              pdf_url: null,
              landing_url: "https://example.test/closed",
              created_at: "now",
            },
          ],
        }),
      });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("External search"), "closed paper");
    await userEvent.click(screen.getByRole("button", { name: "Search external" }));

    expect(await screen.findByText("Closed Access Paper")).toBeInTheDocument();
    expect(await screen.findByText("Needs access")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Download PDF" })).not.toBeInTheDocument();
  });

  it("searches the local library and displays page hits", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          query: "contrastive retrieval",
          hits: [
            {
              paper_id: 7,
              title: "Searchable Paper",
              year: 2025,
              doi: null,
              document_id: 3,
              chunk_id: 9,
              page_number: 2,
              snippet: "The method evaluates contrastive retrieval over local literature.",
            },
          ],
        }),
      });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("Search library"), "contrastive retrieval");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/search/local?q=contrastive%20retrieval",
      );
    });
    expect(await screen.findByText("Searchable Paper")).toBeInTheDocument();
    expect(await screen.findByText("Page 2")).toBeInTheDocument();
    expect(await screen.findByText("The method evaluates contrastive retrieval over local literature.")).toBeInTheDocument();
  });

  it("opens a paper and displays reader context for the assistant", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [{ id: 1, title: "Reader Paper", year: null, doi: null, created_at: "now" }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          paper: { id: 1, title: "Reader Paper", year: null, doi: null, created_at: "now" },
          document: {
            id: 4,
            paper_id: 1,
            library_path: "papers/reader/paper.pdf",
            file_hash: "hash",
            page_count: 2,
            parse_status: "parsed",
            parse_error: null,
            created_at: "now",
          },
          pages: [
            { page_number: 1, text: "Page one explains the research question." },
            { page_number: 2, text: "Page two describes the experimental setup." },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ notes: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ highlights: [] }),
      });

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Open Reader Paper" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8765/api/papers/1/reader-context");
    });
    expect(await screen.findByText("Page 1")).toBeInTheDocument();
    expect(await screen.findByText("Page one explains the research question.")).toBeInTheDocument();
    expect(await screen.findByText("Context: Reader Paper - parsed")).toBeInTheDocument();
  });

  it("shows selected reader text in the assistant panel", async () => {
    queueInitialReaderLoad();
    queueOpenReaderContext();

    await openReaderPaper();
    selectReaderText("retrieval augmented generation");

    expect(await screen.findByText("Selected text")).toBeInTheDocument();
    expect(screen.getByText("retrieval augmented generation")).toBeInTheDocument();
  });

  it("translates selected text through the selected assistant endpoint", async () => {
    queueInitialReaderLoad(configuredProviderSettings);
    queueOpenReaderContext();
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        answer: "Selected translation",
        mode: "selection",
        provider: "openai_compatible",
        qna_id: 13,
        citations: [
          {
            chunk_id: null,
            paper_id: 1,
            title: "Reader Paper",
            page_number: 2,
            snippet: "retrieval augmented generation",
            source_span: "page:2:selection",
          },
        ],
      }),
    });

    await openReaderPaper();
    selectReaderText("retrieval augmented generation");
    await userEvent.click(await screen.findByRole("button", { name: "Translate selection" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/papers/1/assistant/selection",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchCallBody("/assistant/selection")).toMatchObject({
      selected_text: "retrieval augmented generation",
      page_number: 2,
      source_span: "page:2:selection",
      action: "translate",
    });
    expect(await screen.findByText("Selected translation")).toBeInTheDocument();
    expect(await screen.findByText("Citation Page 2")).toBeInTheDocument();
  });

  it("explains selected text with the explain action", async () => {
    queueInitialReaderLoad(configuredProviderSettings);
    queueOpenReaderContext();
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        answer: "Selected explanation",
        mode: "selection",
        provider: "openai_compatible",
        qna_id: 14,
        citations: [
          {
            chunk_id: null,
            paper_id: 1,
            title: "Reader Paper",
            page_number: 2,
            snippet: "retrieval augmented generation",
            source_span: "page:2:selection",
          },
        ],
      }),
    });

    await openReaderPaper();
    selectReaderText("retrieval augmented generation");
    await userEvent.click(await screen.findByRole("button", { name: "Explain selection" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/papers/1/assistant/selection",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchCallBody("/assistant/selection")).toMatchObject({
      action: "explain",
    });
    expect(await screen.findByText("Selected explanation")).toBeInTheDocument();
  });

  it("highlights selected text and displays it in the paper notes area", async () => {
    queueInitialReaderLoad();
    queueOpenReaderContext();
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 21,
        paper_id: 1,
        page_number: 2,
        source_span: "page:2:selection",
        selected_text: "retrieval augmented generation",
        color: "yellow",
        note_id: null,
        created_at: "now",
      }),
    });

    await openReaderPaper();
    selectReaderText("retrieval augmented generation");
    await userEvent.click(await screen.findByRole("button", { name: "Highlight selection" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/highlights",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchCallBody("/api/highlights")).toMatchObject({
      paper_id: 1,
      page_number: 2,
      source_span: "page:2:selection",
      selected_text: "retrieval augmented generation",
      color: "yellow",
    });
    expect(await screen.findByText("Highlight Page 2")).toBeInTheDocument();
  });

  it("saves a selected assistant answer as a note", async () => {
    queueInitialReaderLoad(configuredProviderSettings);
    queueOpenReaderContext();
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: "Selected translation",
          mode: "selection",
          provider: "openai_compatible",
          qna_id: 13,
          citations: [
            {
              chunk_id: null,
              paper_id: 1,
              title: "Reader Paper",
              page_number: 2,
              snippet: "retrieval augmented generation",
              source_span: "page:2:selection",
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 31,
          paper_id: 1,
          body: "Selected translation",
          page_number: 2,
          source_span: "page:2:selection",
          selected_text: "retrieval augmented generation",
          note_type: "assistant_answer",
          qna_id: 13,
          created_at: "now",
          updated_at: "now",
        }),
      });

    await openReaderPaper();
    selectReaderText("retrieval augmented generation");
    await userEvent.click(await screen.findByRole("button", { name: "Translate selection" }));
    await screen.findByText("Selected translation");
    await userEvent.click(screen.getByRole("button", { name: "Save answer as note" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/notes",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchCallBody("/api/notes")).toMatchObject({
      paper_id: 1,
      body: "Selected translation",
      page_number: 2,
      source_span: "page:2:selection",
      selected_text: "retrieval augmented generation",
      note_type: "assistant_answer",
      qna_id: 13,
    });
    expect(await screen.findByText("Note Page 2")).toBeInTheDocument();
  });

  it("saves provider settings without displaying the raw API key", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          provider: "openai_compatible",
          base_url: "https://api.example.test/v1",
          model: "research-model",
          outbound_context_policy: "snippets_only",
          api_key_configured: true,
        }),
      });

    render(<App />);
    await userEvent.selectOptions(await screen.findByLabelText("Provider"), "openai_compatible");
    await userEvent.type(screen.getByLabelText("Base URL"), "https://api.example.test/v1");
    await userEvent.type(screen.getByLabelText("Model"), "research-model");
    await userEvent.type(screen.getByLabelText("API key"), "secret-key");
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/settings/provider",
        expect.objectContaining({ method: "PUT" }),
      );
    });
    expect(await screen.findByText("Provider: openai_compatible")).toBeInTheDocument();
    expect(await screen.findByText("API key configured")).toBeInTheDocument();
    expect(screen.queryByText("secret-key")).not.toBeInTheDocument();
  });

  it("asks a current-paper question and displays cited snippets", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [{ id: 1, title: "Reader Paper", year: null, doi: null, created_at: "now" }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...configuredProviderSettings,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          paper: { id: 1, title: "Reader Paper", year: null, doi: null, created_at: "now" },
          document: {
            id: 4,
            paper_id: 1,
            library_path: "papers/reader/paper.pdf",
            file_hash: "hash",
            page_count: 2,
            parse_status: "parsed",
            parse_error: null,
            created_at: "now",
          },
          pages: [
            { page_number: 1, text: "Page one explains the research question." },
            { page_number: 2, text: "The method uses retrieval augmented generation." },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ notes: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ highlights: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: "该方法使用检索增强生成。",
          mode: "strict",
          provider: "openai_compatible",
          qna_id: 11,
          citations: [
            {
              chunk_id: 5,
              paper_id: 1,
              title: "Reader Paper",
              page_number: 2,
              snippet: "The cited snippet says retrieval augmented generation.",
              source_span: "page:2:chars:0-47",
            },
          ],
        }),
      });

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Open Reader Paper" }));
    await userEvent.type(await screen.findByLabelText("Question"), "What method is used?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/papers/1/assistant/ask",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("该方法使用检索增强生成。")).toBeInTheDocument();
    expect(await screen.findByText("Citation Page 2")).toBeInTheDocument();
    expect(await screen.findByText("The cited snippet says retrieval augmented generation.")).toBeInTheDocument();
  });
});

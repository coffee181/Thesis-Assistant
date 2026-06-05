import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  proxy_url: null,
  api_key_configured: false,
};

const configuredProviderSettings: ProviderSettings = {
  provider: "openai_compatible",
  base_url: "https://api.example.test/v1",
  model: "research-model",
  outbound_context_policy: "snippets_only",
  proxy_url: null,
  api_key_configured: true,
};

const defaultLibraryStatus = {
  library_dir: "F:\\KnowledgeAgentLibrary",
  database_path: "F:\\KnowledgeAgentLibrary\\database.sqlite",
  paper_count: 0,
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

const emptyJobsResponse = { jobs: [] };

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
      json: async () => defaultLibraryStatus,
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ papers: [readerPaper] }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => settings,
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => emptyJobsResponse,
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

function jsonResponse(payload: unknown) {
  return {
    ok: true,
    json: async () => payload,
  };
}

function streamResponse(chunks: string[], delayMs = 0) {
  return {
    ok: true,
    body: new ReadableStream<Uint8Array>({
      async start(controller) {
        const encoder = new TextEncoder();
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk));
          if (delayMs > 0) {
            await new Promise((resolve) => window.setTimeout(resolve, delayMs));
          }
        }
        controller.close();
      },
    }),
  };
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
        json: async () => defaultLibraryStatus,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [{ id: 1, title: "Paper A", year: null, doi: null, created_at: "now" }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultProviderSettings,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => emptyJobsResponse,
      });

    render(<App />);

    expect(await screen.findByText("Backend ok")).toBeInTheDocument();
    expect(await screen.findByText("Paper A")).toBeInTheDocument();
    expect(screen.queryByText("Provider: none")).not.toBeInTheDocument();
  });

  it("shows a reader-centered shell and hides low-frequency controls by default", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ status: "ok", service: "knowledge-agent-backend" }))
      .mockResolvedValueOnce(jsonResponse(defaultLibraryStatus))
      .mockResolvedValueOnce(jsonResponse({ papers: [] }))
      .mockResolvedValueOnce(jsonResponse(defaultProviderSettings))
      .mockResolvedValueOnce(jsonResponse(emptyJobsResponse));

    render(<App />);

    expect(await screen.findByRole("banner", { name: "Thesis Assistant workspace" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Thesis Assistant" })).toBeInTheDocument();
    expect(screen.getByText("Backend ok")).toBeInTheDocument();
    expect(screen.getByText("0 papers")).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search library or DOI" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Discover" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Jobs" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();

    expect(screen.getByRole("navigation", { name: "Library" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Start your research library" })).toBeInTheDocument();
    expect(screen.getByText("Import papers or discover literature to begin reading with cited context.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import papers" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Discover literature" })).toBeInTheDocument();
    expect(screen.getByText("Configure a model provider to ask questions about the current paper.")).toBeInTheDocument();

    expect(screen.queryByLabelText("PDF source path")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("PDF folder path")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Bibliography source path")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Provider")).not.toBeInTheDocument();
    expect(screen.queryByText("No recent jobs.")).not.toBeInTheDocument();
    expect(screen.queryByText("No search hits.")).not.toBeInTheDocument();
    expect(screen.queryByText("No external results.")).not.toBeInTheDocument();
  });

  it("waits for a backend that is still starting", async () => {
    fetchMock
      .mockRejectedValueOnce(new Error("connection refused"))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
      });

    render(<App />);

    expect(await screen.findByText("Backend ok")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(6);
  });

  it("loads library status and displays the active library path", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok", service: "knowledge-agent-backend" });
      }
      if (url.endsWith("/api/library")) {
        return jsonResponse(defaultLibraryStatus);
      }
      if (url.endsWith("/api/papers")) {
        return jsonResponse({ papers: [] });
      }
      if (url.endsWith("/api/settings/provider")) {
        return jsonResponse(defaultProviderSettings);
      }
      if (url.endsWith("/api/jobs")) {
        return jsonResponse(emptyJobsResponse);
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Settings" }));
    const dialog = screen.getByRole("dialog", { name: "Settings" });
    expect(within(dialog).getByLabelText("Library location")).toHaveValue("F:\\KnowledgeAgentLibrary");
    const urls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(urls.indexOf("http://127.0.0.1:8765/api/library")).toBeLessThan(
      urls.indexOf("http://127.0.0.1:8765/api/papers"),
    );
  });

  it("selects a new library path and refreshes papers", async () => {
    const selectedLibrary = {
      library_dir: "D:\\ResearchLibrary",
      database_path: "D:\\ResearchLibrary\\database.sqlite",
      paper_count: 1,
    };
    let paperLoads = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok", service: "knowledge-agent-backend" });
      }
      if (url.endsWith("/api/library") && init?.method === "PUT") {
        return jsonResponse(selectedLibrary);
      }
      if (url.endsWith("/api/library")) {
        return jsonResponse(defaultLibraryStatus);
      }
      if (url.endsWith("/api/papers")) {
        paperLoads += 1;
        return jsonResponse({
          papers: paperLoads === 1 ? [] : [{ ...readerPaper, id: 5, title: "Switched Paper" }],
        });
      }
      if (url.endsWith("/api/settings/provider")) {
        return jsonResponse(defaultProviderSettings);
      }
      if (url.endsWith("/api/jobs")) {
        return jsonResponse(emptyJobsResponse);
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Settings" }));
    const dialog = screen.getByRole("dialog", { name: "Settings" });
    await userEvent.clear(within(dialog).getByLabelText("Library location"));
    await userEvent.type(within(dialog).getByLabelText("Library location"), "D:\\ResearchLibrary");
    await userEvent.click(within(dialog).getByRole("button", { name: "Select library" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/library",
        expect.objectContaining({ method: "PUT" }),
      );
    });
    const selectCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url).endsWith("/api/library") && init?.method === "PUT",
    );
    expect(JSON.parse(String(selectCall?.[1]?.body))).toEqual({
      library_dir: "D:\\ResearchLibrary",
    });
    expect(await screen.findByText("Library selected")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Settings" })).not.toBeInTheDocument();
    expect(await screen.findByText("Switched Paper")).toBeInTheDocument();
  });

  it("clears paper-specific state when selecting a new library", async () => {
    const selectedLibrary = {
      library_dir: "D:\\ResearchLibrary",
      database_path: "D:\\ResearchLibrary\\database.sqlite",
      paper_count: 0,
    };
    let paperLoads = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok", service: "knowledge-agent-backend" });
      }
      if (url.endsWith("/api/library") && init?.method === "PUT") {
        return jsonResponse(selectedLibrary);
      }
      if (url.endsWith("/api/library")) {
        return jsonResponse(defaultLibraryStatus);
      }
      if (url.endsWith("/api/papers")) {
        paperLoads += 1;
        return jsonResponse({ papers: paperLoads === 1 ? [readerPaper] : [] });
      }
      if (url.endsWith("/api/settings/provider")) {
        return jsonResponse(configuredProviderSettings);
      }
      if (url.endsWith("/api/jobs")) {
        return jsonResponse(emptyJobsResponse);
      }
      if (url.endsWith("/api/papers/1/reader-context")) {
        return jsonResponse(readerContextPayload);
      }
      if (url.endsWith("/api/papers/1/notes")) {
        return jsonResponse({
          notes: [
            {
              id: 41,
              paper_id: 1,
              body: "Old library note",
              page_number: 2,
              source_span: "page:2:selection",
              selected_text: "old selected note text",
              note_type: "selection",
              qna_id: null,
              created_at: "now",
              updated_at: "now",
            },
          ],
        });
      }
      if (url.endsWith("/api/papers/1/highlights")) {
        return jsonResponse({
          highlights: [
            {
              id: 51,
              paper_id: 1,
              page_number: 2,
              source_span: "page:2:selection",
              selected_text: "Old highlight text",
              color: "yellow",
              note_id: null,
              created_at: "now",
            },
          ],
        });
      }
      if (url.endsWith("/api/papers/1/assistant/selection")) {
        return jsonResponse({
          answer: "Old selected answer",
          mode: "selection",
          provider: "openai_compatible",
          qna_id: 61,
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
        });
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Open Reader Paper" }));
    expect(await screen.findByText("Old library note")).toBeInTheDocument();
    expect(await screen.findByText("Old highlight text")).toBeInTheDocument();
    selectReaderText("retrieval augmented generation");
    await userEvent.click(await screen.findByRole("button", { name: "Translate" }));
    expect(await screen.findByText("Old selected answer")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    const dialog = screen.getByRole("dialog", { name: "Settings" });
    await userEvent.clear(within(dialog).getByLabelText("Library location"));
    await userEvent.type(within(dialog).getByLabelText("Library location"), "D:\\ResearchLibrary");
    await userEvent.click(within(dialog).getByRole("button", { name: "Select library" }));

    expect(await screen.findByText("Library selected")).toBeInTheDocument();
    expect(screen.queryByText("Old selected answer")).not.toBeInTheDocument();
    expect(screen.queryByText("Old library note")).not.toBeInTheDocument();
    expect(screen.queryByText("Old highlight text")).not.toBeInTheDocument();
    expect(screen.getByText("Context: no paper open")).toBeInTheDocument();
  });

  it("job panel queues a PDF folder import and refreshes job progress", async () => {
    let paperLoads = 0;
    let jobLoads = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok", service: "knowledge-agent-backend" });
      }
      if (url.endsWith("/api/library")) {
        return jsonResponse(defaultLibraryStatus);
      }
      if (url.endsWith("/api/imports/folder") && init?.method === "POST") {
        return jsonResponse({
          id: 41,
          kind: "folder_import",
          status: "queued",
          source_path: "F:\\incoming",
          description: "Import folder F:\\incoming",
          total_items: 0,
          processed_items: 0,
          succeeded_items: 0,
          failed_items: 0,
          error: null,
          result_json: null,
          created_at: "now",
          updated_at: "now",
        });
      }
      if (url.endsWith("/api/jobs")) {
        jobLoads += 1;
        return jsonResponse({
          jobs:
            jobLoads === 1
              ? []
              : [
                  {
                    id: 41,
                    kind: "folder_import",
                    status: "succeeded",
                    source_path: "F:\\incoming",
                    description: "Import folder F:\\incoming",
                    total_items: 3,
                    processed_items: 3,
                    succeeded_items: 2,
                    failed_items: 1,
                    error: null,
                    result_json: null,
                    created_at: "now",
                    updated_at: "later",
                  },
                ],
        });
      }
      if (url.endsWith("/api/papers")) {
        paperLoads += 1;
        return jsonResponse({
          papers: paperLoads === 1 ? [] : [{ ...readerPaper, id: 6, title: "Folder Paper" }],
        });
      }
      if (url.endsWith("/api/settings/provider")) {
        return jsonResponse(defaultProviderSettings);
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("PDF folder path"), "F:\\incoming");
    await userEvent.click(screen.getByRole("button", { name: "Import folder" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/imports/folder",
        expect.objectContaining({ method: "POST" }),
      );
    });
    const importCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url).endsWith("/api/imports/folder") && init?.method === "POST",
    );
    expect(JSON.parse(String(importCall?.[1]?.body))).toEqual({
      source_dir: "F:\\incoming",
    });
    expect(await screen.findByText("Folder import queued")).toBeInTheDocument();
    expect(await screen.findByText("folder_import - succeeded")).toBeInTheDocument();
    expect(await screen.findByText("3 / 3 processed")).toBeInTheDocument();
    expect(await screen.findByText("2 succeeded, 1 failed")).toBeInTheDocument();
    expect(await screen.findByText("Folder Paper")).toBeInTheDocument();
  });

  it("job panel retries a failed folder import job", async () => {
    let jobLoads = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok", service: "knowledge-agent-backend" });
      }
      if (url.endsWith("/api/library")) {
        return jsonResponse(defaultLibraryStatus);
      }
      if (url.endsWith("/api/papers")) {
        return jsonResponse({ papers: [] });
      }
      if (url.endsWith("/api/settings/provider")) {
        return jsonResponse(defaultProviderSettings);
      }
      if (url.endsWith("/api/jobs/7/retry") && init?.method === "POST") {
        return jsonResponse({
          id: 8,
          kind: "folder_import",
          status: "queued",
          source_path: "F:\\incoming",
          description: "Import folder F:\\incoming",
          total_items: 0,
          processed_items: 0,
          succeeded_items: 0,
          failed_items: 0,
          error: null,
          result_json: null,
          created_at: "now",
          updated_at: "now",
        });
      }
      if (url.endsWith("/api/jobs")) {
        jobLoads += 1;
        return jsonResponse({
          jobs:
            jobLoads === 1
              ? [
                  {
                    id: 7,
                    kind: "folder_import",
                    status: "failed",
                    source_path: "F:\\incoming",
                    description: "Import folder F:\\incoming",
                    total_items: 3,
                    processed_items: 1,
                    succeeded_items: 0,
                    failed_items: 1,
                    error: "source path is not a folder",
                    result_json: null,
                    created_at: "earlier",
                    updated_at: "earlier",
                  },
                ]
              : [
                  {
                    id: 8,
                    kind: "folder_import",
                    status: "queued",
                    source_path: "F:\\incoming",
                    description: "Import folder F:\\incoming",
                    total_items: 0,
                    processed_items: 0,
                    succeeded_items: 0,
                    failed_items: 0,
                    error: null,
                    result_json: null,
                    created_at: "now",
                    updated_at: "now",
                  },
                ],
        });
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    render(<App />);
    expect(await screen.findByText("folder_import - failed")).toBeInTheDocument();
    expect(await screen.findByText("source path is not a folder")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry job 7" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/jobs/7/retry",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Job retry queued")).toBeInTheDocument();
    expect(await screen.findByText("folder_import - queued")).toBeInTheDocument();
  });

  it("imports a PDF from the import dialog", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
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
    await userEvent.click(await screen.findByRole("button", { name: "Import" }));

    const dialog = screen.getByRole("dialog", { name: "Import papers" });
    await userEvent.type(within(dialog).getByLabelText("PDF source path"), "F:\\papers\\imported.pdf");
    await userEvent.click(within(dialog).getByRole("button", { name: "Import PDF" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/imports/pdf",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchCallBody("/api/imports/pdf")).toEqual({ source_path: "F:\\papers\\imported.pdf" });
    expect(await screen.findByText("PDF imported")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Import papers" })).not.toBeInTheDocument();
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
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
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
    await userEvent.click(await screen.findByRole("button", { name: "Import" }));

    const dialog = screen.getByRole("dialog", { name: "Import papers" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Bibliography" }));
    await userEvent.type(within(dialog).getByLabelText("Bibliography source path"), "F:\\papers\\library.bib");
    await userEvent.selectOptions(within(dialog).getByLabelText("Bibliography format"), "bibtex");
    await userEvent.click(within(dialog).getByRole("button", { name: "Import bibliography" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/imports/bibliography",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Bibliography imported: 1 new, 0 updated")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Import papers" })).not.toBeInTheDocument();
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
        json: async () => defaultLibraryStatus,
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
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => emptyJobsResponse,
      });

    render(<App />);

    expect(await screen.findByText("Metadata Paper")).toBeInTheDocument();
    expect(await screen.findByText("Jane Doe and John Smith · 2024")).toBeInTheDocument();
  });

  it("paper organization toggles a paper favorite from the library row", async () => {
    let paperLoads = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok", service: "knowledge-agent-backend" });
      }
      if (url.endsWith("/api/library")) {
        return jsonResponse(defaultLibraryStatus);
      }
      if (url.endsWith("/api/settings/provider")) {
        return jsonResponse(defaultProviderSettings);
      }
      if (url.endsWith("/api/jobs")) {
        return jsonResponse(emptyJobsResponse);
      }
      if (url.endsWith("/api/papers/1/favorite") && init?.method === "PUT") {
        return jsonResponse({ ...readerPaper, title: "Org Paper", favorite: true, tags: [] });
      }
      if (url.endsWith("/api/papers")) {
        paperLoads += 1;
        return jsonResponse({
          papers: [
            {
              ...readerPaper,
              title: "Org Paper",
              favorite: paperLoads > 1,
              tags: [],
            },
          ],
        });
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Mark Org Paper as favorite" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/papers/1/favorite",
        expect.objectContaining({ method: "PUT" }),
      );
    });
    expect(fetchCallBody("/favorite")).toEqual({ favorite: true });
    expect(await screen.findByRole("button", { name: "Remove Org Paper from favorites" })).toBeInTheDocument();
  });

  it("paper organization adds a tag to a paper", async () => {
    let paperLoads = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok", service: "knowledge-agent-backend" });
      }
      if (url.endsWith("/api/library")) {
        return jsonResponse(defaultLibraryStatus);
      }
      if (url.endsWith("/api/settings/provider")) {
        return jsonResponse(defaultProviderSettings);
      }
      if (url.endsWith("/api/jobs")) {
        return jsonResponse(emptyJobsResponse);
      }
      if (url.endsWith("/api/papers/1/tags") && init?.method === "POST") {
        return jsonResponse({ ...readerPaper, title: "Org Paper", favorite: false, tags: ["reading"] });
      }
      if (url.endsWith("/api/papers")) {
        paperLoads += 1;
        return jsonResponse({
          papers: [
            {
              ...readerPaper,
              title: "Org Paper",
              favorite: false,
              tags: paperLoads > 1 ? ["reading"] : [],
            },
          ],
        });
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("Tag Org Paper"), "reading");
    await userEvent.click(screen.getByRole("button", { name: "Add tag to Org Paper" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/papers/1/tags",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchCallBody("/tags")).toEqual({ name: "reading" });
    expect(await screen.findByText("reading")).toBeInTheDocument();
  });

  it("paper organization filters the library by favorite and tag", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok", service: "knowledge-agent-backend" });
      }
      if (url.endsWith("/api/library")) {
        return jsonResponse(defaultLibraryStatus);
      }
      if (url.endsWith("/api/settings/provider")) {
        return jsonResponse(defaultProviderSettings);
      }
      if (url.endsWith("/api/jobs")) {
        return jsonResponse(emptyJobsResponse);
      }
      if (url.endsWith("/api/papers?favorite=true&tag=reading")) {
        return jsonResponse({
          papers: [{ ...readerPaper, title: "Filtered Paper", favorite: true, tags: ["reading"] }],
        });
      }
      if (url.endsWith("/api/papers")) {
        return jsonResponse({
          papers: [{ ...readerPaper, title: "Unfiltered Paper", favorite: false, tags: [] }],
        });
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    render(<App />);
    await userEvent.click(await screen.findByLabelText("Favorites only"));
    await userEvent.type(screen.getByLabelText("Filter by tag"), "reading");
    await userEvent.click(screen.getByRole("button", { name: "Apply library filters" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8765/api/papers?favorite=true&tag=reading");
    });
    expect(await screen.findByText("Filtered Paper")).toBeInTheDocument();
  });

  it("exports BibTeX and displays it in a preview area", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          format: "bibtex",
          content: "@article{doe2024local,\n  title = {Local Knowledge Agents}\n}",
        }),
      });

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Import" }));

    const dialog = screen.getByRole("dialog", { name: "Import papers" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Bibliography" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Export BibTeX" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/exports/bibliography?format=bibtex",
      );
    });
    expect(await within(dialog).findByLabelText("Bibliography export preview")).toHaveValue(
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
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
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
    await userEvent.click(await screen.findByRole("button", { name: "Discover" }));
    expect(screen.getByRole("complementary", { name: "Discover literature" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("External search"), "local rag");
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
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
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
    await userEvent.click(await screen.findByRole("button", { name: "Discover" }));
    expect(screen.getByRole("complementary", { name: "Discover literature" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("External search"), "local rag");
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
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
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
    await userEvent.click(await screen.findByRole("button", { name: "Discover" }));
    expect(screen.getByRole("complementary", { name: "Discover literature" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("External search"), "closed paper");
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
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
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

  it("displays metadata-only local search hits without page links", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          query: "10.1234/traceable",
          hits: [
            {
              paper_id: 12,
              title: "Traceable Literature Assistants",
              year: 2024,
              doi: "10.1234/traceable",
              document_id: null,
              chunk_id: null,
              page_number: null,
              snippet:
                "Traceable Literature Assistants. Jane Doe and John Smith. DOI 10.1234/traceable.",
            },
          ],
        }),
      });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("Search library"), "10.1234/traceable");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("Traceable Literature Assistants")).toBeInTheDocument();
    expect(await screen.findByText("Metadata match")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Open Traceable Literature Assistants page null",
      }),
    ).not.toBeInTheDocument();
  });

  it("opens a paper and displays reader context for the assistant", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
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

  it("opens the managed PDF preview while keeping extracted text selectable", async () => {
    queueInitialReaderLoad();
    queueOpenReaderContext();

    await openReaderPaper();

    const preview = await screen.findByTitle("PDF reader for Reader Paper");
    expect(preview).toHaveAttribute(
      "src",
      "http://127.0.0.1:8765/api/papers/1/pdf",
    );
    expect(await screen.findByText("The method uses retrieval augmented generation.")).toBeInTheDocument();
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

  it("saves selected text directly as a note", async () => {
    queueInitialReaderLoad();
    queueOpenReaderContext();
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 32,
        paper_id: 1,
        body: "retrieval augmented generation",
        page_number: 2,
        source_span: "page:2:selection",
        selected_text: "retrieval augmented generation",
        note_type: "selection",
        qna_id: null,
        created_at: "now",
        updated_at: "now",
      }),
    });

    await openReaderPaper();
    selectReaderText("retrieval augmented generation");
    await userEvent.click(await screen.findByRole("button", { name: "Save selection as note" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/notes",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchCallBody("/api/notes")).toMatchObject({
      paper_id: 1,
      body: "retrieval augmented generation",
      page_number: 2,
      source_span: "page:2:selection",
      selected_text: "retrieval augmented generation",
      note_type: "selection",
      qna_id: null,
    });
    expect(await screen.findByText("Note Page 2")).toBeInTheDocument();
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
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          provider: "openai_compatible",
          base_url: "https://api.example.test/v1",
          model: "research-model",
          outbound_context_policy: "snippets_only",
          proxy_url: "http://127.0.0.1:7897",
          api_key_configured: true,
        }),
      });

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Settings" }));
    const dialog = screen.getByRole("dialog", { name: "Settings" });
    await userEvent.selectOptions(within(dialog).getByLabelText("Provider"), "openai_compatible");
    await userEvent.type(within(dialog).getByLabelText("Base URL"), "https://api.example.test/v1");
    await userEvent.type(within(dialog).getByLabelText("Proxy URL"), "http://127.0.0.1:7897");
    await userEvent.type(within(dialog).getByLabelText("Model"), "research-model");
    await userEvent.type(within(dialog).getByLabelText("API key"), "secret-key");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save settings" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/settings/provider",
        expect.objectContaining({ method: "PUT" }),
      );
    });
    const settingsCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url).endsWith("/api/settings/provider") && init?.method === "PUT",
    );
    expect(JSON.parse(String(settingsCall?.[1]?.body ?? "{}"))).toMatchObject({
      provider: "openai_compatible",
      base_url: "https://api.example.test/v1",
      model: "research-model",
      api_key: "secret-key",
      outbound_context_policy: "snippets_only",
      proxy_url: "http://127.0.0.1:7897",
    });
    expect(screen.queryByRole("dialog", { name: "Settings" })).not.toBeInTheDocument();
    expect(screen.queryByText("secret-key")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    const savedDialog = screen.getByRole("dialog", { name: "Settings" });
    expect(within(savedDialog).getByLabelText("Provider")).toHaveValue("openai_compatible");
    expect(within(savedDialog).getByText("API key configured")).toBeInTheDocument();
    expect(within(savedDialog).queryByText("secret-key")).not.toBeInTheDocument();
  });

  it("opens a cited page from an assistant citation", async () => {
    queueInitialReaderLoad(configuredProviderSettings);
    queueOpenReaderContext();
    fetchMock.mockImplementationOnce(async () =>
      streamResponse([
        'event: final\ndata: {"answer":"The method uses retrieval augmented generation.","citations":[{"chunk_id":5,"paper_id":1,"title":"Reader Paper","page_number":2,"snippet":"The cited snippet says retrieval augmented generation.","source_span":"page:2:chars:0-47"}],"mode":"strict","provider":"openai_compatible","qna_id":11}\n\n',
      ]),
    );

    await openReaderPaper();
    await userEvent.type(await screen.findByLabelText("Question"), "What method is used?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    await userEvent.click(await screen.findByRole("button", { name: "Open citation page 2" }));

    expect(screen.getByTitle("PDF reader for Reader Paper")).toHaveAttribute(
      "src",
      "http://127.0.0.1:8765/api/papers/1/pdf#page=2",
    );
    expect(screen.getByLabelText("Reader page 2")).toHaveAttribute("aria-current", "page");
  });

  it("streams current-paper ask progress before displaying the final answer", async () => {
    queueInitialReaderLoad(configuredProviderSettings);
    queueOpenReaderContext();
    fetchMock.mockImplementationOnce(async () =>
      streamResponse([
        'event: started\ndata: {"paper_id":1}\n\n',
        'event: context\ndata: {"citation_count":1}\n\n',
        'event: final\ndata: {"answer":"Streamed answer","citations":[{"chunk_id":5,"paper_id":1,"title":"Reader Paper","page_number":2,"snippet":"The cited snippet says retrieval augmented generation.","source_span":"page:2:chars:0-47"}],"mode":"strict","provider":"openai_compatible","qna_id":11}\n\n',
      ], 25),
    );

    await openReaderPaper();
    await userEvent.type(await screen.findByLabelText("Question"), "What method is used?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/papers/1/assistant/ask/stream",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Gathering cited context...")).toBeInTheDocument();
    expect(await screen.findByText("Streamed answer")).toBeInTheDocument();
    expect(await screen.findByText("Citation Page 2")).toBeInTheDocument();
  });

  it("falls back to sync current-paper ask when streaming fails", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => defaultLibraryStatus,
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
        json: async () => emptyJobsResponse,
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
        ok: false,
        json: async () => ({ detail: "Stream unavailable" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: "Fallback answer",
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
        "http://127.0.0.1:8765/api/papers/1/assistant/ask/stream",
        expect.objectContaining({ method: "POST" }),
      );
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/papers/1/assistant/ask",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Fallback answer")).toBeInTheDocument();
    expect(await screen.findByText("Citation Page 2")).toBeInTheDocument();
    expect(await screen.findByText("The cited snippet says retrieval augmented generation.")).toBeInTheDocument();
  });
});

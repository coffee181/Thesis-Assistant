import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

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
      });

    render(<App />);

    expect(await screen.findByText("Backend: ok")).toBeInTheDocument();
    expect(await screen.findByText("Paper A")).toBeInTheDocument();
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
});

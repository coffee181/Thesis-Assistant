import { FormEvent, useEffect, useState } from "react";

import {
  getHealth,
  getReaderContext,
  importPdf,
  listPapers,
  Paper,
  ReaderContext,
  SearchHit,
  searchLocal,
} from "./api";
import "./styles.css";

export default function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [sourcePath, setSourcePath] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchHits, setSearchHits] = useState<SearchHit[]>([]);
  const [readerContext, setReaderContext] = useState<ReaderContext | null>(null);
  const [message, setMessage] = useState("");

  async function refreshPapers() {
    const response = await listPapers();
    setPapers(response.papers);
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const health = await getHealth();
        if (!active) return;
        setBackendStatus(health.status);
        await refreshPapers();
      } catch (error) {
        if (!active) return;
        setBackendStatus("offline");
        setMessage(error instanceof Error ? error.message : "Backend unavailable");
      }
    }

    load();
    return () => {
      active = false;
    };
  }, []);

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    try {
      await importPdf(sourcePath);
      setSourcePath("");
      setMessage("PDF imported");
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Import failed");
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = searchQuery.trim();
    setMessage("");
    if (!query) {
      setSearchHits([]);
      return;
    }

    try {
      const response = await searchLocal(query);
      setSearchHits(response.hits);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed");
    }
  }

  async function openPaper(paper: Paper) {
    setMessage("");
    try {
      const context = await getReaderContext(paper.id);
      setReaderContext(context);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not open paper");
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <h1>Knowledge Agent</h1>
        <p className="status">Backend: {backendStatus}</p>

        <form className="panel-form" onSubmit={handleImport}>
          <label htmlFor="source-path">PDF source path</label>
          <div className="form-row">
            <input
              id="source-path"
              value={sourcePath}
              onChange={(event) => setSourcePath(event.target.value)}
              placeholder="F:\\papers\\example.pdf"
            />
            <button type="submit" disabled={sourcePath.trim().length === 0}>
              Import PDF
            </button>
          </div>
        </form>

        <form className="panel-form" onSubmit={handleSearch}>
          <label htmlFor="search-query">Search library</label>
          <div className="form-row">
            <input
              id="search-query"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="retrieval, DOI, title"
            />
            <button type="submit" disabled={searchQuery.trim().length === 0}>
              Search
            </button>
          </div>
        </form>

        {message ? <p className="message">{message}</p> : null}

        <section className="library-section" aria-labelledby="library-heading">
          <h2 id="library-heading">Library</h2>
          <div className="paper-list">
            {papers.length === 0 ? (
              <p className="empty">No papers imported yet.</p>
            ) : (
              papers.map((paper) => (
                <button
                  className="paper-row"
                  key={paper.id}
                  onClick={() => openPaper(paper)}
                  type="button"
                  aria-label={`Open ${paper.title}`}
                >
                  <span className="paper-title">{paper.title}</span>
                  <span className="paper-meta">{paper.doi ?? "No DOI"}</span>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="library-section" aria-labelledby="search-heading">
          <h2 id="search-heading">Search results</h2>
          <div className="search-list">
            {searchHits.length === 0 ? (
              <p className="empty">No search hits.</p>
            ) : (
              searchHits.map((hit) => (
                <button
                  className="search-hit"
                  key={hit.chunk_id}
                  onClick={() => openPaper({ id: hit.paper_id, title: hit.title, year: hit.year, doi: hit.doi, created_at: "" })}
                  type="button"
                  aria-label={`Open ${hit.title} page ${hit.page_number}`}
                >
                  <span className="paper-title">{hit.title}</span>
                  <span className="page-label">Page {hit.page_number}</span>
                  <span className="snippet">{hit.snippet}</span>
                </button>
              ))
            )}
          </div>
        </section>
      </aside>

      <section className="reader-pane">
        <header className="toolbar">
          <h2>{readerContext?.paper.title ?? "Reader"}</h2>
        </header>

        <div className="paper-list">
          {readerContext === null ? (
            <p className="empty">No paper open.</p>
          ) : readerContext.pages.length === 0 ? (
            <p className="empty">No extracted text available.</p>
          ) : (
            readerContext.pages.map((page) => (
              <article className="reader-page" key={page.page_number}>
                <h3>Page {page.page_number}</h3>
                <p>{page.text}</p>
              </article>
            ))
          )}
        </div>
      </section>

      <aside className="assistant-panel">
        <h2>Assistant</h2>
        <p className="context-status">
          {readerContext
            ? `Context: ${readerContext.paper.title} - ${readerContext.document.parse_status}`
            : "Context: none"}
        </p>
      </aside>
    </main>
  );
}

import { FormEvent, useEffect, useState } from "react";

import {
  AskPaperQuestionResponse,
  askPaperQuestion,
  exportBibliography,
  getHealth,
  getProviderSettings,
  getReaderContext,
  importBibliography,
  importPdf,
  listPapers,
  Paper,
  ProviderSettings,
  ReaderContext,
  saveProviderSettings,
  SearchHit,
  searchLocal,
} from "./api";
import "./styles.css";

export default function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [sourcePath, setSourcePath] = useState("");
  const [bibliographyPath, setBibliographyPath] = useState("");
  const [bibliographyFormat, setBibliographyFormat] = useState("auto");
  const [exportPreview, setExportPreview] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchHits, setSearchHits] = useState<SearchHit[]>([]);
  const [readerContext, setReaderContext] = useState<ReaderContext | null>(null);
  const [providerSettings, setProviderSettings] = useState<ProviderSettings | null>(null);
  const [provider, setProvider] = useState("none");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [outboundContextPolicy, setOutboundContextPolicy] = useState("snippets_only");
  const [question, setQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AskPaperQuestionResponse | null>(null);
  const [message, setMessage] = useState("");

  async function refreshPapers() {
    const response = await listPapers();
    setPapers(response.papers);
  }

  function applyProviderSettings(settings: ProviderSettings) {
    setProviderSettings(settings);
    setProvider(settings.provider);
    setBaseUrl(settings.base_url ?? "");
    setModel(settings.model ?? "");
    setOutboundContextPolicy(settings.outbound_context_policy);
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const health = await getHealth();
        if (!active) return;
        setBackendStatus(health.status);
        await refreshPapers();
        const settings = await getProviderSettings();
        if (!active) return;
        applyProviderSettings(settings);
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

  async function handleBibliographyImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    try {
      const response = await importBibliography(bibliographyPath, bibliographyFormat);
      setBibliographyPath("");
      setMessage(
        `Bibliography imported: ${response.imported_count} new, ${response.updated_count} updated`,
      );
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Bibliography import failed");
    }
  }

  async function handleBibliographyExport(format: "bibtex" | "ris") {
    setMessage("");
    try {
      const response = await exportBibliography(format);
      setExportPreview(response.content);
      setMessage(`Exported ${response.format}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Bibliography export failed");
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
      setAssistantAnswer(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not open paper");
    }
  }

  async function handleSaveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    try {
      const saved = await saveProviderSettings({
        provider,
        base_url: emptyToNull(baseUrl),
        model: emptyToNull(model),
        api_key: emptyToNull(apiKey),
        outbound_context_policy: outboundContextPolicy,
      });
      setApiKey("");
      applyProviderSettings(saved);
      setMessage("Provider settings saved");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save provider settings");
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!readerContext) return;
    setMessage("");
    try {
      const response = await askPaperQuestion(readerContext.paper.id, question);
      setAssistantAnswer(response);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Ask failed");
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

        <form className="panel-form bibliography-form" onSubmit={handleBibliographyImport}>
          <label htmlFor="bibliography-path">Bibliography source path</label>
          <input
            id="bibliography-path"
            value={bibliographyPath}
            onChange={(event) => setBibliographyPath(event.target.value)}
            placeholder="F:\\papers\\library.bib"
          />

          <label htmlFor="bibliography-format">Bibliography format</label>
          <div className="form-row">
            <select
              id="bibliography-format"
              value={bibliographyFormat}
              onChange={(event) => setBibliographyFormat(event.target.value)}
            >
              <option value="auto">Auto</option>
              <option value="bibtex">BibTeX</option>
              <option value="ris">RIS</option>
            </select>
            <button type="submit" disabled={bibliographyPath.trim().length === 0}>
              Import bibliography
            </button>
          </div>

          <div className="export-actions">
            <button type="button" onClick={() => handleBibliographyExport("bibtex")}>
              Export BibTeX
            </button>
            <button type="button" onClick={() => handleBibliographyExport("ris")}>
              Export RIS
            </button>
          </div>

          <label htmlFor="bibliography-export-preview">Bibliography export preview</label>
          <textarea
            id="bibliography-export-preview"
            value={exportPreview}
            onChange={(event) => setExportPreview(event.target.value)}
            rows={7}
          />
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
                  <span className="paper-meta">{paperMetadata(paper)}</span>
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
                  onClick={() => openPaper(paperFromSearchHit(hit))}
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

        <section className="assistant-section" aria-labelledby="provider-heading">
          <h3 id="provider-heading">Model settings</h3>
          <p className="context-status">Provider: {providerSettings?.provider ?? "loading"}</p>
          <p className="context-status">
            {providerSettings?.api_key_configured ? "API key configured" : "API key not configured"}
          </p>
          <form className="settings-form" onSubmit={handleSaveSettings}>
            <label htmlFor="provider">Provider</label>
            <select
              id="provider"
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
            >
              <option value="none">None</option>
              <option value="openai_compatible">OpenAI-compatible</option>
              <option value="ollama">Ollama</option>
            </select>

            <label htmlFor="base-url">Base URL</label>
            <input
              id="base-url"
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder="https://api.example.com/v1"
            />

            <label htmlFor="model">Model</label>
            <input
              id="model"
              value={model}
              onChange={(event) => setModel(event.target.value)}
              placeholder="gpt-4.1-mini"
            />

            <label htmlFor="api-key">API key</label>
            <input
              id="api-key"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="Stored locally"
              type="password"
            />

            <label htmlFor="outbound-policy">Outbound policy</label>
            <select
              id="outbound-policy"
              value={outboundContextPolicy}
              onChange={(event) => setOutboundContextPolicy(event.target.value)}
            >
              <option value="snippets_only">Snippets only</option>
              <option value="local_only">Local only</option>
            </select>

            <button type="submit">Save settings</button>
          </form>
        </section>

        <section className="assistant-section" aria-labelledby="ask-heading">
          <h3 id="ask-heading">Ask</h3>
          <form className="settings-form" onSubmit={handleAsk}>
            <label htmlFor="question">Question</label>
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={4}
            />
            <button type="submit" disabled={!readerContext || question.trim().length === 0}>
              Ask
            </button>
          </form>

          {assistantAnswer ? (
            <article className="answer-block">
              <p>{assistantAnswer.answer}</p>
              <div className="citation-list">
                {assistantAnswer.citations.map((citation) => (
                  <div className="citation" key={citation.chunk_id}>
                    <strong>Citation Page {citation.page_number}</strong>
                    <p>{citation.snippet}</p>
                  </div>
                ))}
              </div>
            </article>
          ) : null}
        </section>
      </aside>
    </main>
  );
}

function emptyToNull(value: string): string | null {
  const stripped = value.trim();
  return stripped.length > 0 ? stripped : null;
}

function paperMetadata(paper: Paper): string {
  const parts = [paper.authors, paper.year?.toString()].filter(Boolean);
  if (parts.length > 0) return parts.join(" · ");
  return paper.doi ?? "No DOI";
}

function paperFromSearchHit(hit: SearchHit): Paper {
  return {
    id: hit.paper_id,
    title: hit.title,
    authors: null,
    year: hit.year,
    doi: hit.doi,
    venue: null,
    abstract: null,
    citation_key: null,
    arxiv_id: null,
    entry_type: null,
    created_at: "",
  };
}

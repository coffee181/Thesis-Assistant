import { FormEvent, useEffect, useState } from "react";

import {
  AskPaperQuestionResponse,
  askPaperQuestion,
  askSelectedText,
  createHighlight,
  createNote,
  downloadOpenPdf,
  exportBibliography,
  getHealth,
  getLibrary,
  getProviderSettings,
  getReaderContext,
  Highlight,
  importBibliography,
  importFolder,
  importPendingDownload,
  importPdf,
  listHighlights,
  listNotes,
  listPapers,
  LibraryStatus,
  Note,
  Paper,
  paperPdfUrl,
  ProviderSettings,
  ReaderContext,
  SearchResultRecord,
  saveProviderSettings,
  SearchHit,
  searchExternal,
  searchLocal,
  selectLibrary,
  SelectedTextAction,
} from "./api";
import "./styles.css";

export default function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [libraryStatus, setLibraryStatus] = useState<LibraryStatus | null>(null);
  const [libraryPath, setLibraryPath] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [sourcePath, setSourcePath] = useState("");
  const [bibliographyPath, setBibliographyPath] = useState("");
  const [bibliographyFormat, setBibliographyFormat] = useState("auto");
  const [exportPreview, setExportPreview] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchHits, setSearchHits] = useState<SearchHit[]>([]);
  const [externalQuery, setExternalQuery] = useState("");
  const [externalResults, setExternalResults] = useState<SearchResultRecord[]>([]);
  const [pendingDownloads, setPendingDownloads] = useState<Record<number, string>>({});
  const [readerContext, setReaderContext] = useState<ReaderContext | null>(null);
  const [providerSettings, setProviderSettings] = useState<ProviderSettings | null>(null);
  const [provider, setProvider] = useState("none");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [outboundContextPolicy, setOutboundContextPolicy] = useState("snippets_only");
  const [question, setQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AskPaperQuestionResponse | null>(null);
  const [selectedText, setSelectedText] = useState("");
  const [selectedPageNumber, setSelectedPageNumber] = useState<number | null>(null);
  const [selectedSourceSpan, setSelectedSourceSpan] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [selectionBusy, setSelectionBusy] = useState(false);
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
        const library = await getLibrary();
        if (!active) return;
        setLibraryStatus(library);
        setLibraryPath(library.library_dir);
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

  async function handleSelectLibrary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selectedPath = libraryPath.trim();
    if (!selectedPath) return;
    setMessage("");
    try {
      const library = await selectLibrary(selectedPath);
      setLibraryStatus(library);
      setLibraryPath(library.library_dir);
      setPapers([]);
      setReaderContext(null);
      clearSelection();
      setNotes([]);
      setHighlights([]);
      setAssistantAnswer(null);
      setPendingDownloads({});
      setSearchHits([]);
      setExternalResults([]);
      setMessage("Library selected");
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Library selection failed");
    }
  }

  async function handleFolderImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const sourceDir = folderPath.trim();
    if (!sourceDir) return;
    setMessage("");
    try {
      const response = await importFolder(sourceDir);
      setFolderPath("");
      setMessage(
        `Folder imported: ${response.imported_count} imported, ${response.skipped_count} skipped, ${response.failed_count} failed`,
      );
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Folder import failed");
    }
  }

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

  async function handleExternalSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = externalQuery.trim();
    setMessage("");
    if (!query) {
      setExternalResults([]);
      return;
    }

    try {
      const response = await searchExternal(query);
      setExternalResults(response.results);
      setPendingDownloads({});
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "External search failed");
    }
  }

  async function handleDownloadOpenPdf(result: SearchResultRecord) {
    setMessage("");
    try {
      const response = await downloadOpenPdf(result.id);
      setPendingDownloads((current) => ({
        ...current,
        [result.id]: response.pending_path,
      }));
      setMessage("Open PDF downloaded");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Download failed");
    }
  }

  async function handleConfirmPendingImport(result: SearchResultRecord) {
    const pendingPath = pendingDownloads[result.id];
    if (!pendingPath) return;
    setMessage("");
    try {
      await importPendingDownload(result.id, pendingPath);
      setPendingDownloads((current) => {
        const next = { ...current };
        delete next[result.id];
        return next;
      });
      setMessage("Downloaded paper imported");
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Pending import failed");
    }
  }

  function clearSelection() {
    setSelectedText("");
    setSelectedPageNumber(null);
    setSelectedSourceSpan("");
  }

  async function openPaper(paper: Paper) {
    setMessage("");
    clearSelection();
    setNotes([]);
    setHighlights([]);
    setAssistantAnswer(null);
    try {
      const [context, notesResponse, highlightsResponse] = await Promise.all([
        getReaderContext(paper.id),
        listNotes(paper.id),
        listHighlights(paper.id),
      ]);
      setReaderContext(context);
      setNotes(notesResponse.notes);
      setHighlights(highlightsResponse.highlights);
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

  function handleReaderPageMouseUp(pageNumber: number) {
    const selection = (window.getSelection?.()?.toString() ?? "").trim();
    if (!selection) return;
    setSelectedText(selection);
    setSelectedPageNumber(pageNumber);
    setSelectedSourceSpan(`page:${pageNumber}:selection`);
  }

  async function handleSelectionAction(action: SelectedTextAction) {
    if (!readerContext || !selectedText.trim() || selectedPageNumber === null) return;
    setMessage("");
    setSelectionBusy(true);
    try {
      const response = await askSelectedText(readerContext.paper.id, {
        selected_text: selectedText,
        page_number: selectedPageNumber,
        source_span: selectedSourceSpan,
        action,
      });
      setAssistantAnswer(response);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Selection ask failed");
    } finally {
      setSelectionBusy(false);
    }
  }

  async function handleHighlightSelection() {
    if (!readerContext || !selectedText.trim() || selectedPageNumber === null) return;
    setMessage("");
    setSelectionBusy(true);
    try {
      const highlight = await createHighlight({
        paper_id: readerContext.paper.id,
        page_number: selectedPageNumber,
        source_span: selectedSourceSpan,
        selected_text: selectedText,
        color: "yellow",
        note_id: null,
      });
      setHighlights((current) => [...current, highlight]);
      setMessage("Highlight saved");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Highlight save failed");
    } finally {
      setSelectionBusy(false);
    }
  }

  async function handleSaveAnswerAsNote() {
    if (!readerContext || !assistantAnswer) return;
    const citation = assistantAnswer.citations[0];
    setMessage("");
    try {
      const note = await createNote({
        paper_id: readerContext.paper.id,
        body: assistantAnswer.answer,
        page_number: citation?.page_number ?? selectedPageNumber,
        source_span: citation?.source_span ?? (selectedSourceSpan || null),
        selected_text: citation?.snippet ?? (selectedText || null),
        note_type: "assistant_answer",
        qna_id: assistantAnswer.qna_id,
      });
      setNotes((current) => [note, ...current]);
      setMessage("Note saved");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Note save failed");
    }
  }

  const selectionReady =
    readerContext !== null && selectedText.trim().length > 0 && selectedPageNumber !== null;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <h1>Knowledge Agent</h1>
        <p className="status">Backend: {backendStatus}</p>

        <form className="panel-form library-control" onSubmit={handleSelectLibrary}>
          <p className="library-path">
            Library: {libraryStatus?.library_dir ?? "loading"}
          </p>
          <label htmlFor="library-path">Library location</label>
          <div className="form-row">
            <input
              id="library-path"
              value={libraryPath}
              onChange={(event) => setLibraryPath(event.target.value)}
              placeholder="F:\\KnowledgeAgentLibrary"
            />
            <button type="submit" disabled={libraryPath.trim().length === 0}>
              Select library
            </button>
          </div>
        </form>

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

        <form className="panel-form" onSubmit={handleFolderImport}>
          <label htmlFor="folder-path">PDF folder path</label>
          <div className="form-row">
            <input
              id="folder-path"
              value={folderPath}
              onChange={(event) => setFolderPath(event.target.value)}
              placeholder="F:\\papers"
            />
            <button type="submit" disabled={folderPath.trim().length === 0}>
              Import folder
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

        <form className="panel-form" onSubmit={handleExternalSearch}>
          <label htmlFor="external-query">External search</label>
          <div className="form-row">
            <input
              id="external-query"
              value={externalQuery}
              onChange={(event) => setExternalQuery(event.target.value)}
              placeholder="keyword, DOI, title, arXiv"
            />
            <button type="submit" disabled={externalQuery.trim().length === 0}>
              Search external
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

        <section className="library-section" aria-labelledby="external-heading">
          <h2 id="external-heading">External discovery</h2>
          <div className="search-list">
            {externalResults.length === 0 ? (
              <p className="empty">No external results.</p>
            ) : (
              externalResults.map((result) => (
                <article className="search-hit discovery-result" key={result.id}>
                  <span className="paper-title">{result.title}</span>
                  <span className="paper-meta">{resultMetadata(result)}</span>
                  <span className="source-label">{result.source}</span>
                  {result.doi ? <span className="snippet">DOI {result.doi}</span> : null}
                  {result.arxiv_id ? <span className="snippet">arXiv {result.arxiv_id}</span> : null}
                  <span className={result.pdf_url ? "availability open" : "availability closed"}>
                    {result.pdf_url ? "Open PDF available" : "Needs access"}
                  </span>
                  <div className="result-actions">
                    {pendingDownloads[result.id] ? (
                      <button type="button" onClick={() => handleConfirmPendingImport(result)}>
                        Confirm import
                      </button>
                    ) : result.pdf_url ? (
                      <button type="button" onClick={() => handleDownloadOpenPdf(result)}>
                        Download PDF
                      </button>
                    ) : null}
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      </aside>

      <section className="reader-pane">
        <header className="toolbar">
          <h2>{readerContext?.paper.title ?? "Reader"}</h2>
        </header>

        {readerContext === null ? (
          <p className="empty">No paper open.</p>
        ) : (
          <div className="reader-content">
            <iframe
              className="pdf-preview"
              src={paperPdfUrl(readerContext.paper.id)}
              title={`PDF reader for ${readerContext.paper.title}`}
            />
            <section className="extracted-text-layer" aria-label="Extracted text">
              {readerContext.pages.length === 0 ? (
                <p className="empty">No extracted text available.</p>
              ) : (
                readerContext.pages.map((page) => (
                  <article
                    className="reader-page"
                    key={page.page_number}
                    onMouseUp={() => handleReaderPageMouseUp(page.page_number)}
                  >
                    <h3>Page {page.page_number}</h3>
                    <p>{page.text}</p>
                  </article>
                ))
              )}
            </section>
          </div>
        )}
      </section>

      <aside className="assistant-panel">
        <h2>Assistant</h2>
        <p className="context-status">
          {readerContext
            ? `Context: ${readerContext.paper.title} - ${readerContext.document.parse_status}`
            : "Context: none"}
        </p>

        <section className="assistant-section" aria-labelledby="selection-heading">
          <h3 id="selection-heading">Selection</h3>
          {selectedText ? (
            <div className="selection-block">
              <strong>Selected text</strong>
              <p>{selectedText}</p>
              <span>Page {selectedPageNumber}</span>
            </div>
          ) : (
            <p className="empty">No selection.</p>
          )}
          <div className="selection-actions">
            <button
              type="button"
              disabled={!selectionReady || selectionBusy}
              onClick={() => handleSelectionAction("translate")}
            >
              Translate selection
            </button>
            <button
              type="button"
              disabled={!selectionReady || selectionBusy}
              onClick={() => handleSelectionAction("explain")}
            >
              Explain selection
            </button>
            <button
              type="button"
              disabled={!selectionReady || selectionBusy}
              onClick={handleHighlightSelection}
            >
              Highlight selection
            </button>
          </div>
        </section>

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
              <div className="answer-actions">
                <button type="button" onClick={handleSaveAnswerAsNote}>
                  Save answer as note
                </button>
              </div>
              <div className="citation-list">
                {assistantAnswer.citations.map((citation) => (
                  <div
                    className="citation"
                    key={`${citation.chunk_id ?? "selection"}-${citation.page_number}-${citation.source_span}`}
                  >
                    <strong>Citation Page {citation.page_number}</strong>
                    <p>{citation.snippet}</p>
                  </div>
                ))}
              </div>
            </article>
          ) : null}
        </section>

        <section className="assistant-section" aria-labelledby="paper-notes-heading">
          <h3 id="paper-notes-heading">Paper notes</h3>
          <div className="note-list">
            {notes.length === 0 ? (
              <p className="empty">No notes.</p>
            ) : (
              notes.map((note) => (
                <article className="note-item" key={note.id}>
                  <strong>
                    Note{note.page_number === null ? "" : ` Page ${note.page_number}`}
                  </strong>
                  <p>{note.body}</p>
                  {note.selected_text ? <span>{note.selected_text}</span> : null}
                </article>
              ))
            )}
          </div>
          <div className="note-list">
            {highlights.length === 0 ? (
              <p className="empty">No highlights.</p>
            ) : (
              highlights.map((highlight) => (
                <article className="note-item highlight-item" key={highlight.id}>
                  <strong>Highlight Page {highlight.page_number}</strong>
                  <p>{highlight.selected_text}</p>
                </article>
              ))
            )}
          </div>
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

function resultMetadata(result: SearchResultRecord): string {
  const parts = [result.authors, result.year?.toString()].filter(Boolean);
  if (parts.length > 0) return parts.join(" · ");
  return result.venue ?? result.doi ?? "No metadata";
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

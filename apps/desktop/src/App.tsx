import { FormEvent, useEffect, useState } from "react";

import {
  addPaperTag,
  AskPaperQuestionResponse,
  askPaperQuestion,
  askPaperQuestionStream,
  AssistantStreamEvent,
  askSelectedText,
  createHighlight,
  createNote,
  downloadOpenPdf,
  exportBibliography,
  getHealthWithRetry,
  getLibrary,
  getProviderSettings,
  getReaderContext,
  Highlight,
  importBibliography,
  importFolder,
  importPendingDownload,
  importPdf,
  Job,
  listHighlights,
  listJobs,
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
  removePaperTag,
  retryJob,
  setPaperFavorite,
} from "./api";
import { AssistantRail } from "./components/AssistantRail";
import { LibraryRail } from "./components/LibraryRail";
import { ReaderWorkspace } from "./components/ReaderWorkspace";
import { TopBar } from "./components/TopBar";
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
  const [activeReaderPage, setActiveReaderPage] = useState<number | null>(null);
  const [providerSettings, setProviderSettings] = useState<ProviderSettings | null>(null);
  const [provider, setProvider] = useState("none");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [proxyUrl, setProxyUrl] = useState("");
  const [outboundContextPolicy, setOutboundContextPolicy] = useState("snippets_only");
  const [question, setQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AskPaperQuestionResponse | null>(null);
  const [assistantProgress, setAssistantProgress] = useState("");
  const [selectedText, setSelectedText] = useState("");
  const [selectedPageNumber, setSelectedPageNumber] = useState<number | null>(null);
  const [selectedSourceSpan, setSelectedSourceSpan] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectionBusy, setSelectionBusy] = useState(false);
  const [favoriteFilter, setFavoriteFilter] = useState(false);
  const [tagFilter, setTagFilter] = useState("");
  const [tagInputs, setTagInputs] = useState<Record<number, string>>({});
  const [searchPerformed, setSearchPerformed] = useState(false);
  const [openSurface, setOpenSurface] = useState<"import" | "discover" | "jobs" | "settings" | null>(null);
  const [message, setMessage] = useState("");

  async function refreshPapers(filters = { favorite: favoriteFilter, tag: tagFilter }) {
    const response = await listPapers(filters);
    setPapers(response.papers);
  }

  async function refreshJobs() {
    const response = await listJobs();
    setJobs(response.jobs);
  }

  function applyProviderSettings(settings: ProviderSettings) {
    setProviderSettings(settings);
    setProvider(settings.provider);
    setBaseUrl(settings.base_url ?? "");
    setModel(settings.model ?? "");
    setProxyUrl(settings.proxy_url ?? "");
    setOutboundContextPolicy(settings.outbound_context_policy);
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const health = await getHealthWithRetry();
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
        try {
          await refreshJobs();
        } catch {
          if (!active) return;
          setJobs([]);
        }
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
      setActiveReaderPage(null);
      clearSelection();
      setNotes([]);
      setHighlights([]);
      setAssistantAnswer(null);
      setAssistantProgress("");
      setPendingDownloads({});
      setSearchHits([]);
      setSearchPerformed(false);
      setExternalResults([]);
      setJobs([]);
      setMessage("Library selected");
      await refreshPapers();
      try {
        await refreshJobs();
      } catch {
        setJobs([]);
      }
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
      const job = await importFolder(sourceDir);
      setFolderPath("");
      setJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
      setMessage("Folder import queued");
      await refreshJobs();
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
    await runLocalSearch();
  }

  async function runLocalSearch() {
    const query = searchQuery.trim();
    setMessage("");
    if (!query) {
      setSearchHits([]);
      setSearchPerformed(false);
      return;
    }

    try {
      const response = await searchLocal(query);
      setSearchHits(response.hits);
      setSearchPerformed(true);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed");
    }
  }

  async function handleApplyLibraryFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await applyLibraryFilters();
  }

  async function applyLibraryFilters() {
    setMessage("");
    try {
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not filter library");
    }
  }

  async function handleToggleFavorite(paper: Paper) {
    setMessage("");
    try {
      await setPaperFavorite(paper.id, !paper.favorite);
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Favorite update failed");
    }
  }

  async function handleAddTag(event: FormEvent<HTMLFormElement>, paper: Paper) {
    event.preventDefault();
    const tagName = (tagInputs[paper.id] ?? "").trim();
    if (!tagName) return;
    setMessage("");
    try {
      await addPaperTag(paper.id, tagName);
      setTagInputs((current) => ({ ...current, [paper.id]: "" }));
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Tag update failed");
    }
  }

  async function handleRemoveTag(paper: Paper, tagName: string) {
    setMessage("");
    try {
      await removePaperTag(paper.id, tagName);
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Tag removal failed");
    }
  }

  async function handleRetryJob(job: Job) {
    setMessage("");
    try {
      const retry = await retryJob(job.id);
      setJobs((current) => [retry, ...current.filter((item) => item.id !== retry.id)]);
      setMessage("Job retry queued");
      await refreshJobs();
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Job retry failed");
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
    setAssistantProgress("");
    setActiveReaderPage(null);
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
        proxy_url: emptyToNull(proxyUrl),
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
    setAssistantAnswer(null);
    setAssistantProgress("Starting assistant...");
    try {
      const response = await askPaperQuestionStream(
        readerContext.paper.id,
        question,
        handleAssistantStreamEvent,
      );
      setAssistantAnswer(response);
    } catch (error) {
      try {
        const response = await askPaperQuestion(readerContext.paper.id, question);
        setAssistantAnswer(response);
      } catch (fallbackError) {
        setMessage(fallbackError instanceof Error ? fallbackError.message : "Ask failed");
      }
    } finally {
      setAssistantProgress("");
    }
  }

  function handleAssistantStreamEvent(streamEvent: AssistantStreamEvent) {
    if (streamEvent.event === "started") {
      setAssistantProgress("Starting assistant...");
    } else if (streamEvent.event === "context") {
      setAssistantProgress("Gathering cited context...");
    } else if (streamEvent.event === "final") {
      setAssistantAnswer(streamEvent.data);
    }
  }

  function handleReaderPageMouseUp(pageNumber: number) {
    const selection = (window.getSelection?.()?.toString() ?? "").trim();
    if (!selection) return;
    setSelectedText(selection);
    setSelectedPageNumber(pageNumber);
    setSelectedSourceSpan(`page:${pageNumber}:selection`);
  }

  function pdfPreviewUrl(): string {
    if (!readerContext) return "";
    const baseUrl = paperPdfUrl(readerContext.paper.id);
    return activeReaderPage === null ? baseUrl : `${baseUrl}#page=${activeReaderPage}`;
  }

  function openReaderPage(pageNumber: number) {
    setActiveReaderPage(pageNumber);
    const scrollPageIntoView = () => {
      document
        .getElementById(`reader-page-${pageNumber}`)
        ?.scrollIntoView?.({ block: "start" });
    };
    if (typeof window.requestAnimationFrame === "function") {
      window.requestAnimationFrame(scrollPageIntoView);
    } else {
      scrollPageIntoView();
    }
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

  async function handleSaveSelectionAsNote() {
    if (!readerContext || !selectedText.trim() || selectedPageNumber === null) return;
    setMessage("");
    setSelectionBusy(true);
    try {
      const note = await createNote({
        paper_id: readerContext.paper.id,
        body: selectedText,
        page_number: selectedPageNumber,
        source_span: selectedSourceSpan,
        selected_text: selectedText,
        note_type: "selection",
        qna_id: null,
      });
      setNotes((current) => [note, ...current]);
      setMessage("Selection note saved");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Selection note save failed");
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
  const recentJobs = Array.isArray(jobs) ? jobs : [];

  return (
    <main className="app-shell">
      <TopBar
        backendStatus={backendStatus}
        jobCount={recentJobs.filter((job) => job.status === "queued" || job.status === "running").length}
        paperCount={libraryStatus?.paper_count ?? papers.length}
        searchQuery={searchQuery}
        onOpenDiscover={() => setOpenSurface("discover")}
        onOpenImport={() => setOpenSurface("import")}
        onOpenJobs={() => setOpenSurface("jobs")}
        onOpenSettings={() => setOpenSurface("settings")}
        onSearchQueryChange={setSearchQuery}
        onSearchSubmit={runLocalSearch}
      />

      <div className="workspace-grid">
        <LibraryRail
          activePaperId={readerContext?.paper.id ?? null}
          favoriteFilter={favoriteFilter}
          paperFromSearchHit={paperFromSearchHit}
          paperMetadata={paperMetadata}
          papers={papers}
          searchHits={searchHits}
          searchPerformed={searchPerformed}
          tagFilter={tagFilter}
          tagInputs={tagInputs}
          onAddTag={handleAddTag}
          onApplyFilters={applyLibraryFilters}
          onFavoriteFilterChange={setFavoriteFilter}
          onOpenPaper={openPaper}
          onRemoveTag={handleRemoveTag}
          onTagFilterChange={setTagFilter}
          onTagInputChange={(paperId, value) =>
            setTagInputs((current) => ({
              ...current,
              [paperId]: value,
            }))
          }
          onToggleFavorite={handleToggleFavorite}
        />

        <ReaderWorkspace
          activeReaderPage={activeReaderPage}
          pdfPreviewUrl={pdfPreviewUrl()}
          readerContext={readerContext}
          selectedPageNumber={selectedPageNumber}
          selectedText={selectedText}
          selectionBusy={selectionBusy}
          onHighlightSelection={handleHighlightSelection}
          onOpenDiscover={() => setOpenSurface("discover")}
          onOpenImport={() => setOpenSurface("import")}
          onReaderPageMouseUp={handleReaderPageMouseUp}
          onSaveSelectionAsNote={handleSaveSelectionAsNote}
          onSelectionAction={handleSelectionAction}
        />

        <AssistantRail
          assistantAnswer={assistantAnswer}
          assistantProgress={assistantProgress}
          highlights={highlights}
          notes={notes}
          providerSettings={providerSettings}
          question={question}
          readerContext={readerContext}
          onAsk={handleAsk}
          onOpenReaderPage={openReaderPage}
          onOpenSettings={() => setOpenSurface("settings")}
          onQuestionChange={setQuestion}
          onSaveAnswerAsNote={handleSaveAnswerAsNote}
        />
      </div>

      {message ? <p className="toast-status">{message}</p> : null}
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
    favorite: false,
    tags: [],
    created_at: "",
  };
}

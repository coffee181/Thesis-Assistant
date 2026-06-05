import type { ReaderContext } from "../api";

type ReaderWorkspaceProps = {
  readerContext: ReaderContext | null;
  activeReaderPage: number | null;
  selectedText: string;
  selectedPageNumber: number | null;
  selectionBusy: boolean;
  pdfPreviewUrl: string;
  onOpenImport: () => void;
  onOpenDiscover: () => void;
  onReaderPageMouseUp: (pageNumber: number) => void;
  onSelectionAction: (action: "translate" | "explain" | "summarize") => void;
  onHighlightSelection: () => void;
  onSaveSelectionAsNote: () => void;
};

export function ReaderWorkspace({
  readerContext,
  activeReaderPage,
  selectedText,
  selectedPageNumber,
  selectionBusy,
  pdfPreviewUrl,
  onOpenImport,
  onOpenDiscover,
  onReaderPageMouseUp,
  onSelectionAction,
  onHighlightSelection,
  onSaveSelectionAsNote,
}: ReaderWorkspaceProps) {
  const selectionReady = selectedText.trim().length > 0 && selectedPageNumber !== null;

  if (!readerContext) {
    return (
      <section aria-label="Reader workspace" className="reader-workspace empty-reader">
        <div className="onboarding-panel">
          <p className="eyebrow">Local research workspace</p>
          <h2>Start your research library</h2>
          <p>Import papers or discover literature to begin reading with cited context.</p>
          <div className="onboarding-actions">
            <button type="button" onClick={onOpenImport}>
              Import papers
            </button>
            <button type="button" onClick={onOpenDiscover}>
              Discover literature
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Reader workspace" className="reader-workspace">
      <header className="reader-header">
        <div>
          <h2>{readerContext.paper.title}</h2>
          <p>
            {readerContext.document.parse_status} -{" "}
            {readerContext.document.page_count ?? readerContext.pages.length} pages
          </p>
        </div>
      </header>

      {selectionReady ? (
        <div aria-label="Selected text actions" className="selection-toolbar" role="toolbar">
          <span>Page {selectedPageNumber}</span>
          <button disabled={selectionBusy} type="button" onClick={() => onSelectionAction("translate")}>
            Translate
          </button>
          <button disabled={selectionBusy} type="button" onClick={() => onSelectionAction("explain")}>
            Explain
          </button>
          <button disabled={selectionBusy} type="button" onClick={onHighlightSelection}>
            Highlight
          </button>
          <button disabled={selectionBusy} type="button" onClick={onSaveSelectionAsNote}>
            Note
          </button>
        </div>
      ) : null}

      <div className="reader-grid">
        <iframe className="pdf-preview" src={pdfPreviewUrl} title={`PDF reader for ${readerContext.paper.title}`} />
        <section aria-label="Extracted text" className="extracted-text-layer">
          {readerContext.pages.map((page) => (
            <article
              aria-current={activeReaderPage === page.page_number ? "page" : undefined}
              aria-label={`Reader page ${page.page_number}`}
              className={activeReaderPage === page.page_number ? "reader-page active" : "reader-page"}
              id={`reader-page-${page.page_number}`}
              key={page.page_number}
              onMouseUp={() => onReaderPageMouseUp(page.page_number)}
            >
              <h3>Page {page.page_number}</h3>
              <p>{page.text}</p>
            </article>
          ))}
        </section>
      </div>
    </section>
  );
}

import { FormEvent } from "react";

import type { SearchResultRecord } from "../api";

type DiscoverDrawerProps = {
  externalQuery: string;
  externalResults: SearchResultRecord[];
  pendingDownloads: Record<number, string>;
  onExternalQueryChange: (value: string) => void;
  onExternalSearch: (event: FormEvent<HTMLFormElement>) => void;
  onDownloadOpenPdf: (result: SearchResultRecord) => void;
  onConfirmPendingImport: (result: SearchResultRecord) => void;
  onClose: () => void;
  resultMetadata: (result: SearchResultRecord) => string;
};

export function DiscoverDrawer({
  externalQuery,
  externalResults,
  pendingDownloads,
  onExternalQueryChange,
  onExternalSearch,
  onDownloadOpenPdf,
  onConfirmPendingImport,
  onClose,
  resultMetadata,
}: DiscoverDrawerProps) {
  return (
    <aside aria-label="Discover literature" className="drawer-panel">
      <header className="drawer-header">
        <div>
          <h2>Discover literature</h2>
          <p>Search external sources and import open PDFs into your local library.</p>
        </div>
        <button aria-label="Close discover drawer" type="button" onClick={onClose}>
          Close
        </button>
      </header>

      <form className="drawer-form" onSubmit={onExternalSearch}>
        <label htmlFor="external-query">External search</label>
        <div className="compact-row">
          <input
            id="external-query"
            placeholder="keyword, DOI, title, arXiv"
            value={externalQuery}
            onChange={(event) => onExternalQueryChange(event.target.value)}
          />
          <button disabled={externalQuery.trim().length === 0} type="submit">
            Search external
          </button>
        </div>
      </form>

      <div className="drawer-list">
        {externalResults.length === 0 ? (
          <p className="empty compact">Search external sources to find papers.</p>
        ) : (
          externalResults.map((result) => (
            <article className="result-card" key={result.id}>
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
                  <button type="button" onClick={() => onConfirmPendingImport(result)}>
                    Confirm import
                  </button>
                ) : result.pdf_url ? (
                  <button type="button" onClick={() => onDownloadOpenPdf(result)}>
                    Download PDF
                  </button>
                ) : null}
              </div>
            </article>
          ))
        )}
      </div>
    </aside>
  );
}

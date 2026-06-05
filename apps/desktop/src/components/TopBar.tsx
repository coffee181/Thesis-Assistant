type TopBarProps = {
  backendStatus: string;
  paperCount: number;
  searchQuery: string;
  jobCount: number;
  onSearchQueryChange: (value: string) => void;
  onSearchSubmit: () => void;
  onOpenImport: () => void;
  onOpenDiscover: () => void;
  onOpenJobs: () => void;
  onOpenSettings: () => void;
};

export function TopBar({
  backendStatus,
  paperCount,
  searchQuery,
  jobCount,
  onSearchQueryChange,
  onSearchSubmit,
  onOpenImport,
  onOpenDiscover,
  onOpenJobs,
  onOpenSettings,
}: TopBarProps) {
  return (
    <header aria-label="Thesis Assistant workspace" className="top-bar">
      <div className="brand-block">
        <h1>Thesis Assistant</h1>
        <div aria-label="Workspace status" className="status-row">
          <span className={backendStatus === "ok" ? "status-pill ready" : "status-pill"}>
            Backend {backendStatus}
          </span>
          <span className="status-pill">{paperCount} papers</span>
        </div>
      </div>

      <form
        aria-label="Global library search"
        className="global-search"
        onSubmit={(event) => {
          event.preventDefault();
          onSearchSubmit();
        }}
      >
        <input
          aria-label="Search library or DOI"
          placeholder="Search library or paste DOI/title/arXiv"
          type="search"
          value={searchQuery}
          onChange={(event) => onSearchQueryChange(event.target.value)}
        />
      </form>

      <div className="top-actions">
        <button type="button" onClick={onOpenImport}>
          Import
        </button>
        <button type="button" onClick={onOpenDiscover}>
          Discover
        </button>
        <button type="button" onClick={onOpenJobs}>
          Jobs{jobCount > 0 ? ` ${jobCount}` : ""}
        </button>
        <button type="button" onClick={onOpenSettings}>
          Settings
        </button>
      </div>
    </header>
  );
}

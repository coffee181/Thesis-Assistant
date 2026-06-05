import { FormEvent } from "react";

import type { Paper, SearchHit } from "../api";

type LibraryRailProps = {
  papers: Paper[];
  activePaperId: number | null;
  favoriteFilter: boolean;
  tagFilter: string;
  tagInputs: Record<number, string>;
  searchHits: SearchHit[];
  searchPerformed: boolean;
  onOpenPaper: (paper: Paper) => void;
  onToggleFavorite: (paper: Paper) => void;
  onFavoriteFilterChange: (value: boolean) => void;
  onTagFilterChange: (value: string) => void;
  onApplyFilters: () => void;
  onTagInputChange: (paperId: number, value: string) => void;
  onAddTag: (event: FormEvent<HTMLFormElement>, paper: Paper) => void;
  onRemoveTag: (paper: Paper, tagName: string) => void;
  paperMetadata: (paper: Paper) => string;
  paperFromSearchHit: (hit: SearchHit) => Paper;
};

export function LibraryRail({
  papers,
  activePaperId,
  favoriteFilter,
  tagFilter,
  tagInputs,
  searchHits,
  searchPerformed,
  onOpenPaper,
  onToggleFavorite,
  onFavoriteFilterChange,
  onTagFilterChange,
  onApplyFilters,
  onTagInputChange,
  onAddTag,
  onRemoveTag,
  paperMetadata,
  paperFromSearchHit,
}: LibraryRailProps) {
  return (
    <nav aria-label="Library" className="library-rail">
      <div className="rail-header">
        <div>
          <h2>Library</h2>
          <p>{papers.length} papers in this view</p>
        </div>
      </div>

      <div aria-label="Library filters" className="segmented-control">
        <button
          className={!favoriteFilter ? "active" : ""}
          onClick={() => onFavoriteFilterChange(false)}
          type="button"
        >
          All
        </button>
        <button
          className={favoriteFilter ? "active" : ""}
          onClick={() => onFavoriteFilterChange(true)}
          type="button"
        >
          Favorites
        </button>
      </div>

      <form
        className="tag-filter-form"
        onSubmit={(event) => {
          event.preventDefault();
          onApplyFilters();
        }}
      >
        <label htmlFor="tag-filter">Tag filter</label>
        <div className="compact-row">
          <input
            id="tag-filter"
            placeholder="reading"
            value={tagFilter}
            onChange={(event) => onTagFilterChange(event.target.value)}
          />
          <button type="submit">Apply</button>
        </div>
      </form>

      <div className="paper-list">
        {papers.length === 0 ? (
          <p className="empty compact">No papers in this library yet.</p>
        ) : (
          papers.map((paper) => (
            <article className={activePaperId === paper.id ? "paper-card active" : "paper-card"} key={paper.id}>
              <button
                aria-label={`Open ${paper.title}`}
                className="paper-open"
                onClick={() => onOpenPaper(paper)}
                type="button"
              >
                <span className="paper-title">{paper.title}</span>
                <span className="paper-meta">{paperMetadata(paper)}</span>
              </button>
              <div className="paper-card-actions">
                <button
                  aria-label={
                    paper.favorite
                      ? `Remove ${paper.title} from favorites`
                      : `Mark ${paper.title} as favorite`
                  }
                  className={paper.favorite ? "chip active" : "chip"}
                  onClick={() => onToggleFavorite(paper)}
                  type="button"
                >
                  {paper.favorite ? "Favorited" : "Favorite"}
                </button>
              </div>
              {paper.tags.length > 0 ? (
                <div aria-label={`Tags for ${paper.title}`} className="tag-list">
                  {paper.tags.map((tag) => (
                    <button
                      aria-label={`Remove tag ${tag} from ${paper.title}`}
                      className="tag-pill"
                      key={tag}
                      onClick={() => onRemoveTag(paper, tag)}
                      type="button"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              ) : null}
              <form className="tag-form" onSubmit={(event) => onAddTag(event, paper)}>
                <input
                  aria-label={`Tag ${paper.title}`}
                  placeholder="Add tag"
                  value={tagInputs[paper.id] ?? ""}
                  onChange={(event) => onTagInputChange(paper.id, event.target.value)}
                />
                <button
                  aria-label={`Add tag to ${paper.title}`}
                  disabled={(tagInputs[paper.id] ?? "").trim().length === 0}
                  type="submit"
                >
                  Add
                </button>
              </form>
            </article>
          ))
        )}
      </div>

      {searchPerformed ? (
        <section aria-labelledby="local-search-heading" className="rail-section">
          <h3 id="local-search-heading">Search results</h3>
          {searchHits.length === 0 ? (
            <p className="empty compact">No local matches.</p>
          ) : (
            <div className="search-list">
              {searchHits.map((hit) =>
                hit.page_number === null || hit.chunk_id === null ? (
                  <article className="search-result-card" key={`metadata-${hit.paper_id}`}>
                    <span className="paper-title">{hit.title}</span>
                    <span className="page-label">Metadata match</span>
                    <span className="snippet">{hit.snippet}</span>
                  </article>
                ) : (
                  <button
                    aria-label={`Open ${hit.title} page ${hit.page_number}`}
                    className="search-result-card"
                    key={hit.chunk_id}
                    onClick={() => onOpenPaper(paperFromSearchHit(hit))}
                    type="button"
                  >
                    <span className="paper-title">{hit.title}</span>
                    <span className="page-label">Page {hit.page_number}</span>
                    <span className="snippet">{hit.snippet}</span>
                  </button>
                ),
              )}
            </div>
          )}
        </section>
      ) : null}
    </nav>
  );
}

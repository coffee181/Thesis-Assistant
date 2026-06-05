import { FormEvent } from "react";

import type { AskPaperQuestionResponse, Highlight, Note, ProviderSettings, ReaderContext } from "../api";

type AssistantRailProps = {
  readerContext: ReaderContext | null;
  providerSettings: ProviderSettings | null;
  question: string;
  assistantProgress: string;
  assistantAnswer: AskPaperQuestionResponse | null;
  notes: Note[];
  highlights: Highlight[];
  onQuestionChange: (value: string) => void;
  onAsk: (event: FormEvent<HTMLFormElement>) => void;
  onOpenSettings: () => void;
  onOpenReaderPage: (pageNumber: number) => void;
  onSaveAnswerAsNote: () => void;
};

export function AssistantRail({
  readerContext,
  providerSettings,
  question,
  assistantProgress,
  assistantAnswer,
  notes,
  highlights,
  onQuestionChange,
  onAsk,
  onOpenSettings,
  onOpenReaderPage,
  onSaveAnswerAsNote,
}: AssistantRailProps) {
  const providerConfigured = providerSettings?.provider !== "none" && providerSettings?.api_key_configured;

  return (
    <aside aria-label="Assistant" className="assistant-rail">
      <header className="assistant-header">
        <h2>Assistant</h2>
        <p>
          {readerContext
            ? `Context: ${readerContext.paper.title} - ${readerContext.document.parse_status}`
            : "Context: no paper open"}
        </p>
      </header>

      {!providerConfigured ? (
        <section className="provider-callout">
          <strong>Model not configured</strong>
          <p>Configure a model provider to ask questions about the current paper.</p>
          <button type="button" onClick={onOpenSettings}>
            Configure model
          </button>
        </section>
      ) : null}

      <section className="assistant-card">
        <h3>Ask current paper</h3>
        <form className="ask-form" onSubmit={onAsk}>
          <label htmlFor="question">Question</label>
          <textarea id="question" rows={4} value={question} onChange={(event) => onQuestionChange(event.target.value)} />
          <button disabled={!readerContext || question.trim().length === 0} type="submit">
            Ask
          </button>
        </form>
        {assistantProgress ? <p className="context-status">{assistantProgress}</p> : null}
      </section>

      {assistantAnswer ? (
        <article className="answer-block">
          <p>{assistantAnswer.answer}</p>
          <div className="answer-actions">
            <button type="button" onClick={onSaveAnswerAsNote}>
              Save answer as note
            </button>
          </div>
          <div className="citation-list">
            {assistantAnswer.citations.map((citation) => (
              <button
                aria-label={`Open citation page ${citation.page_number}`}
                className="citation-card"
                key={`${citation.chunk_id ?? "selection"}-${citation.page_number}-${citation.source_span}`}
                onClick={() => onOpenReaderPage(citation.page_number)}
                type="button"
              >
                <strong>Citation Page {citation.page_number}</strong>
                <p>{citation.snippet}</p>
              </button>
            ))}
          </div>
        </article>
      ) : null}

      <section className="notes-panel">
        <header className="notes-header">
          <h3>Notes and highlights</h3>
        </header>
        {notes.length > 0 ? (
          <div className="note-list">
            {notes.map((note) => (
              <article className="note-item" key={note.id}>
                <strong>Note{note.page_number === null ? "" : ` Page ${note.page_number}`}</strong>
                <p>{note.body}</p>
                {note.selected_text ? <span>{note.selected_text}</span> : null}
              </article>
            ))}
          </div>
        ) : null}
        {highlights.length > 0 ? (
          <div className="note-list">
            {highlights.map((highlight) => (
              <article className="note-item highlight-item" key={highlight.id}>
                <strong>Highlight Page {highlight.page_number}</strong>
                <p>{highlight.selected_text}</p>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </aside>
  );
}

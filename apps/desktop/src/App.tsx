import { FormEvent, useEffect, useState } from "react";

import { getHealth, importPdf, listPapers, Paper } from "./api";
import "./styles.css";

export default function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [sourcePath, setSourcePath] = useState("");
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

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <h1>Knowledge Agent</h1>
        <p className="status">Backend: {backendStatus}</p>
      </aside>

      <section className="content">
        <header className="toolbar">
          <h2>Library</h2>
        </header>

        <form className="import-form" onSubmit={handleImport}>
          <label htmlFor="source-path">PDF source path</label>
          <div className="import-row">
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

        {message ? <p className="message">{message}</p> : null}

        <div className="paper-list">
          {papers.length === 0 ? (
            <p className="empty">No papers imported yet.</p>
          ) : (
            papers.map((paper) => (
              <article className="paper-row" key={paper.id}>
                <h3>{paper.title}</h3>
                <p>{paper.doi ?? "No DOI"}</p>
              </article>
            ))
          )}
        </div>
      </section>
    </main>
  );
}

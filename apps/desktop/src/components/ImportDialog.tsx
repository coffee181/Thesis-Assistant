import { FormEvent } from "react";

export type ImportMode = "pdf" | "folder" | "bibliography";

type ImportDialogProps = {
  mode: ImportMode;
  sourcePath: string;
  folderPath: string;
  bibliographyPath: string;
  bibliographyFormat: string;
  exportPreview: string;
  onModeChange: (mode: ImportMode) => void;
  onSourcePathChange: (value: string) => void;
  onFolderPathChange: (value: string) => void;
  onBibliographyPathChange: (value: string) => void;
  onBibliographyFormatChange: (value: string) => void;
  onExportPreviewChange: (value: string) => void;
  onImportPdf: (event: FormEvent<HTMLFormElement>) => void;
  onImportFolder: (event: FormEvent<HTMLFormElement>) => void;
  onImportBibliography: (event: FormEvent<HTMLFormElement>) => void;
  onExportBibliography: (format: "bibtex" | "ris") => void;
  onClose: () => void;
};

export function ImportDialog({
  mode,
  sourcePath,
  folderPath,
  bibliographyPath,
  bibliographyFormat,
  exportPreview,
  onModeChange,
  onSourcePathChange,
  onFolderPathChange,
  onBibliographyPathChange,
  onBibliographyFormatChange,
  onExportPreviewChange,
  onImportPdf,
  onImportFolder,
  onImportBibliography,
  onExportBibliography,
  onClose,
}: ImportDialogProps) {
  return (
    <div className="modal-backdrop">
      <section aria-label="Import papers" aria-modal="true" className="modal-panel" role="dialog">
        <header className="modal-header">
          <div>
            <h2>Import papers</h2>
            <p>Add PDFs, folders, or bibliography metadata to the active library.</p>
          </div>
          <button aria-label="Close import dialog" type="button" onClick={onClose}>
            Close
          </button>
        </header>

        <div aria-label="Import mode" className="segmented-control import-tabs">
          <button className={mode === "pdf" ? "active" : ""} type="button" onClick={() => onModeChange("pdf")}>
            PDF file
          </button>
          <button
            className={mode === "folder" ? "active" : ""}
            type="button"
            onClick={() => onModeChange("folder")}
          >
            Folder
          </button>
          <button
            className={mode === "bibliography" ? "active" : ""}
            type="button"
            onClick={() => onModeChange("bibliography")}
          >
            Bibliography
          </button>
        </div>

        {mode === "pdf" ? (
          <form className="dialog-form" onSubmit={onImportPdf}>
            <label htmlFor="source-path">PDF source path</label>
            <div className="compact-row">
              <input
                id="source-path"
                placeholder="F:\\papers\\example.pdf"
                value={sourcePath}
                onChange={(event) => onSourcePathChange(event.target.value)}
              />
              <button disabled={sourcePath.trim().length === 0} type="submit">
                Import PDF
              </button>
            </div>
          </form>
        ) : null}

        {mode === "folder" ? (
          <form className="dialog-form" onSubmit={onImportFolder}>
            <label htmlFor="folder-path">PDF folder path</label>
            <div className="compact-row">
              <input
                id="folder-path"
                placeholder="F:\\papers"
                value={folderPath}
                onChange={(event) => onFolderPathChange(event.target.value)}
              />
              <button disabled={folderPath.trim().length === 0} type="submit">
                Import folder
              </button>
            </div>
          </form>
        ) : null}

        {mode === "bibliography" ? (
          <form className="dialog-form" onSubmit={onImportBibliography}>
            <label htmlFor="bibliography-path">Bibliography source path</label>
            <input
              id="bibliography-path"
              placeholder="F:\\papers\\library.bib"
              value={bibliographyPath}
              onChange={(event) => onBibliographyPathChange(event.target.value)}
            />

            <label htmlFor="bibliography-format">Bibliography format</label>
            <div className="compact-row">
              <select
                id="bibliography-format"
                value={bibliographyFormat}
                onChange={(event) => onBibliographyFormatChange(event.target.value)}
              >
                <option value="auto">Auto</option>
                <option value="bibtex">BibTeX</option>
                <option value="ris">RIS</option>
              </select>
              <button disabled={bibliographyPath.trim().length === 0} type="submit">
                Import bibliography
              </button>
            </div>

            <div className="secondary-actions">
              <button type="button" onClick={() => onExportBibliography("bibtex")}>
                Export BibTeX
              </button>
              <button type="button" onClick={() => onExportBibliography("ris")}>
                Export RIS
              </button>
            </div>

            <label htmlFor="bibliography-export-preview">Bibliography export preview</label>
            <textarea
              id="bibliography-export-preview"
              rows={7}
              value={exportPreview}
              onChange={(event) => onExportPreviewChange(event.target.value)}
            />
          </form>
        ) : null}
      </section>
    </div>
  );
}

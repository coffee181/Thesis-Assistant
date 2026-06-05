import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from knowledge_agent.import_service import (
    FolderImportFailure,
    ImportResult,
    import_pdf,
)
from knowledge_agent.models import Job
from knowledge_agent.repositories import JobsRepository


def run_folder_import_job(
    conn: sqlite3.Connection,
    library_root: Path,
    job_id: int,
    source_dir: Path,
) -> Job:
    jobs = JobsRepository(conn)
    source_dir = source_dir.resolve()

    if not source_dir.exists():
        failed = jobs.fail(job_id, f"source folder not found: {source_dir}")
        conn.commit()
        return failed
    if not source_dir.is_dir():
        failed = jobs.fail(job_id, "source path is not a folder")
        conn.commit()
        return failed

    pdf_paths = sorted(
        (path for path in source_dir.rglob("*") if path.suffix.lower() == ".pdf"),
        key=lambda path: path.as_posix().lower(),
    )
    jobs.start(job_id, total_items=len(pdf_paths))
    conn.commit()

    imports: list[ImportResult] = []
    failures: list[FolderImportFailure] = []
    imported_count = 0
    skipped_count = 0

    for pdf_path in pdf_paths:
        try:
            result = import_pdf(conn, library_root, pdf_path)
        except Exception as exc:
            failures.append(
                FolderImportFailure(
                    source_path=str(pdf_path),
                    error=str(exc)[:500],
                )
            )
        else:
            if result.imported:
                imports.append(result)
                imported_count += 1
            else:
                skipped_count += 1

        jobs.update_progress(
            job_id,
            processed_items=imported_count + skipped_count + len(failures),
            succeeded_items=imported_count + skipped_count,
            failed_items=len(failures),
            result_json=_folder_result_json(
                source_dir=source_dir,
                discovered_count=len(pdf_paths),
                imported_count=imported_count,
                skipped_count=skipped_count,
                imports=imports,
                failures=failures,
            ),
        )
        conn.commit()

    completed = jobs.complete(
        job_id,
        processed_items=len(pdf_paths),
        succeeded_items=imported_count + skipped_count,
        failed_items=len(failures),
        result_json=_folder_result_json(
            source_dir=source_dir,
            discovered_count=len(pdf_paths),
            imported_count=imported_count,
            skipped_count=skipped_count,
            imports=imports,
            failures=failures,
        ),
    )
    conn.commit()
    return completed


def _folder_result_json(
    source_dir: Path,
    discovered_count: int,
    imported_count: int,
    skipped_count: int,
    imports: list[ImportResult],
    failures: list[FolderImportFailure],
) -> str:
    return json.dumps(
        {
            "source_path": str(source_dir),
            "discovered_count": discovered_count,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "failed_count": len(failures),
            "imports": [
                {
                    "imported": item.imported,
                    "paper": asdict(item.paper),
                    "document": asdict(item.document),
                }
                for item in imports
            ],
            "failures": [
                {
                    "source_path": failure.source_path,
                    "error": failure.error,
                }
                for failure in failures
            ],
        },
        ensure_ascii=True,
    )

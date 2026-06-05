import type { Job } from "../api";

type JobsDrawerProps = {
  jobs: Job[];
  onRetryJob: (job: Job) => void;
  onClose: () => void;
};

export function JobsDrawer({ jobs, onRetryJob, onClose }: JobsDrawerProps) {
  return (
    <aside aria-label="Jobs" className="drawer-panel">
      <header className="drawer-header">
        <div>
          <h2>Jobs</h2>
          <p>Imports, downloads, and retries for the active library.</p>
        </div>
        <button aria-label="Close jobs drawer" type="button" onClick={onClose}>
          Close
        </button>
      </header>

      <div className="drawer-list">
        {jobs.length === 0 ? (
          <p className="empty compact">No recent jobs.</p>
        ) : (
          jobs.map((job) => (
            <article className="job-card" key={job.id}>
              <strong>
                {job.kind} - {job.status}
              </strong>
              <span className="job-source">{job.source_path}</span>
              <span>
                {job.processed_items} / {job.total_items} processed
              </span>
              <span>
                {job.succeeded_items} succeeded, {job.failed_items} failed
              </span>
              {job.error ? <span className="job-error">{job.error}</span> : null}
              {job.status === "failed" ? (
                <button aria-label={`Retry job ${job.id}`} type="button" onClick={() => onRetryJob(job)}>
                  Retry
                </button>
              ) : null}
            </article>
          ))
        )}
      </div>
    </aside>
  );
}

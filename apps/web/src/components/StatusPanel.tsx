import type { VideoJobStatusResponse } from '@shared-types';

type StatusPanelProps = {
  status: VideoJobStatusResponse;
  successMessage?: string | null;
};

export function StatusPanel({ status, successMessage }: StatusPanelProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Job Status</div>
          <h2>{status.status}</h2>
        </div>
        <span className={`status-pill status-${status.status}`}>{status.status}</span>
      </div>
      <div className="progress-track" aria-hidden="true">
        <div className="progress-fill" style={{ width: `${status.progress}%` }} />
      </div>
      <dl className="status-grid">
        <div>
          <dt>Job ID</dt>
          <dd>{status.id}</dd>
        </div>
        <div>
          <dt>Current step</dt>
          <dd>{status.currentStep}</dd>
        </div>
        <div>
          <dt>Progress</dt>
          <dd>{status.progress}%</dd>
        </div>
        <div>
          <dt>Filename</dt>
          <dd>{status.originalFilename}</dd>
        </div>
      </dl>
      {successMessage ? <p className="success">{successMessage}</p> : null}
      {status.errorMessage ? <p className="error">{status.errorMessage}</p> : null}
    </section>
  );
}

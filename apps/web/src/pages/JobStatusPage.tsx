import type { VideoJobStatusResponse } from '@shared-types';
import { StatusPanel } from '../components/StatusPanel';

type JobStatusPageProps = {
  status: VideoJobStatusResponse;
};

export function JobStatusPage({ status }: JobStatusPageProps) {
  return (
    <div className="page-shell">
      <StatusPanel status={status} />
      <aside className="info-card">
        <div className="eyebrow">Worker Steps</div>
        <ol>
          <li>normalizing_video</li>
          <li>extracting_frames</li>
          <li>transcribing_audio</li>
          <li>describing_frames</li>
          <li>generating_neutral_summary</li>
          <li>generating_styled_captions</li>
          <li>completed</li>
        </ol>
      </aside>
    </div>
  );
}

import type { VideoJobStatus } from '@shared-types';

const STATUS_STYLES: Record<VideoJobStatus, string> = {
  pending_upload: 'bg-[var(--color-tag-yellow-bg)] text-[var(--color-tag-yellow-text)]',
  uploaded: 'bg-[var(--color-tag-blue-bg)] text-[var(--color-tag-blue-text)]',
  queued: 'bg-[var(--color-tag-blue-bg)] text-[var(--color-tag-blue-text)]',
  processing: 'bg-[var(--color-tag-yellow-bg)] text-[var(--color-tag-yellow-text)]',
  completed: 'bg-[var(--color-tag-green-bg)] text-[var(--color-tag-green-text)]',
  failed: 'bg-[var(--color-tag-red-bg)] text-[var(--color-tag-red-text)]',
};

export function JobStatusBadge({ status }: { status: VideoJobStatus }) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]',
        STATUS_STYLES[status],
      ].join(' ')}
    >
      {status.replace('_', ' ')}
    </span>
  );
}

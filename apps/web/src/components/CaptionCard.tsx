type CaptionCardProps = {
  label: string;
  tone: string;
  text: string;
};

export function CaptionCard({ label, tone, text }: CaptionCardProps) {
  return (
    <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-6 transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-[1px] hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
      <div className="flex items-start justify-between gap-3 border-b border-[var(--color-line)] pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
            {label}
          </p>
          <p className="mt-2 text-sm text-[var(--color-muted)]">{tone}</p>
        </div>
        <span className="rounded-full bg-[var(--color-tag-blue-bg)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-tag-blue-text)]">
          Ready
        </span>
      </div>
      <p className="mt-5 text-base leading-8 text-[var(--color-ink)]">{text}</p>
    </article>
  );
}

type CaptionCardProps = {
  label: string;
  tone: string;
  text: string;
};

export function CaptionCard({ label, tone, text }: CaptionCardProps) {
  return (
    <article className="caption-card">
      <div className="caption-meta">
        <span>{label}</span>
        <span>{tone}</span>
      </div>
      <p>{text}</p>
    </article>
  );
}

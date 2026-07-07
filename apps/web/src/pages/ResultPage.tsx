import type { CaptionResultResponse } from '@shared-types';
import { CaptionCard } from '../components/CaptionCard';

type ResultPageProps = {
  result: CaptionResultResponse;
  onReset: () => void;
};

export function ResultPage({ result, onReset }: ResultPageProps) {
  return (
    <div className="result-layout">
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Neutral Summary</div>
            <h2>Worker output is ready.</h2>
          </div>
          <button className="secondary-button" onClick={onReset} type="button">
            Upload another
          </button>
        </div>
        <p className="summary-copy">{result.neutralSummary}</p>
      </section>
      <section className="caption-grid">
        <CaptionCard label="Formal" tone="safe" text={result.formalCaption} />
        <CaptionCard label="Sarcastic" tone="dry" text={result.sarcasticCaption} />
        <CaptionCard label="Humorous Tech" tone="developer" text={result.humorousTechCaption} />
        <CaptionCard
          label="Humorous Non-Tech"
          tone="broad"
          text={result.humorousNonTechCaption}
        />
      </section>
    </div>
  );
}

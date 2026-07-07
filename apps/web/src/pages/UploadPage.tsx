import { UploadForm } from '../components/UploadForm';

type UploadPageProps = {
  isUploading: boolean;
  onUpload: (file: File) => Promise<void>;
  error: string | null;
};

export function UploadPage({ isUploading, onUpload, error }: UploadPageProps) {
  return (
    <div className="page-shell">
      <UploadForm isUploading={isUploading} onUpload={onUpload} />
      <aside className="info-card">
        <div className="eyebrow">Output Modes</div>
        <ul>
          <li>Formal: polished and presentation-safe</li>
          <li>Sarcastic: dry and punchy</li>
          <li>Humorous-tech: developer in-jokes</li>
          <li>Humorous-non-tech: broad audience humor</li>
        </ul>
        {error ? <p className="error">{error}</p> : null}
      </aside>
    </div>
  );
}

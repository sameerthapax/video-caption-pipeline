import { UploadForm } from '../components/UploadForm';

type UploadPageProps = {
  isUploading: boolean;
  uploadProgress: number;
  successMessage: string | null;
  onUpload: (file: File) => Promise<void>;
  error: string | null;
};

export function UploadPage({
  isUploading,
  uploadProgress,
  successMessage,
  onUpload,
  error
}: UploadPageProps) {
  return (
    <div className="page-shell">
      <UploadForm
        isUploading={isUploading}
        uploadProgress={uploadProgress}
        successMessage={successMessage}
        onUpload={onUpload}
      />
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

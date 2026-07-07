import { useState } from 'react';

type UploadFormProps = {
  isUploading: boolean;
  onUpload: (file: File) => Promise<void>;
};

export function UploadForm({ isUploading, onUpload }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file) {
      setError('Select a short video to continue.');
      return;
    }

    setError(null);
    await onUpload(file);
  }

  return (
    <section className="panel">
      <div className="eyebrow">Hackathon Starter</div>
      <h1>Upload a clip and generate four caption styles.</h1>
      <p className="lede">
        The placeholder pipeline simulates video normalization, frame analysis, transcription,
        and caption generation so the product flow is ready before the real AI stack lands.
      </p>
      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="upload-input">
          <span>Video file</span>
          <input
            accept="video/*"
            name="video"
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button className="primary-button" disabled={isUploading} type="submit">
          {isUploading ? 'Uploading...' : 'Start pipeline'}
        </button>
      </form>
    </section>
  );
}

export type VideoJobStatus = 'pending_upload' | 'uploaded' | 'queued' | 'processing' | 'completed' | 'failed';

export interface UploadResponse {
  jobId: string;
  status: VideoJobStatus;
}

export interface UploadPreparationResponse extends UploadResponse {
  bucket: string;
  objectPath: string;
  uploadUrl: string;
  uploadMethod: 'PUT';
  uploadHeaders: Record<string, string>;
}

export interface UploadCompletionResponse extends UploadResponse {
  verified: boolean;
}

export interface VideoJobStatusResponse {
  id: string;
  status: VideoJobStatus;
  currentStep: string;
  progress: number;
  errorMessage: string;
  originalFilename: string;
  createdAt: string;
  updatedAt: string;
}

export interface CaptionResultResponse {
  jobId: string;
  neutralSummary: string;
  formalCaption: string;
  sarcasticCaption: string;
  humorousTechCaption: string;
  humorousNonTechCaption: string;
  rawOutputJson: Record<string, unknown>;
  createdAt: string;
}

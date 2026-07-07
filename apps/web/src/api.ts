import type {
  CaptionResultResponse,
  UploadResponse,
  VideoJobStatusResponse
} from '@shared-types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

type UploadResponseApi = {
  job_id: string;
  status: UploadResponse['status'];
};

type VideoJobStatusResponseApi = {
  id: string;
  status: VideoJobStatusResponse['status'];
  current_step: string;
  progress: number;
  error_message: string;
  original_filename: string;
  created_at: string;
  updated_at: string;
};

type CaptionResultResponseApi = {
  job_id: string;
  neutral_summary: string;
  formal_caption: string;
  sarcastic_caption: string;
  humorous_tech_caption: string;
  humorous_non_tech_caption: string;
  raw_pipeline_json: Record<string, unknown>;
  created_at: string;
};

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('video', file);

  const response = await fetch(`${API_BASE_URL}/api/videos/upload/`, {
    method: 'POST',
    body: formData
  });

  const payload = await parseResponse<UploadResponseApi>(response);
  return {
    jobId: payload.job_id,
    status: payload.status
  };
}

export async function getJobStatus(jobId: string): Promise<VideoJobStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/status/`);
  const payload = await parseResponse<VideoJobStatusResponseApi>(response);
  return {
    id: payload.id,
    status: payload.status,
    currentStep: payload.current_step,
    progress: payload.progress,
    errorMessage: payload.error_message,
    originalFilename: payload.original_filename,
    createdAt: payload.created_at,
    updatedAt: payload.updated_at
  };
}

export async function getJobResult(jobId: string): Promise<CaptionResultResponse> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/result/`);
  const payload = await parseResponse<CaptionResultResponseApi>(response);
  return {
    jobId: payload.job_id,
    neutralSummary: payload.neutral_summary,
    formalCaption: payload.formal_caption,
    sarcasticCaption: payload.sarcastic_caption,
    humorousTechCaption: payload.humorous_tech_caption,
    humorousNonTechCaption: payload.humorous_non_tech_caption,
    rawPipelineJson: payload.raw_pipeline_json,
    createdAt: payload.created_at
  };
}

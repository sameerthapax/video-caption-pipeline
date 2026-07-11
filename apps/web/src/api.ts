import type {
  AuthProfileResponse,
  CaptionResultResponse,
  JobListItemResponse,
  UploadPreparationResponse,
  VideoJobStatusResponse,
} from '@shared-types';

const API_BASE_URL = resolveApiBaseUrl();
const CSRF_COOKIE = 'vp_csrf_token';
const CSRF_HEADER = 'X-CSRF-Token';
const AUTH_DISABLED = resolveAuthDisabled();

export type AuthUser = {
  id: string;
  email: string | null;
};

type AuthSessionResponseApi = {
  user: AuthUser;
};

type AuthProfileResponseApi = {
  user: AuthUser;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  active_jobs: number;
  latest_job_at: string | null;
};

type UploadPreparationRequestApi = {
  filename: string;
  content_type: string;
};

type UploadPreparationResponseApi = {
  job_id: string;
  bucket: string;
  object_key: string;
  upload_url: string;
  expires_in: number;
  headers: Record<string, string>;
};

type UploadCompletionRequestApi = {
  job_id: string;
  source_key: string;
  filename: string;
  content_type: string;
};

export type UploadStreamEvent = {
  event: string;
  jobId: string;
  step: string;
  message: string;
  progress?: number;
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

type JobListItemResponseApi = VideoJobStatusResponseApi & {
  has_result: boolean;
};

type CaptionResultResponseApi = {
  job_id: string;
  neutral_summary: string;
  formal_caption: string;
  sarcastic_caption: string;
  humorous_tech_caption: string;
  humorous_non_tech_caption: string;
  raw_output_json: Record<string, unknown>;
  created_at: string;
};

function resolveApiBaseUrl(): string {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configuredUrl) {
    return configuredUrl.replace(/\/$/, '');
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000';
    }
  }

  throw new Error('VITE_API_BASE_URL is required for non-local environments.');
}

function resolveAuthDisabled(): boolean {
  const configuredValue = import.meta.env.VITE_DISABLE_AUTH?.trim().toLowerCase();
  if (configuredValue) {
    return configuredValue === 'true';
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    return hostname !== 'localhost' && hostname !== '127.0.0.1';
  }

  return false;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      const payload = (await response.json()) as {
        detail?: string | { msg?: string }[];
        errors?: { msg?: string }[];
      };
      const detail =
        typeof payload.detail === 'string'
          ? payload.detail
          : Array.isArray(payload.detail)
            ? payload.detail.map((item) => item.msg).filter(Boolean).join(', ')
            : Array.isArray(payload.errors)
              ? payload.errors.map((item) => item.msg).filter(Boolean).join(', ')
              : null;
      throw new Error(detail || `Request failed with status ${response.status}`);
    }

    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const method = (init?.method ?? 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrfToken = getCookieValue(CSRF_COOKIE);
    if (csrfToken) {
      headers.set(CSRF_HEADER, csrfToken);
    }
  }

  return fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...init,
    headers,
  });
}

function getCookieValue(name: string): string | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const cookies = document.cookie ? document.cookie.split('; ') : [];
  for (const cookie of cookies) {
    const [key, ...valueParts] = cookie.split('=');
    if (key === name) {
      return decodeURIComponent(valueParts.join('='));
    }
  }

  return null;
}

export async function signup(email: string, password: string): Promise<AuthUser> {
  if (AUTH_DISABLED) {
    return { id: 'guest', email: 'guest@example.com' };
  }
  const response = await apiFetch('/api/auth/signup/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  const payload = await parseResponse<AuthSessionResponseApi>(response);
  return payload.user;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  if (AUTH_DISABLED) {
    return { id: 'guest', email: 'guest@example.com' };
  }
  const response = await apiFetch('/api/auth/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  const payload = await parseResponse<AuthSessionResponseApi>(response);
  return payload.user;
}

export async function logout(): Promise<void> {
  if (AUTH_DISABLED) {
    return;
  }
  const response = await apiFetch('/api/auth/logout/', {
    method: 'POST',
  });
  await parseResponse<void>(response);
}

export async function getSession(): Promise<AuthUser> {
  if (AUTH_DISABLED) {
    return { id: 'guest', email: 'guest@example.com' };
  }
  const response = await apiFetch('/api/auth/session/');
  const payload = await parseResponse<AuthSessionResponseApi>(response);
  return payload.user;
}

export async function getProfile(): Promise<AuthProfileResponse> {
  if (AUTH_DISABLED) {
    return {
      user: { id: 'guest', email: null },
      totalJobs: 0,
      completedJobs: 0,
      failedJobs: 0,
      activeJobs: 0,
      latestJobAt: null,
    };
  }
  const response = await apiFetch('/api/auth/profile/');
  const payload = await parseResponse<AuthProfileResponseApi>(response);
  return {
    user: payload.user,
    totalJobs: payload.total_jobs,
    completedJobs: payload.completed_jobs,
    failedJobs: payload.failed_jobs,
    activeJobs: payload.active_jobs,
    latestJobAt: payload.latest_job_at,
  };
}

export async function listJobs(): Promise<JobListItemResponse[]> {
  if (AUTH_DISABLED) {
    return [];
  }
  const response = await apiFetch('/api/jobs/');
  const payload = await parseResponse<JobListItemResponseApi[]>(response);
  return payload.map(mapJobListItemResponse);
}

export async function getJobStatus(jobId: string): Promise<VideoJobStatusResponse> {
  const response = await apiFetch(`/jobs/${jobId}`);
  const payload = await parseResponse<Record<string, unknown>>(response);
  return mapLambdaJobStatusResponse(payload);
}

export async function getJobResult(jobId: string): Promise<CaptionResultResponse> {
  const response = await apiFetch(`/jobs/${jobId}/result`);
  const payload = await parseResponse<{ result?: CaptionResultResponseApi; status?: string }>(response);
  if (!payload.result) {
    throw new Error(payload.status === 'completed' ? 'Result payload missing.' : 'Result is not ready yet.');
  }
  return {
    jobId: payload.result.job_id,
    neutralSummary: payload.result.neutral_summary,
    formalCaption: payload.result.formal_caption,
    sarcasticCaption: payload.result.sarcastic_caption,
    humorousTechCaption: payload.result.humorous_tech_caption,
    humorousNonTechCaption: payload.result.humorous_non_tech_caption,
    rawOutputJson: payload.result.raw_output_json,
    createdAt: payload.result.created_at,
  };
}

export async function uploadVideo(
  file: File,
  onProgress?: (progress: number) => void,
  onStreamEvent?: (event: UploadStreamEvent) => void
): Promise<{ jobId: string }> {
  const preparation = await prepareVideoUpload(file);
  await uploadFileToSignedUrl(preparation, file, onProgress);
  await completeVideoUploadStream(preparation, file, onStreamEvent);
  return { jobId: preparation.jobId };
}

async function prepareVideoUpload(file: File): Promise<UploadPreparationResponse> {
  const contentType = file.type || inferVideoContentType(file.name);
  const response = await apiFetch('/uploads/presign', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename: file.name,
      content_type: contentType,
    } satisfies UploadPreparationRequestApi),
  });

  const payload = await parseResponse<UploadPreparationResponseApi>(response);
  return {
    jobId: payload.job_id,
    status: 'queued',
    bucket: payload.bucket,
    objectPath: payload.object_key,
    uploadUrl: payload.upload_url,
    uploadMethod: 'PUT',
    uploadHeaders: payload.headers,
  };
}

function uploadFileToSignedUrl(
  preparation: UploadPreparationResponse,
  file: File,
  onProgress?: (progress: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(preparation.uploadMethod, preparation.uploadUrl, true);

    for (const [key, value] of Object.entries(preparation.uploadHeaders)) {
      xhr.setRequestHeader(key, value);
    }

    xhr.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable || !onProgress) {
        return;
      }
      onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100);
        resolve();
        return;
      }

      reject(new Error(xhr.responseText || `Upload failed with status ${xhr.status}`));
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Network error while uploading to storage.'));
    });

    xhr.send(file);
  });
}

async function completeVideoUploadStream(
  preparation: UploadPreparationResponse,
  file: File,
  onStreamEvent?: (event: UploadStreamEvent) => void
): Promise<void> {
  onStreamEvent?.({
    event: 'queued',
    jobId: preparation.jobId,
    step: 'registering',
    message: 'Registering uploaded file and queueing the worker job.',
    progress: 100,
  });

  const response = await apiFetch('/jobs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      job_id: preparation.jobId,
      source_key: preparation.objectPath,
      filename: file.name,
      content_type: file.type || inferVideoContentType(file.name),
    } satisfies UploadCompletionRequestApi),
  });
  await parseResponse<Record<string, unknown>>(response);
  onStreamEvent?.({
    event: 'queued',
    jobId: preparation.jobId,
    step: 'queued',
    message: 'Upload registered. Worker job queued successfully.',
    progress: 100,
  });
}

function inferVideoContentType(filename: string): string {
  const extension = filename.split('.').pop()?.toLowerCase();
  switch (extension) {
    case 'mp4':
      return 'video/mp4';
    case 'mov':
      return 'video/quicktime';
    case 'webm':
      return 'video/webm';
    case 'mkv':
      return 'video/x-matroska';
    case 'm4v':
      return 'video/x-m4v';
    default:
      return 'application/octet-stream';
  }
}

function mapLambdaJobStatusResponse(payload: Record<string, unknown>): VideoJobStatusResponse {
  return {
    id: String(payload.job_id ?? ''),
    status: mapLambdaStatus(payload.status),
    currentStep: String(payload.current_step ?? payload.status ?? 'queued'),
    progress: Number(payload.progress ?? 0),
    errorMessage: String(payload.error_message ?? ''),
    originalFilename: String(payload.original_filename ?? 'Uploaded video'),
    createdAt: String(payload.created_at ?? new Date().toISOString()),
    updatedAt: String(payload.updated_at ?? payload.created_at ?? new Date().toISOString()),
  };
}

function mapLambdaStatus(value: unknown): VideoJobStatusResponse['status'] {
  const status = String(value ?? 'queued');
  if (
    status === 'pending_upload' ||
    status === 'uploaded' ||
    status === 'queued' ||
    status === 'processing' ||
    status === 'completed' ||
    status === 'failed'
  ) {
    return status;
  }
  return 'queued';
}

function mapVideoJobStatusResponse(payload: VideoJobStatusResponseApi): VideoJobStatusResponse {
  return {
    id: payload.id,
    status: payload.status,
    currentStep: payload.current_step,
    progress: payload.progress,
    errorMessage: payload.error_message,
    originalFilename: payload.original_filename,
    createdAt: payload.created_at,
    updatedAt: payload.updated_at,
  };
}

function mapJobListItemResponse(payload: JobListItemResponseApi): JobListItemResponse {
  return {
    ...mapVideoJobStatusResponse(payload),
    hasResult: payload.has_result,
  };
}

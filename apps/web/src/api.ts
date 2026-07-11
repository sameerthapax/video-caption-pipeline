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
  file_size: number;
};

type UploadPreparationResponseApi = {
  job_id: string;
  status: UploadPreparationResponse['status'];
  bucket: string;
  object_path: string;
  upload_url: string;
  upload_method: 'PUT';
  upload_headers: Record<string, string>;
};

type UploadCompletionRequestApi = {
  job_id: string;
  object_path: string;
  file_size: number;
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
  const response = await apiFetch('/api/auth/logout/', {
    method: 'POST',
  });
  await parseResponse<void>(response);
}

export async function getSession(): Promise<AuthUser> {
  const response = await apiFetch('/api/auth/session/');
  const payload = await parseResponse<AuthSessionResponseApi>(response);
  return payload.user;
}

export async function getProfile(): Promise<AuthProfileResponse> {
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
  const response = await apiFetch('/api/jobs/');
  const payload = await parseResponse<JobListItemResponseApi[]>(response);
  return payload.map(mapJobListItemResponse);
}

export async function getJobStatus(jobId: string): Promise<VideoJobStatusResponse> {
  const response = await apiFetch(`/api/jobs/${jobId}/status/`);
  const payload = await parseResponse<VideoJobStatusResponseApi>(response);
  return mapVideoJobStatusResponse(payload);
}

export async function getJobResult(jobId: string): Promise<CaptionResultResponse> {
  const response = await apiFetch(`/api/jobs/${jobId}/result/`);
  const payload = await parseResponse<CaptionResultResponseApi>(response);
  return {
    jobId: payload.job_id,
    neutralSummary: payload.neutral_summary,
    formalCaption: payload.formal_caption,
    sarcasticCaption: payload.sarcastic_caption,
    humorousTechCaption: payload.humorous_tech_caption,
    humorousNonTechCaption: payload.humorous_non_tech_caption,
    rawOutputJson: payload.raw_output_json,
    createdAt: payload.created_at,
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
  const response = await apiFetch('/api/videos/upload/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename: file.name,
      content_type: contentType,
      file_size: file.size,
    } satisfies UploadPreparationRequestApi),
  });

  const payload = await parseResponse<UploadPreparationResponseApi>(response);
  return {
    jobId: payload.job_id,
    status: payload.status,
    bucket: payload.bucket,
    objectPath: payload.object_path,
    uploadUrl: payload.upload_url,
    uploadMethod: payload.upload_method,
    uploadHeaders: payload.upload_headers,
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
  const response = await apiFetch('/api/videos/upload/complete/stream', {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      job_id: preparation.jobId,
      object_path: preparation.objectPath,
      file_size: file.size,
      content_type: file.type || inferVideoContentType(file.name),
    } satisfies UploadCompletionRequestApi),
  });

  if (!response.ok) {
    throw await buildResponseError(response);
  }

  if (!response.body) {
    throw new Error('Streaming upload completion response did not include a body.');
  }

  await readEventStream(response, (rawEvent) => {
    if (!rawEvent.data) {
      return;
    }

    const payload = JSON.parse(rawEvent.data) as {
      event: string;
      job_id: string;
      step: string;
      message: string;
      progress?: number;
    };

    onStreamEvent?.({
      event: payload.event,
      jobId: payload.job_id,
      step: payload.step,
      message: payload.message,
      progress: payload.progress,
    });

    if (payload.event === 'failed') {
      throw new Error(payload.message || 'Upload completion stream failed.');
    }
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

async function buildResponseError(response: Response): Promise<Error> {
  try {
    await parseResponse(response);
  } catch (error) {
    return error instanceof Error ? error : new Error('Request failed.');
  }

  return new Error(`Request failed with status ${response.status}`);
}

async function readEventStream(
  response: Response,
  onEvent: (event: { event: string; data: string }) => void
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Streaming response body could not be read.');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundaryMatch = buffer.match(/\r?\n\r?\n/);
    while (boundaryMatch?.index !== undefined) {
      const boundaryLength = boundaryMatch[0].length;
      const rawChunk = buffer.slice(0, boundaryMatch.index);
      buffer = buffer.slice(boundaryMatch.index + boundaryLength);
      const parsedEvent = parseSseChunk(rawChunk);
      if (parsedEvent) {
        onEvent(parsedEvent);
      }
      boundaryMatch = buffer.match(/\r?\n\r?\n/);
    }

    if (done) {
      const trailingEvent = parseSseChunk(buffer);
      if (trailingEvent) {
        onEvent(trailingEvent);
      }
      return;
    }
  }
}

function parseSseChunk(chunk: string): { event: string; data: string } | null {
  const lines = chunk
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.length > 0 && !line.startsWith(':'));

  if (lines.length === 0) {
    return null;
  }

  let event = 'message';
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim();
      continue;
    }

    if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim());
    }
  }

  return dataLines.length > 0 ? { event, data: dataLines.join('\n') } : null;
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

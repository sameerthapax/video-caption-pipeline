import type {
  CaptionResultResponse,
  UploadResponse,
  VideoJobStatusResponse
} from '@shared-types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const CSRF_COOKIE = 'vp_csrf_token';
const CSRF_HEADER = 'X-CSRF-Token';

export type AuthUser = {
  id: string;
  email: string | null;
};

type AuthSessionResponseApi = {
  user: AuthUser;
};

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
  raw_output_json: Record<string, unknown>;
  created_at: string;
};

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      const payload = (await response.json()) as { detail?: string };
      throw new Error(payload.detail || `Request failed with status ${response.status}`);
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
    headers
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
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });
  const payload = await parseResponse<AuthSessionResponseApi>(response);
  return payload.user;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const response = await apiFetch('/api/auth/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });
  const payload = await parseResponse<AuthSessionResponseApi>(response);
  return payload.user;
}

export async function logout(): Promise<void> {
  const response = await apiFetch('/api/auth/logout/', {
    method: 'POST'
  });
  await parseResponse<void>(response);
}

export async function getSession(): Promise<AuthUser> {
  const response = await apiFetch('/api/auth/session/');
  const payload = await parseResponse<AuthSessionResponseApi>(response);
  return payload.user;
}

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('video', file);

  const response = await apiFetch('/api/videos/upload/', {
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
  const response = await apiFetch(`/api/jobs/${jobId}/status/`);
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
    createdAt: payload.created_at
  };
}

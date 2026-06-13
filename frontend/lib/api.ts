const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SourceChunk {
  text: string;
  document_name: string;
  page_number?: number;
  chunk_index: number;
  score: number;
  document_id?: string;
}

export interface Citation {
  source_index: number;
  text: string;
  document_name: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceChunk[];
  citations?: Citation[];
  query: string;
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  upload_time: string;
  file_size_bytes: number;
  status: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  status: string;
  message: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceChunk[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
}

// ── Authentication Management ────────────────────────────────────────────────

function getAccessToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token');
  }
  return null;
}

function getRefreshToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('refresh_token');
  }
  return null;
}

function setTokens(access: string, refresh: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }
}

export function clearTokens() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
}

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  let token = getAccessToken();
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response = await fetch(url, { ...options, headers });

  // If unauthorized, attempt to refresh token once
  if (response.status === 401) {
    const refresh = getRefreshToken();
    if (refresh) {
      try {
        const refreshResp = await fetch(`${API_URL}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refresh })
        });
        
        if (refreshResp.ok) {
          const data: TokenResponse = await refreshResp.json();
          setTokens(data.access_token, data.refresh_token);
          
          // Retry original request
          headers.set('Authorization', `Bearer ${data.access_token}`);
          response = await fetch(url, { ...options, headers });
        } else {
          clearTokens();
          // Trigger a redirect to login in the app (handled by AuthContext)
          window.dispatchEvent(new Event('auth_expired'));
        }
      } catch (e) {
        clearTokens();
        window.dispatchEvent(new Event('auth_expired'));
      }
    } else {
      clearTokens();
      window.dispatchEvent(new Event('auth_expired'));
    }
  }

  return response;
}

// ── Auth Endpoints ─────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<UserResponse> {
  const resp = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Login failed');
  }

  const tokenData: TokenResponse = await resp.json();
  setTokens(tokenData.access_token, tokenData.refresh_token);

  return getMe();
}

export async function register(email: string, password: string, full_name: string): Promise<UserResponse> {
  const resp = await fetch(`${API_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name })
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Registration failed');
  }

  const tokenData: TokenResponse = await resp.json();
  setTokens(tokenData.access_token, tokenData.refresh_token);

  return getMe();
}

export async function getMe(): Promise<UserResponse> {
  const resp = await fetchWithAuth(`${API_URL}/api/auth/me`);
  if (!resp.ok) {
    throw new Error('Failed to get user profile');
  }
  return resp.json();
}

// ── Document Endpoints ──────────────────────────────────────────────────────

export async function uploadPDF(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetchWithAuth(`${API_URL}/api/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

export async function getDocuments(): Promise<DocumentInfo[]> {
  const response = await fetchWithAuth(`${API_URL}/api/documents`);
  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.status}`);
  }
  return response.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetchWithAuth(`${API_URL}/api/documents/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete document: ${response.status}`);
  }
}

// ── Chat & SSE ─────────────────────────────────────────────────────────────

/**
 * Sends a chat query using SSE streaming and invokes callbacks for different events.
 */
export async function streamChat(
  query: string, 
  callbacks: {
    onStart?: (session_id?: string) => void;
    onToken?: (token: string) => void;
    onSources?: (sources: SourceChunk[]) => void;
    onDone?: (fullAnswer: string) => void;
    onError?: (errorMsg: string) => void;
  },
  document_ids?: string[]
): Promise<void> {
  const body = { query, stream: true, document_ids };
  const token = getAccessToken();
  const headers = new Headers({
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  });
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      if (response.status === 401) {
        window.dispatchEvent(new Event('auth_expired'));
        throw new Error("Authentication expired");
      }
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Chat request failed');
    }

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      buffer = lines.pop() || ''; // Keep the incomplete line in the buffer

      let currentEvent = '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.substring(7).trim();
        } else if (line.startsWith('data: ')) {
          const dataStr = line.substring(6).trim();
          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            
            if (currentEvent === 'start' && callbacks.onStart) {
              callbacks.onStart(data.session_id);
            } else if (currentEvent === 'token' && callbacks.onToken) {
              callbacks.onToken(data.token);
            } else if (currentEvent === 'sources' && callbacks.onSources) {
              callbacks.onSources(data.sources);
            } else if (currentEvent === 'done' && callbacks.onDone) {
              callbacks.onDone(data.answer);
            } else if (currentEvent === 'error' && callbacks.onError) {
              callbacks.onError(data.error || "Stream error");
            }
          } catch (e) {
            console.error("Failed to parse SSE data", dataStr, e);
          }
        }
      }
    }
  } catch (err) {
    if (callbacks.onError) {
      callbacks.onError(err instanceof Error ? err.message : String(err));
    }
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

function getAuthHeaders(): HeadersInit {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    apiFetch('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),

  register: (data: object) =>
    apiFetch('/auth/register', { method: 'POST', body: JSON.stringify(data) }),

  getDashboard: () => apiFetch('/auth/dashboard'),

  // Questions
  getQuestions: (params: Record<string, string | number | undefined>) => {
    const query = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== '')
          .map(([k, v]) => [k, String(v)])
      )
    ).toString();
    return apiFetch(`/questions?${query}`);
  },

  getQuestion: (id: number) => apiFetch(`/questions/${id}`),

  updateQuestion: (id: number, data: object) =>
    apiFetch(`/questions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteQuestion: (id: number) =>
    apiFetch(`/questions/${id}`, { method: 'DELETE' }),

  deleteAllQuestions: () =>
    apiFetch('/questions/all', { method: 'DELETE' }),

  getSubjects: () => apiFetch('/questions/subjects/list'),

  getMetadataFilters: () => apiFetch('/questions/metadata/filters'),

  // Upload
  uploadTex: (formData: FormData) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    return fetch(`${API_URL}/upload/tex`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Upload failed');
      }
      return res.json();
    });
  },

  confirmUpload: (data: object) =>
    apiFetch('/upload/confirm', { method: 'POST', body: JSON.stringify(data) }),

  confirmUploadAsContest: (data: object) =>
    apiFetch('/upload/confirm-as-contest', { method: 'POST', body: JSON.stringify(data) }),

  // Classes
  getClasses: () => apiFetch('/classes'),

  createClass: (data: object) =>
    apiFetch('/classes', { method: 'POST', body: JSON.stringify(data) }),

  getClass: (id: number) => apiFetch(`/classes/${id}`),

  deleteClass: (id: number) =>
    apiFetch(`/classes/${id}`, { method: 'DELETE' }),

  joinClass: (classPublicId: string) =>
    apiFetch('/classes/join', { method: 'POST', body: JSON.stringify({ class_public_id: classPublicId }) }),

  addStudentToClass: (classId: number, identifier: string) =>
    apiFetch(`/classes/${classId}/students`, { method: 'POST', body: JSON.stringify({ identifier }) }),

  searchStudents: (query: string) =>
    apiFetch(`/classes/students/search?q=${encodeURIComponent(query)}`),

  // Contests
  getContests: () => apiFetch('/contests'),

  createContest: (data: object) =>
    apiFetch('/contests', { method: 'POST', body: JSON.stringify(data) }),

  createRandomContest: (data: object) =>
    apiFetch('/contests/random', { method: 'POST', body: JSON.stringify(data) }),

  getContest: (id: number) => apiFetch(`/contests/${id}`),

  getContestSubmissions: (id: number) => apiFetch(`/contests/${id}/submissions`),

  deleteResult: (id: number) => apiFetch(`/contests/results/${id}`, { method: 'DELETE' }),

  startContest: (id: number, data: object) =>
    apiFetch(`/contests/${id}/start`, { method: 'POST', body: JSON.stringify(data) }),

  submitContest: (id: number, data: object) =>
    apiFetch(`/contests/${id}/submit`, { method: 'POST', body: JSON.stringify(data) }),

  getResult: (resultId: number) => apiFetch(`/contests/results/${resultId}`),

  updateContestStatus: (id: number, status: string) =>
    apiFetch(`/contests/${id}/status?status=${status}`, { method: 'PATCH' }),

  exportContest: async (id: number, data: object) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const res = await fetch(`${API_URL}/export/exam/${id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Export failed');
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    // Lấy filename từ header Content-Disposition nếu có
    const contentDisposition = res.headers.get('Content-Disposition');
    let filename = `Export_Contest_${id}.zip`;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      if (filenameMatch && filenameMatch.length === 2) {
        filename = filenameMatch[1];
      }
    }
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};

export default api;

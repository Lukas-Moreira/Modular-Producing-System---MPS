const RAW_API_URL = process.env.REACT_APP_API_URL || "http://localhost:3000/";
const API_URL = RAW_API_URL.endsWith('/') ? RAW_API_URL : RAW_API_URL + '/';

function buildUrl(endpoint: string) {
  const path = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return `${API_URL}${path}`;
}

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access_token');

  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers,
  } as Record<string, string>;

  const response = await fetch(buildUrl(endpoint), {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('user');
    throw new Error('Sessão expirada. Faça login novamente.');
  }

  return response;
}

export function isAuthenticated(): boolean {
  return localStorage.getItem('access_token') !== null;
}

export function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('isAuthenticated');
  localStorage.removeItem('user');
}
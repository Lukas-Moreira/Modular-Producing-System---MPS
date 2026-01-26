const API_URL = "http://192.168.0.77:8000/";

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_URL}${endpoint}`, {
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
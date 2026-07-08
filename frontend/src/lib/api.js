import axios from 'axios';

export const API_URL = (process.env.REACT_APP_API_URL || 'http://localhost:8000').replace(/\/$/, '');
/** Website-only Google OAuth client (Web application type — NOT the extension client). */
export const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

const TOKEN_KEY = 'krai_token';
const EMAIL_KEY = 'krai_user_email';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuth(token, email) {
  localStorage.setItem(TOKEN_KEY, token);
  if (email) localStorage.setItem(EMAIL_KEY, email);
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EMAIL_KEY);
}

export function getStoredEmail() {
  return localStorage.getItem(EMAIL_KEY) || '';
}

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function fetchMe() {
  const res = await api.get('/api/v1/auth/me');
  return res.data;
}

export async function login(email, password) {
  const res = await api.post('/api/v1/auth/login', { email, password });
  setAuth(res.data.access_token, email);
  return res.data;
}

export async function register(email, password, fullName) {
  const res = await api.post('/api/v1/auth/register', {
    email,
    password,
    full_name: fullName || undefined,
  });
  setAuth(res.data.access_token, email);
  return res.data;
}

export async function googleLogin(idToken) {
  const res = await api.post('/api/v1/auth/google', { id_token: idToken, platform: 'web' });
  return res.data;
}

export async function fetchMeetings() {
  const res = await api.get('/api/v1/meetings');
  return res.data.items || [];
}

export function meetingUrl(meetingId, shareToken) {
  const url = new URL(window.location.origin);
  url.pathname = '/';
  url.searchParams.set('meeting_id', meetingId);
  if (shareToken) url.searchParams.set('share', shareToken);
  url.searchParams.set('api', API_URL);
  return url.toString();
}

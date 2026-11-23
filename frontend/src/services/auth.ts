import axios from 'axios'

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000',
  headers: { 'Content-Type': 'application/json' },
})

export async function loginWithBackend(email: string, password: string): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>('/api/auth/login', { email, password })
  return response.data
}
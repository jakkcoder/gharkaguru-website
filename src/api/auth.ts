import { apiGet, apiPost } from './http'

export type AuthRole = 'student' | 'teacher'

export function phoneLogin(phone: string, role: AuthRole = 'student') {
  return apiPost<{ token: string; role: AuthRole }>('/api/auth/otp/send', { phone, role })
}

export function getEnquiries() {
  return apiGet<{ items: unknown[] }>('/api/enquiries')
}


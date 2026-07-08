import { apiGet, apiPostForm } from './http'
import { apiPost } from './http'

export function submitTeacherRegistration(form: FormData, idempotencyKey?: string) {
  return apiPostForm<{ referenceId: string }>('/api/teacher/register', form, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
  })
}

export function getTeacherApplication() {
  return apiGet<{ referenceId: string | null; status: string; profileCompletionPercent: number }>('/api/teacher/application')
}

export function upsertTeacherApplicationDraft(data: Record<string, unknown>) {
  return apiPost<{ referenceId: string; status: string; profileCompletionPercent: number }>('/api/teacher/application/draft', { data })
}


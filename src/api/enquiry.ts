import { ApiError, apiPost } from './http'

export function submitInquiry(payload: { tutorId: string; contactPhone: string; message?: string }) {
  return apiPost<{ inquiryId: string }>('/api/inquiry', payload)
}

export function submitLeadInquiry(payload: {
  contactPhone: string
  classLevel: string
  subject: string
}) {
  const body = {
    contactPhone: payload.contactPhone,
    classLevel: payload.classLevel,
    subject: payload.subject,
  }

  return apiPost<{ inquiryId: string }>('/api/lead-inquiry', body).catch(async (err) => {
    if (
      err instanceof ApiError &&
      err.status === 404 &&
      (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ) {
      // Dev fallback: call gateway directly.
      const res = await fetch('http://localhost:8080/v1/api/lead-inquiry', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new ApiError(text || `Request failed: ${res.status}`, res.status)
      }
      return (await res.json()) as { inquiryId: string }
    }
    throw err
  })
}


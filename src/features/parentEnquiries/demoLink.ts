import type { ParentEnquiry } from '../../api/parentEnquiries'
import { displayValue } from './display'

/**
 * Link to the teacher demo app, which the website's nginx proxies at /demo to an
 * internal service. Only the enquiry fields already public on this page are passed;
 * the parent's name and phone never are.
 */
export function demoSubmissionHref(enquiry: ParentEnquiry, teacherPhone?: string | null): string {
  const params = new URLSearchParams()
  const fields: Record<string, string> = {
    lead_id: enquiry.id,
    student_name: enquiry.studentName,
    class_level: enquiry.classLevel,
    subject: enquiry.subject,
    board: enquiry.board,
    medium: displayValue(enquiry.medium),
    tutor_mode: displayValue(enquiry.tutorMode),
    teacher_preference: displayValue(enquiry.teacherPreference),
    area: enquiry.address,
    pin: enquiry.pin,
    budget: enquiry.budget,
    schedule: enquiry.schedule,
    notes: enquiry.notes,
    phone: teacherPhone || '',
  }
  for (const [key, value] of Object.entries(fields)) {
    const text = (value || '').trim()
    if (text) params.set(key, text)
  }
  return `/demo/?${params.toString()}`
}

import { Link } from 'react-router-dom'
import type { ParentEnquiry } from '../../api/parentEnquiries'

const LABELS: Record<string, string> = {
  home: 'Home tutor',
  online: 'Online tutor',
  english: 'English',
  hindi: 'Hindi',
  male: 'Male',
  female: 'Female',
}

function displayValue(value: string) {
  const text = value.trim()
  return LABELS[text.toLowerCase()] || text
}

function classHeading(value: string) {
  const text = value.trim()
  if (!text) return 'Class —'
  if (/^class\b/i.test(text)) return text
  return `Class ${text}`
}

function line(label: string, value: string) {
  const text = displayValue(value)
  if (!text) return null
  return (
    <p className="text-sm text-tn-muted">
      <span className="font-medium text-tn-text">{label}: </span>
      {text}
    </p>
  )
}

export function EnquiryCard({ enquiry, showLink = true }: { enquiry: ParentEnquiry; showLink?: boolean }) {
  return (
    <article className="rounded-2xl border border-tn-border bg-white p-5">
      <h2 className="text-lg font-semibold">
        {enquiry.studentName || 'Student'} · {classHeading(enquiry.classLevel)}
      </h2>
      <div className="mt-3 space-y-1">
        {line('Subject', enquiry.subject)}
        {line('Board', enquiry.board)}
        {line('Medium', enquiry.medium)}
        {line('Mode', enquiry.tutorMode)}
        {line('Teacher preference', enquiry.teacherPreference)}
        {line('Address', enquiry.address)}
        {line('PIN', enquiry.pin)}
        {line('Budget', enquiry.budget)}
        {line('Notes', enquiry.notes)}
      </div>
      {showLink ? (
        <Link to={`/parent-enquiries/${enquiry.id}`} className="mt-4 inline-flex text-sm font-medium text-tn-primary">
          Move forward
        </Link>
      ) : null}
    </article>
  )
}

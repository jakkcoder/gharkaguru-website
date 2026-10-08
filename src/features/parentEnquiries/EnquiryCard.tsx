import { Link } from 'react-router-dom'
import type { ParentEnquiry } from '../../api/parentEnquiries'
import { demoSubmissionHref } from './demoLink'
import { displayValue } from './display'

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

export function EnquiryCard({
  enquiry,
  showLink = true,
  teacherPhone,
}: {
  enquiry: ParentEnquiry
  showLink?: boolean
  teacherPhone?: string | null
}) {
  return (
    <article className="rounded-2xl border border-tn-border bg-white p-5">
      <h2 className="text-lg font-semibold">
        {classHeading(enquiry.classLevel)}
      </h2>
      <div className="mt-3 space-y-1">
        {line('Subject', enquiry.subject)}
        {line('Board', enquiry.board)}
        {line('Medium', enquiry.medium)}
        {line('Mode', enquiry.tutorMode)}
        {line('Teacher preference', enquiry.teacherPreference)}
        {line('Area', enquiry.locality)}
        {line('PIN', enquiry.pin)}
        {line('Budget', enquiry.budget)}
        {line('Schedule', enquiry.schedule)}
        {line('Notes', enquiry.notes)}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
        {showLink ? (
          <Link to={`/parent-enquiries/${enquiry.id}`} className="inline-flex text-sm font-medium text-tn-primary">
            Move forward
          </Link>
        ) : null}
        {/* Full page load: /demo is a separate app behind the same domain. */}
        <a
          href={demoSubmissionHref(enquiry, teacherPhone)}
          className="inline-flex items-center rounded-lg bg-tn-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-tn-primaryDark"
        >
          Submit your demo
        </a>
      </div>
    </article>
  )
}

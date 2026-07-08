export type AnalyticsEvent =
  | 'search_submitted'
  | 'filter_applied'
  | 'tutor_profile_viewed'
  | 'contact_clicked'
  | 'enquiry_submitted'
  | 'lead_enquiry_submitted'
  | 'teacher_registration_started'
  | 'teacher_registration_submitted'
  | 'shortlist_added'
  | 'shortlist_removed'

export function trackEvent(event: AnalyticsEvent, payload?: Record<string, unknown>) {
  // Stub for now per spec: log to console (backend later).
  console.log('[analytics]', event, payload ?? {})
}


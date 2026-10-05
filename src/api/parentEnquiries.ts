import { apiGet, apiPost } from './http'

export type ParentEnquiry = {
  id: string
  status: string
  parentName: string
  studentName: string
  classLevel: string
  subject: string
  board: string
  medium: string
  tutorMode: string
  teacherPreference: string
  address: string
  pin: string
  budget: string
  notes: string
  schedule: string
  updatedAt: string
}

export type EnquiryPolicy = {
  version: string
  text: string
  hash: string
  firstFeeRupees: number
  nextFeeRupees: number
  commissionPercent: number
}

export type EnquiryEligibility = {
  registered: boolean
  source: string
  nextFeeRupees: number
}

export type AccessPayment = {
  id: string
  status: string
  amountRupees: number
  amountPaise: number
  currency: string
  provider: string | null
  providerOrderId: string | null
  providerReference: string | null
}

export type TeacherEnquiryApplication = {
  enquiryId: string
  studentName: string
  subject: string
  classLevel: string
  enquiryStatus: string
  paymentId: string
  paymentStatus: string
  amountRupees: number
  createdAt: string
  parentPhone: string
  parentName: string
}

export function parentPhoneForDisplay(paymentStatus: string, phone: string) {
  return paymentStatus === 'paid' ? phone : ''
}

export function listParentEnquiries() {
  return apiGet<{ items: ParentEnquiry[] }>('/api/parent-enquiries')
}

export function getParentEnquiry(id: string) {
  return apiGet<ParentEnquiry>(`/api/parent-enquiries/${encodeURIComponent(id)}`)
}

export function getEnquiryPolicy() {
  return apiGet<EnquiryPolicy>('/api/parent-enquiries/policy')
}

export function getEnquiryEligibility() {
  return apiGet<EnquiryEligibility>('/api/teacher/enquiry-eligibility')
}

export function listMyParentEnquiries() {
  return apiGet<{ items: TeacherEnquiryApplication[] }>('/api/teacher/parent-enquiries')
}

export function applyForParentEnquiry(
  id: string,
  body: { isTutor: boolean; acceptNoRefund: boolean; acceptCommission: boolean; policyVersion: string },
) {
  return apiPost<{ interestId: string; created: boolean; payment: AccessPayment }>(
    `/api/parent-enquiries/${encodeURIComponent(id)}/apply`,
    body,
  )
}

export function getParentContact(id: string) {
  return apiGet<{ parentPhone: string; parentName: string }>(`/api/parent-enquiries/${encodeURIComponent(id)}/contact`)
}

export type AvailabilityDay = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun'

export type AvailabilitySlot = {
  day: AvailabilityDay
  start: string // "HH:MM"
  end: string // "HH:MM"
}

export type Review = {
  id: string
  studentName: string
  rating: number
  comment: string
  dateISO: string
  city: string
}

export type TutorMode = 'offline' | 'online' | 'both'

export type Tutor = {
  id: string
  name: string
  slug: string
  photoUrl: string
  isVerified: boolean
  rating: number
  reviewCount: number
  subjects: string[]
  topSubjects: string[]
  experienceYears: number
  feeMin: number
  feeMax: number
  city: string
  locality: string
  distanceKm: number
  responseTimeMins: number
  boards: string[]
  classes: string[]
  gender: 'Male' | 'Female' | 'Other'
  mode: TutorMode
  availability: AvailabilitySlot[]
  qualifications: {
    tenthPercent?: number
    twelfthPercent?: number
    degrees: { name: string; college: string; year: number; grade: string }[]
    certifications: { name: string; issuer: string; year: number }[]
  }
  bio: string
  teachingStyle: string[]
  achievements: string[]
  gallery: string[]
  reviews: Review[]
}

export type TutorSummary = Pick<
  Tutor,
  | 'id'
  | 'name'
  | 'slug'
  | 'photoUrl'
  | 'isVerified'
  | 'rating'
  | 'reviewCount'
  | 'topSubjects'
  | 'experienceYears'
  | 'feeMin'
  | 'feeMax'
  | 'city'
  | 'locality'
  | 'distanceKm'
  | 'responseTimeMins'
  | 'mode'
  | 'boards'
> & {
  subjects: string[]
}

export type Paginated<T> = {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export type Enquiry = {
  id: string
  tutorId: string
  tutorName: string
  subject: string
  createdAtISO: string
  status: 'Pending' | 'Responded' | 'Closed'
  message: string
}


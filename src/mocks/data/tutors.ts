import type { AvailabilitySlot, Tutor } from '../../domain/types'
import { tutorGallery, tutorPortraits } from '../../assets/stockImages'

const cities = [
  { city: 'Delhi', localities: ['Karol Bagh', 'Dwarka', 'Rohini', 'Saket'] },
  { city: 'Noida', localities: ['Sector 62', 'Sector 18', 'Sector 76'] },
  { city: 'Gurgaon', localities: ['DLF Phase 3', 'Sector 45', 'Sohna Road'] },
  { city: 'Ghaziabad', localities: ['Indirapuram', 'Vaishali'] },
  { city: 'Faridabad', localities: ['Sector 15', 'NIT'] },
  { city: 'Mumbai', localities: ['Andheri', 'Powai', 'Bandra'] },
  { city: 'Pune', localities: ['Hinjewadi', 'Baner', 'Kothrud'] },
  { city: 'Bengaluru', localities: ['Whitefield', 'Indiranagar', 'HSR Layout'] },
  { city: 'Hyderabad', localities: ['Gachibowli', 'Madhapur', 'Kondapur'] },
  { city: 'Kolkata', localities: ['Salt Lake', 'New Town', 'Ballygunge'] },
]

export const subjects = [
  'Maths',
  'Science',
  'English',
  'Hindi',
  'Physics',
  'Chemistry',
  'Biology',
  'Computer Science',
  'Sanskrit',
  'French',
  'Guitar',
  'Piano',
]

export const boards = ['CBSE', 'ICSE', 'IB', 'State Board']
export const classes = [
  'Class 1',
  'Class 2',
  'Class 3',
  'Class 4',
  'Class 5',
  'Class 6',
  'Class 7',
  'Class 8',
  'Class 9',
  'Class 10',
  'Class 11',
  'Class 12',
]

const maleNames = ['Aarav', 'Vihaan', 'Arjun', 'Kabir', 'Rohan', 'Aditya', 'Ishaan', 'Manav']
const femaleNames = ['Aanya', 'Diya', 'Ira', 'Anika', 'Sara', 'Meera', 'Kiara', 'Naina']
const lastNames = ['Sharma', 'Verma', 'Gupta', 'Iyer', 'Khan', 'Singh', 'Roy', 'Nair']

function pick<T>(arr: T[]) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function pickMany<T>(arr: T[], count: number) {
  const copy = [...arr]
  const out: T[] = []
  while (out.length < count && copy.length) {
    out.push(copy.splice(Math.floor(Math.random() * copy.length), 1)[0]!)
  }
  return out
}

function slugify(s: string) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

function makeAvailability(): AvailabilitySlot[] {
  const days: AvailabilitySlot['day'][] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const slots: AvailabilitySlot[] = []
  for (const day of days) {
    if (Math.random() < 0.35) continue
    const startHour = 7 + Math.floor(Math.random() * 10) // 7..16
    const start = `${String(startHour).padStart(2, '0')}:00`
    const end = `${String(startHour + 2).padStart(2, '0')}:00`
    slots.push({ day, start, end })
    if (Math.random() < 0.3) {
      const s2 = startHour + 3
      slots.push({ day, start: `${String(s2).padStart(2, '0')}:00`, end: `${String(s2 + 2).padStart(2, '0')}:00` })
    }
  }
  return slots
}

function makePhotoUrlByIndex(index: number) {
  return tutorPortraits[index % tutorPortraits.length]!
}

function makeGalleryByIndex(index: number) {
  const start = index % tutorGallery.length
  return Array.from({ length: 5 }).map((_, i) => tutorGallery[(start + i) % tutorGallery.length]!)
}

function makeReviews(city: string) {
  const count = 6 + Math.floor(Math.random() * 8)
  return Array.from({ length: count }).map((_, i) => {
    const rating = Math.round((3.5 + Math.random() * 1.5) * 10) / 10
    return {
      id: crypto.randomUUID(),
      studentName: `${pick(femaleNames)} ${pick(lastNames).slice(0, 1)}.`,
      rating,
      comment:
        rating > 4.4
          ? 'Very clear explanations and friendly teaching style.'
          : 'Good tutor, helped improve my understanding.',
      dateISO: new Date(Date.now() - (i + 1) * 86400000 * (2 + Math.floor(Math.random() * 10))).toISOString(),
      city,
    }
  })
}

export const tutors: Tutor[] = Array.from({ length: 60 }).map((_, idx) => {
  const id = (1000 + idx).toString(16) + crypto.randomUUID().slice(0, 8)
  const genderPool: Tutor['gender'][] = ['Male', 'Female', 'Other']
  const gender = pick(genderPool)
  const firstName = gender === 'Female' ? pick(femaleNames) : pick(maleNames)
  const lastName = pick(lastNames)
  const name = `${firstName} ${lastName}`

  const cityEntry = pick(cities)
  const city = cityEntry.city
  const locality = pick(cityEntry.localities)

  const subs = pickMany(subjects, 3 + Math.floor(Math.random() * 4))
  const topSubjects = subs.slice(0, 3)
  const experienceYears = Math.floor(Math.random() * 16)
  const feeMin = 200 + Math.floor(Math.random() * 900)
  const feeMax = feeMin + 200 + Math.floor(Math.random() * 700)

  const rating = Math.round((3.5 + Math.random() * 1.5) * 10) / 10
  const reviewCount = 8 + Math.floor(Math.random() * 90)
  const isVerified = Math.random() < 0.55
  const distanceKm = Math.round((2 + Math.random() * 28) * 10) / 10
  const responseTimeMins = 20 + Math.floor(Math.random() * 240)
  const mode: Tutor['mode'] = pick(['offline', 'online', 'both'])

  const b = pickMany(boards, 1 + Math.floor(Math.random() * 3))
  const c = pickMany(classes, 2 + Math.floor(Math.random() * 6))

  return {
    id,
    name,
    slug: slugify(`${name}-${city}-${topSubjects[0] ?? 'tutor'}`),
    photoUrl: makePhotoUrlByIndex(idx),
    isVerified,
    rating,
    reviewCount,
    subjects: subs,
    topSubjects,
    experienceYears,
    feeMin,
    feeMax,
    city,
    locality,
    distanceKm,
    responseTimeMins,
    boards: b,
    classes: c,
    gender,
    mode,
    availability: makeAvailability(),
    qualifications: {
      tenthPercent: 70 + Math.floor(Math.random() * 25),
      twelfthPercent: 65 + Math.floor(Math.random() * 30),
      degrees: [
        {
          name: Math.random() < 0.5 ? 'B.Sc' : 'B.Tech',
          college: 'State University',
          year: 2012 + Math.floor(Math.random() * 12),
          grade: `${70 + Math.floor(Math.random() * 25)}%`,
        },
      ],
      certifications: [
        { name: 'Teaching Certificate', issuer: 'GharKaGuru Academy', year: 2018 + Math.floor(Math.random() * 7) },
      ],
    },
    bio:
      'I focus on concepts first, then practice with targeted examples and past papers. I adapt pace to the student and provide regular feedback.',
    teachingStyle: ['Concept-first explanations', 'Weekly practice plan', 'Regular assessments'],
    achievements: ['Improved student scores within 8 weeks', 'Strong track record with board exams', 'Patient and friendly'],
    gallery: makeGalleryByIndex(idx),
    reviews: makeReviews(city),
  }
})


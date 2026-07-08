import { Helmet } from 'react-helmet-async'
import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { getTutors } from '../api/tutors'
import { subjects } from '../mocks/data/tutors'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { TutorCard } from '../components/tutors/TutorCard'
import { Skeleton } from '../components/ui/Skeleton'
import { trackEvent } from '../lib/analytics'
import { useToast } from '../components/ui/toast/useToast'
import { writeJson, readJson } from '../lib/storage'
import { heroImages } from '../assets/stockImages'
import { CategoryStrip } from '../components/home/CategoryStrip'
import { PromoGrid } from '../components/home/PromoGrid'
import { useAppForm } from '../lib/forms'
import { LeadEnquiryModal } from '../features/enquiry/LeadEnquiryModal'

export function HomePage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [testimonialIdx, setTestimonialIdx] = useState(0)
  const [leadEnquiryOpen, setLeadEnquiryOpen] = useState(false)

  const testimonials = useMemo(
    () => [
      { name: 'Riya S.', city: 'Delhi', rating: 5, comment: 'Found an amazing maths tutor within a day. Super smooth!' },
      { name: 'Arjun K.', city: 'Mumbai', rating: 5, comment: 'Shortlisting made it easy to compare tutors and choose.' },
      { name: 'Meera P.', city: 'Bengaluru', rating: 4.5, comment: 'Great experience. The enquiry flow is quick and clear.' },
      { name: 'Kabir V.', city: 'Pune', rating: 4.8, comment: 'Helped my sister prepare for boards with confidence.' },
      { name: 'Ira N.', city: 'Hyderabad', rating: 4.7, comment: 'Loved the availability view — scheduling felt effortless.' },
      { name: 'Rohan G.', city: 'Kolkata', rating: 4.9, comment: 'Verified badges are reassuring. Solid set of options.' },
    ],
    [],
  )

  useEffect(() => {
    const t = window.setInterval(() => setTestimonialIdx((i) => (i + 1) % testimonials.length), 6000)
    return () => window.clearInterval(t)
  }, [testimonials.length])

  const schema = z.object({
    location: z.string().min(1, 'Location is required'),
    subject: z.string().min(1, 'Subject is required'),
  })

  const last = readJson<{ location: string; subject: string } | null>('tn_last_search', null)

  const form = useAppForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      location: last?.location ?? '',
      subject: last?.subject ?? '',
    },
  })

  const featured = useQuery({
    queryKey: ['featured-tutors'],
    queryFn: () => getTutors({ page: 1, pageSize: 6, sort: 'rating' }),
  })

  return (
    <>
      <Helmet>
        <title>GharKaGuru | Home Tuition & Online Tutors Near You</title>
        <meta
          name="description"
          content="Find verified home and online tutors near you. Search by subject and location, shortlist tutors, and book a demo class."
        />
      </Helmet>

      <section className="relative overflow-hidden rounded-2xl border border-tn-border bg-white shadow-soft">
        <div className="absolute inset-0">
          <img
            src={heroImages[0]}
            alt="Students studying"
            className="h-full w-full object-cover"
            loading="eager"
            decoding="async"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-white via-white/90 to-white/40" />
        </div>

        <div className="relative p-8">
        <h1 className="text-3xl font-semibold tracking-tight md:text-[40px]">
          Find Top Home Tutors Near You
        </h1>
        <p className="mt-3 max-w-2xl text-tn-muted">
          Verified tutors for CBSE, ICSE, IB, Languages, and more. Book a demo class in minutes.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Button type="button" size="lg" onClick={() => setLeadEnquiryOpen(true)}>
            Find Tutors
          </Button>
          <Link to="/teacher/register" className="inline-flex">
            <Button
              type="button"
              variant="secondary"
              size="lg"
              className="border-transparent bg-gradient-to-r from-tn-primary to-tn-primaryDark text-white shadow-soft hover:brightness-105"
            >
              Become a Tutor
            </Button>
          </Link>
        </div>
        </div>
      </section>

      <PromoGrid />
      <CategoryStrip />

      <section className="mt-10 rounded-2xl border border-tn-border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Search Tutors</h2>
        <form
          className="mt-4 grid gap-3 md:grid-cols-[1fr_240px_160px]"
          onSubmit={form.handleSubmit((values) => {
            writeJson('tn_last_search', values)
            trackEvent('search_submitted', values)
            const qs = new URLSearchParams({ location: values.location, subject: values.subject })
            navigate(`/search?${qs.toString()}`)
          })}
        >
          <div>
            <label className="text-sm font-medium">Location</label>
            <Input
              className="mt-1"
              placeholder="Enter city or area (e.g., Delhi, Karol Bagh)"
              {...form.register('location')}
              error={!!form.formState.errors.location}
            />
            {form.formState.errors.location ? (
              <p className="mt-1 text-sm text-tn-error">{form.formState.errors.location.message}</p>
            ) : null}
          </div>

          <div>
            <label className="text-sm font-medium">Subject</label>
            <select
              className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm text-tn-text focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2"
              {...form.register('subject')}
            >
              <option value="">Select a subject</option>
              {subjects.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            {form.formState.errors.subject ? (
              <p className="mt-1 text-sm text-tn-error">{form.formState.errors.subject.message}</p>
            ) : null}
          </div>

          <div className="flex items-end gap-2">
            <Button type="submit" size="lg" className="w-full">
              Search Tutors
            </Button>
          </div>
        </form>

        <div className="mt-3">
          <button
            type="button"
            className="text-sm text-tn-primary hover:underline"
            onClick={() => toast.warning('Location permission required')}
          >
            Use my location
          </button>
        </div>
      </section>

      <section className="mt-10">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Featured Tutors</h2>
          <Link to="/search" className="text-sm font-medium text-tn-primary hover:underline">
            View All Tutors
          </Link>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {featured.isLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="rounded-2xl border border-tn-border bg-white p-4">
                <Skeleton className="h-40 w-full rounded-xl" />
                <Skeleton className="mt-3 h-4 w-1/2" />
                <Skeleton className="mt-2 h-4 w-2/3" />
                <Skeleton className="mt-4 h-10 w-44" />
              </div>
            ))
          ) : (
            featured.data?.items.slice(0, 6).map((t) => <TutorCard key={t.id} tutor={t} view="grid" />)
          )}
        </div>
      </section>

      <section className="mt-10 rounded-2xl border border-tn-border bg-white p-6">
        <h2 className="text-xl font-semibold">How it works</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-sm font-medium">1) Search tutors</div>
            <div className="mt-1 text-sm text-tn-muted">Use filters to find the best match.</div>
          </div>
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-sm font-medium">2) Contact & share needs</div>
            <div className="mt-1 text-sm text-tn-muted">Send an enquiry with preferred timing.</div>
          </div>
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-sm font-medium">3) Start learning</div>
            <div className="mt-1 text-sm text-tn-muted">Schedule a demo and begin classes.</div>
          </div>
        </div>
      </section>

      <section className="mt-10 rounded-2xl border border-tn-border bg-white p-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Testimonials</h2>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setTestimonialIdx((i) => (i - 1 + testimonials.length) % testimonials.length)}
              aria-label="Previous testimonial"
            >
              Prev
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setTestimonialIdx((i) => (i + 1) % testimonials.length)}
              aria-label="Next testimonial"
            >
              Next
            </Button>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-tn-border bg-tn-bg p-5">
          <div className="text-sm font-medium">
            {testimonials[testimonialIdx]!.name} • {testimonials[testimonialIdx]!.city}
          </div>
          <div className="mt-1 text-sm text-tn-muted">Rating: {testimonials[testimonialIdx]!.rating}/5</div>
          <p className="mt-3 text-tn-text">{testimonials[testimonialIdx]!.comment}</p>
        </div>
      </section>

      <section className="mt-10 rounded-2xl border border-tn-border bg-white p-6">
        <h2 className="text-xl font-semibold">GharKaGuru in numbers</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-2xl font-semibold">100,000+</div>
            <div className="mt-1 text-sm text-tn-muted">Students Connected</div>
          </div>
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-2xl font-semibold">25,000+</div>
            <div className="mt-1 text-sm text-tn-muted">Tutors</div>
          </div>
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-2xl font-semibold">4.8/5</div>
            <div className="mt-1 text-sm text-tn-muted">Average Rating</div>
          </div>
        </div>
      </section>

      <LeadEnquiryModal open={leadEnquiryOpen} onOpenChange={setLeadEnquiryOpen} />
    </>
  )
}


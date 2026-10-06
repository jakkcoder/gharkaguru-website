import { useEffect, useState } from 'react'
import { Helmet } from 'react-helmet-async'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Textarea } from '../../components/ui/Textarea'
import { Spinner } from '../../components/ui/Spinner'
import { useToast } from '../../components/ui/toast/useToast'
import { clearTeacherDraft, readTeacherDraft, writeTeacherDraft } from '../../features/teacherRegister/draft'
import { submitTeacherRegistration } from '../../api/teacher'
import { ApiError } from '../../api/http'
import { trackEvent } from '../../lib/analytics'
import { useAppForm } from '../../lib/forms'

// Accept "+91 98765 43210" and similar, keeping the 10-digit mobile number.
function toMobile(raw: string) {
  const digits = raw.replace(/\D/g, '')
  return digits.length === 12 && digits.startsWith('91') ? digits.slice(2) : digits
}

const schema = z.object({
  phone: z
    .string()
    .transform(toMobile)
    .pipe(z.string().regex(/^[6-9]\d{9}$/, 'Enter a valid 10-digit mobile number')),
  fullName: z.string().min(2, 'Full name is required'),
  location: z.string().min(8, 'Enter area and city'),
  pin: z.string().regex(/^\d{6}$/, 'PIN must be 6 digits'),
  subject: z.string().min(1, 'Subjects are required'),
  classCanTeach: z.string().min(1, 'Classes are required'),
  education: z.string().min(1, 'Education is required'),
  medium: z.enum(['English', 'Hindi', 'Both']),
  teachingMode: z.enum(['Home', 'Online', 'Both']),
})

type FormValues = z.infer<typeof schema>

const emptyValues: FormValues = {
  phone: '',
  fullName: '',
  location: '',
  pin: '',
  subject: '',
  classCanTeach: '',
  education: '',
  medium: 'Both',
  teachingMode: 'Both',
}

export function TeacherRegisterPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [submittedPhone, setSubmittedPhone] = useState<string | null>(null)

  const form = useAppForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: emptyValues,
  })

  useEffect(() => {
    const draft = readTeacherDraft()
    if (!draft?.values) return
    form.reset({ ...emptyValues, ...(draft.values as Partial<FormValues>) })
  }, [form])

  const saveDraft = (values: FormValues) => {
    writeTeacherDraft({ step: 0, phoneVerified: false, path: 'wizard', values })
  }

  const onSubmit = form.handleSubmit(async (values) => {
    setSubmitting(true)
    try {
      const fd = new FormData()
      fd.set('phone', values.phone)
      fd.set('fullName', values.fullName.trim())
      fd.set('location', values.location.trim())
      fd.set('pin', values.pin.trim())
      fd.set('subject', values.subject.trim())
      fd.set('classCanTeach', values.classCanTeach.trim())
      fd.set('education', values.education.trim())
      fd.set('medium', values.medium)
      fd.set('teachingMode', values.teachingMode)
      await submitTeacherRegistration(fd)
      clearTeacherDraft()
      setSubmittedPhone(values.phone)
      trackEvent('teacher_registration_submitted', { phone: values.phone })
      toast.success('Application submitted')
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Could not submit the application'
      toast.error('Submit failed', message)
    } finally {
      setSubmitting(false)
    }
  })

  return (
    <>
      <Helmet>
        <title>Become a Tutor | GharKaGuru</title>
        <meta name="description" content="Register as a home or online tutor with GharKaGuru." />
      </Helmet>

      <h1 className="text-2xl font-semibold">Become a Home Tutor</h1>
      <p className="mt-2 text-tn-muted">Share your mobile number and tell us where and what you teach.</p>

      {submittedPhone ? (
        <div className="mt-6 rounded-2xl border border-tn-border bg-white p-8">
          <h2 className="text-xl font-semibold">Thanks, your details are with us. Our team will call you on {submittedPhone}.</h2>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button onClick={() => navigate('/parent-enquiries')}>See parent enquiries</Button>
            <Button variant="secondary" onClick={() => navigate('/')}>
              Back to home
            </Button>
          </div>
        </div>
      ) : (
        <form className="mt-6 space-y-4 rounded-2xl border border-tn-border bg-white p-6" onSubmit={onSubmit}>
          <div>
            <label className="text-sm font-medium" htmlFor="tutor-phone">Mobile number</label>
            <Input
              id="tutor-phone"
              className="mt-1"
              type="tel"
              inputMode="numeric"
              autoComplete="tel-national"
              placeholder="10-digit mobile number"
              {...form.register('phone', { onBlur: () => saveDraft(form.getValues()) })}
              error={!!form.formState.errors.phone}
            />
            {form.formState.errors.phone ? <p className="mt-1 text-sm text-tn-error">{form.formState.errors.phone.message}</p> : null}
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="tutor-full-name">Full name</label>
            <Input id="tutor-full-name" className="mt-1" {...form.register('fullName')} error={!!form.formState.errors.fullName} />
            {form.formState.errors.fullName ? (
              <p className="mt-1 text-sm text-tn-error">{form.formState.errors.fullName.message}</p>
            ) : null}
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="tutor-address">Address</label>
            <Textarea id="tutor-address" className="mt-1" rows={3} {...form.register('location', { onBlur: () => saveDraft(form.getValues()) })} error={!!form.formState.errors.location} />
            {form.formState.errors.location ? (
              <p className="mt-1 text-sm text-tn-error">{form.formState.errors.location.message}</p>
            ) : null}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium" htmlFor="tutor-pin">PIN</label>
              <Input id="tutor-pin" className="mt-1" inputMode="numeric" {...form.register('pin')} error={!!form.formState.errors.pin} />
              {form.formState.errors.pin ? <p className="mt-1 text-sm text-tn-error">{form.formState.errors.pin.message}</p> : null}
            </div>
            <div>
              <label className="text-sm font-medium" htmlFor="tutor-mode">Home, online, or both</label>
              <select id="tutor-mode" className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm" {...form.register('teachingMode')}>
                <option>Home</option>
                <option>Online</option>
                <option>Both</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="tutor-subjects">Subjects</label>
            <Input id="tutor-subjects" className="mt-1" placeholder="Maths, Science" {...form.register('subject')} error={!!form.formState.errors.subject} />
            {form.formState.errors.subject ? <p className="mt-1 text-sm text-tn-error">{form.formState.errors.subject.message}</p> : null}
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="tutor-classes">Classes you can teach</label>
            <Input id="tutor-classes" className="mt-1" placeholder="6 to 10" {...form.register('classCanTeach')} error={!!form.formState.errors.classCanTeach} />
            {form.formState.errors.classCanTeach ? (
              <p className="mt-1 text-sm text-tn-error">{form.formState.errors.classCanTeach.message}</p>
            ) : null}
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="tutor-education">Education</label>
            <Input id="tutor-education" className="mt-1" {...form.register('education')} error={!!form.formState.errors.education} />
            {form.formState.errors.education ? <p className="mt-1 text-sm text-tn-error">{form.formState.errors.education.message}</p> : null}
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="tutor-medium">English or Hindi medium</label>
            <select id="tutor-medium" className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm" {...form.register('medium')}>
              <option>English</option>
              <option>Hindi</option>
              <option>Both</option>
            </select>
          </div>
          <Button type="submit" disabled={submitting}>
            {submitting ? <Spinner /> : 'Submit'}
          </Button>
        </form>
      )}
    </>
  )
}

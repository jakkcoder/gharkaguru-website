import { useEffect, useMemo, useRef, useState } from 'react'
import { Helmet } from 'react-helmet-async'
import { useFieldArray, type Resolver } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Textarea } from '../../components/ui/Textarea'
import { Spinner } from '../../components/ui/Spinner'
import { useToast } from '../../components/ui/toast/useToast'
import { subjects as subjectOptions, boards as boardOptions, classes as classOptions } from '../../mocks/data/tutors'
import { OtpPanel } from '../../features/auth/OtpPanel'
import { useAuth } from '../../features/auth/useAuth'
import { clearTeacherDraft, readTeacherDraft, writeTeacherDraft } from '../../features/teacherRegister/draft'
import { PhotoCropModal } from '../../features/teacherRegister/PhotoCropModal'
import { submitTeacherRegistration, upsertTeacherApplicationDraft } from '../../api/teacher'
import { ApiError } from '../../api/http'
import { trackEvent } from '../../lib/analytics'
import { useAppForm } from '../../lib/forms'

function dataUrlToBlob(dataUrl: string) {
  const m = dataUrl.match(/^data:(.+?);base64,(.*)$/)
  if (!m) throw new Error('Invalid data URL')
  const mime = m[1]!
  const b64 = m[2]!
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return new Blob([bytes], { type: mime })
}

const steps = [
  'Personal',
  'Qualifications',
  'Experience',
  'ID Verification',
  'Availability',
  'Review & Submit',
] as const

const asNumber = (v: unknown) => (typeof v === 'string' && v.trim() === '' ? NaN : Number(v))

const schema = z.object({
  fullName: z.string().min(2, 'Full name is required'),
  email: z.string().email('Invalid email'),
  gender: z.enum(['Male', 'Female', 'Other']),
  dob: z.string().min(1, 'DOB is required'),
  location: z.string().min(1, 'Location is required'),
  photoDataUrl: z.string().min(1, 'Photo is required'),
  feeMin: z.preprocess(asNumber, z.number().min(200).max(5000)),
  feeMax: z.preprocess(asNumber, z.number().min(200).max(5000)),

  tenthPercent: z.preprocess(asNumber, z.number().min(0).max(100)),
  twelfthPercent: z.preprocess(asNumber, z.number().min(0).max(100)),
  degrees: z
    .array(
      z.object({
        name: z.string().min(1),
        college: z.string().min(1),
        year: z.preprocess(asNumber, z.number().min(1950).max(new Date().getFullYear())),
        grade: z.string().min(1),
      }),
    )
    .min(1, 'Add at least 1 degree'),
  certifications: z.array(
    z.object({
      name: z.string().min(1),
      issuer: z.string().min(1),
      year: z.preprocess(asNumber, z.number().min(1950).max(new Date().getFullYear())),
    }),
  ),

  yearsTeaching: z.preprocess(asNumber, z.number().min(0).max(30)),
  subjectsTaught: z.array(z.string()).min(1, 'Select subjects taught'),
  boards: z.array(z.string()).min(1, 'Select at least 1 board'),
  classes: z.array(z.string()).min(1, 'Select at least 1 class'),
  studentsTaught: z.preprocess(asNumber, z.number().min(0).max(100000)),
  bio: z.string().min(1, 'Bio is required').max(500, 'Max 500 characters'),
  teachingMode: z.enum(['Offline', 'Online', 'Both']),

  idDocType: z.enum(['Aadhaar', 'PAN', 'Driving License']),
  consent: z.boolean().refine((v) => v === true, { message: 'Consent is required' }),

  availability: z
    .array(
      z.object({
        day: z.enum(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']),
        start: z.string().min(1),
        end: z.string().min(1),
      }),
    )
    .min(1, 'Add at least 1 availability slot'),
})

type FormValues = z.infer<typeof schema>

export function TeacherRegisterPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const auth = useAuth()

  const [resumePrompt, setResumePrompt] = useState<ReturnType<typeof readTeacherDraft> | null>(null)
  const [phoneVerified, setPhoneVerified] = useState(false)
  const [phone, setPhone] = useState<string | undefined>(undefined)
  const [path, setPath] = useState<'wizard' | 'assist' | null>(null)
  const [pendingAssist, setPendingAssist] = useState(false)
  const [step, setStep] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [referenceId, setReferenceId] = useState<string | null>(null)
  const saveTimer = useRef<number | null>(null)
  const serverDraftBootstrapped = useRef(false)
  const draftAuthFailedOnce = useRef(false)

  const [photoSrc, setPhotoSrc] = useState<string | null>(null)
  const [cropOpen, setCropOpen] = useState(false)

  const [idDocs, setIdDocs] = useState<File[]>([])
  const [certFiles, setCertFiles] = useState<File[]>([])
  const [idPreviews, setIdPreviews] = useState<Array<{ name: string; url?: string; type: string }>>([])
  const [certPreviews, setCertPreviews] = useState<Array<{ name: string; url?: string; type: string }>>([])

  const defaultValues: FormValues = useMemo(
    () => ({
      fullName: '',
      email: '',
      gender: 'Male',
      dob: '',
      location: '',
      photoDataUrl: '',
      feeMin: 200,
      feeMax: 5000,
      tenthPercent: 0,
      twelfthPercent: 0,
      degrees: [{ name: '', college: '', year: new Date().getFullYear(), grade: '' }],
      certifications: [],
      yearsTeaching: 0,
      subjectsTaught: [],
      boards: [],
      classes: [],
      studentsTaught: 0,
      bio: '',
      teachingMode: 'Both',
      idDocType: 'Aadhaar',
      consent: false,
      availability: [{ day: 'Mon', start: '18:00', end: '19:00' }],
    }),
    [],
  )

  const form = useAppForm<FormValues>({
    // Zod preprocess() inputs are typed as unknown; cast resolver for RHF compatibility.
    resolver: zodResolver(schema) as unknown as Resolver<FormValues>,
    defaultValues,
  })

  const degrees = useFieldArray({ control: form.control, name: 'degrees' })
  const certifications = useFieldArray({ control: form.control, name: 'certifications' })
  const availability = useFieldArray({ control: form.control, name: 'availability' })

  // Load draft
  useEffect(() => {
    const draft = readTeacherDraft()
    if (draft) setResumePrompt(draft)
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    setPendingAssist(params.get('assist') === '1')
  }, [location.search])

  // Ensure a server-side draft exists even if user doesn't change any fields yet
  useEffect(() => {
    if (!phoneVerified) return
    if (!phone) return
    if (serverDraftBootstrapped.current) return
    if (auth.role !== 'teacher' || !auth.token) return
    serverDraftBootstrapped.current = true
    void upsertTeacherApplicationDraft({
      contactPhone: phone,
      draftPath: path,
      draftStep: step,
      startedAtISO: new Date().toISOString(),
    }).catch((e) => {
      // If auth is missing/expired, tell user once so they can re-login.
      if (!draftAuthFailedOnce.current && e instanceof ApiError && e.status === 401) {
        draftAuthFailedOnce.current = true
        toast.error('Session expired', 'Please verify your phone again to continue.')
      }
    })
  }, [phoneVerified, phone, auth.role, auth.token, path, step, toast])

  useEffect(() => {
    if (pendingAssist && phoneVerified && !path) {
      setPath('assist')
    }
  }, [pendingAssist, phoneVerified, path])

  // Autosave draft
  useEffect(() => {
    const sub = form.watch((values) => {
      if (!phoneVerified || path !== 'wizard') return
      writeTeacherDraft({
        step,
        phoneVerified,
        phone,
        path,
        values: values as unknown as Record<string, unknown>,
      })

      // Also persist a lightweight draft to backend so CRM can see it.
      // Never send photoDataUrl (base64) to backend; uploads happen only on final submit.
      if (saveTimer.current) window.clearTimeout(saveTimer.current)
      saveTimer.current = window.setTimeout(() => {
        const rest = { ...(values as unknown as Record<string, unknown>) }
        delete rest.photoDataUrl
        void upsertTeacherApplicationDraft({
          ...rest,
          contactPhone: phone,
          draftPath: path,
          draftStep: step,
        }).catch((e) => {
          if (!draftAuthFailedOnce.current && e instanceof ApiError && e.status === 401) {
            draftAuthFailedOnce.current = true
            toast.error('Session expired', 'Please verify your phone again to continue.')
          }
        })
      }, 800)
    })
    return () => sub.unsubscribe()
  }, [form, phoneVerified, path, step, phone, toast])

  const validateCurrentStep = async () => {
    const fieldsByStep: Record<number, (keyof FormValues)[]> = {
      0: ['fullName', 'email', 'gender', 'dob', 'location', 'photoDataUrl', 'feeMin', 'feeMax'],
      1: ['tenthPercent', 'twelfthPercent', 'degrees', 'certifications'],
      2: ['yearsTeaching', 'subjectsTaught', 'boards', 'classes', 'studentsTaught', 'bio', 'teachingMode'],
      3: ['idDocType', 'consent'],
      4: ['availability', 'teachingMode'],
      5: [],
    }

    const ok = await form.trigger(fieldsByStep[step] ?? [])
    if (!ok) return false

    if (step === 3) {
      if (idDocs.length === 0) {
        toast.error('Upload required', 'Please upload at least 1 ID document.')
        return false
      }
      if (idDocs.length > 3) {
        toast.error('Too many files', 'Max 3 ID documents allowed.')
        return false
      }
    }

    if (step === 0) {
      const feeMin = form.getValues('feeMin')
      const feeMax = form.getValues('feeMax')
      if (feeMin > feeMax) {
        toast.error('Invalid fee range', 'Minimum fee must be <= maximum fee.')
        return false
      }
    }

    return true
  }

  const renderErrorSummary = () => {
    const entries = Object.entries(form.formState.errors)
    if (!entries.length) return null
    return (
      <div className="rounded-xl border border-tn-error/30 bg-tn-bg p-4 text-sm">
        <div className="font-medium text-tn-text">Please fix the highlighted fields</div>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-tn-muted">
          {entries.slice(0, 5).map(([k, v]) => (
            <li key={k}>
              {k}: {typeof (v as { message?: unknown } | undefined)?.message === 'string' ? (v as { message?: string }).message : 'Invalid'}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  return (
    <>
      <Helmet>
        <title>Become a Tutor | GharKaGuru</title>
        <meta name="description" content="Teacher registration wizard for GharKaGuru." />
      </Helmet>

      <h1 className="text-2xl font-semibold">Become a Home Tutor</h1>
      <p className="mt-2 text-tn-muted">
        Phone verification is required. Your application is autosaved after each step.
      </p>

      {resumePrompt && !phoneVerified && !path ? (
        <div className="mt-6 rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Resume your application?</h2>
          <p className="mt-2 text-sm text-tn-muted">We found a saved draft in this browser.</p>
          <div className="mt-4 flex gap-2">
            <Button
              type="button"
              onClick={() => {
                if (resumePrompt.values) form.reset(resumePrompt.values as unknown as FormValues)
                setStep(Math.max(0, resumePrompt.step ?? 0))
                setPhoneVerified(!!resumePrompt.phoneVerified)
                setPhone(resumePrompt.phone)
                setPath(resumePrompt.path ?? 'wizard')
                setResumePrompt(null)
                toast.info('Draft loaded')
              }}
            >
              Resume
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                clearTeacherDraft()
                setResumePrompt(null)
                toast.info('Draft cleared')
              }}
            >
              Start fresh
            </Button>
          </div>
        </div>
      ) : null}

      {!phoneVerified ? (
        <div className="mt-6">
          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <div className="text-sm font-medium">Step 0: Phone verification</div>
            <div className="mt-4">
              <OtpPanel
                role="teacher"
                onVerified={(token, role, phone) => {
                  setPhoneVerified(true)
                  setPhone(phone)
                  auth.login(token, role)
                  trackEvent('teacher_registration_started', { phone })
                  toast.success('Phone verified')

                  // Create a server-side draft early (even if user leaves immediately).
                  void upsertTeacherApplicationDraft({
                    contactPhone: phone,
                    draftPath: null,
                    draftStep: 0,
                    startedAtISO: new Date().toISOString(),
                  }).catch(() => {
                    // ignore
                  })
                }}
              />
            </div>
          </div>
        </div>
      ) : !path ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">Fill Form Myself</h2>
            <p className="mt-2 text-sm text-tn-muted">Complete the full wizard (recommended).</p>
            <div className="mt-4">
              <Button
                type="button"
                onClick={() => {
                  setPath('wizard')
                  writeTeacherDraft({ step: 0, phoneVerified: true, phone, path: 'wizard', values: form.getValues() })
                  void upsertTeacherApplicationDraft({
                    ...(form.getValues() as unknown as Record<string, unknown>),
                    contactPhone: phone,
                    draftPath: 'wizard',
                    draftStep: 0,
                  }).catch(() => {
                    // ignore
                  })
                }}
              >
                Start wizard
              </Button>
            </div>
          </div>
          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">Need Assistance</h2>
            <p className="mt-2 text-sm text-tn-muted">We’ll contact you and help complete registration.</p>
            <div className="mt-4">
              <Button type="button" variant="secondary" onClick={() => setPath('assist')}>
                Request assistance
              </Button>
            </div>
          </div>
        </div>
      ) : path === 'assist' ? (
        <AssistanceForm
          phone={phone ?? ''}
          onDone={(ref) => {
            if (ref) setReferenceId(ref)
            navigate('/teacher/dashboard')
          }}
        />
      ) : referenceId ? (
        <div className="mt-6 rounded-2xl border border-tn-border bg-white p-8">
          <h2 className="text-xl font-semibold">Application in processing. We’ll reach out soon.</h2>
          <p className="mt-2 text-tn-muted">Reference ID: {referenceId}</p>
          <div className="mt-6">
            <Button onClick={() => navigate('/teacher/dashboard')}>Go to Teacher Dashboard</Button>
          </div>
        </div>
      ) : (
        <div className="mt-6">
          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-sm font-medium">
                  Step {step + 1} of {steps.length}: {steps[step]}
                </div>
                <div className="mt-2 h-2 w-full rounded-full bg-tn-border md:w-[420px]">
                  <div
                    className="h-2 rounded-full bg-tn-primary"
                    style={{ width: `${Math.round(((step + 1) / steps.length) * 100)}%` }}
                  />
                </div>
              </div>
              <button
                type="button"
                className="text-sm text-tn-primary hover:underline"
                onClick={() => {
                  clearTeacherDraft()
                  toast.info('Draft cleared')
                }}
              >
                Clear draft
              </button>
            </div>

            <form className="mt-6 space-y-6" onSubmit={(e) => e.preventDefault()}>
              {renderErrorSummary()}
              {step === 0 ? (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium">Full name</label>
                      <Input className="mt-1" {...form.register('fullName')} error={!!form.formState.errors.fullName} />
                      {form.formState.errors.fullName ? (
                        <p className="mt-1 text-sm text-tn-error">{form.formState.errors.fullName.message}</p>
                      ) : null}
                    </div>
                    <div>
                      <label className="text-sm font-medium">Email</label>
                      <Input className="mt-1" {...form.register('email')} error={!!form.formState.errors.email} />
                      {form.formState.errors.email ? (
                        <p className="mt-1 text-sm text-tn-error">{form.formState.errors.email.message}</p>
                      ) : null}
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium">Gender</label>
                      <select
                        className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm"
                        {...form.register('gender')}
                      >
                        <option>Male</option>
                        <option>Female</option>
                        <option>Other</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-sm font-medium">DOB</label>
                      <Input className="mt-1" type="date" {...form.register('dob')} error={!!form.formState.errors.dob} />
                      {form.formState.errors.dob ? (
                        <p className="mt-1 text-sm text-tn-error">{form.formState.errors.dob.message}</p>
                      ) : null}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium">Location / address</label>
                    <Input className="mt-1" {...form.register('location')} error={!!form.formState.errors.location} />
                    {form.formState.errors.location ? (
                      <p className="mt-1 text-sm text-tn-error">{form.formState.errors.location.message}</p>
                    ) : null}
                    <div className="mt-2 text-xs text-tn-muted">Lat/long stub will be added later.</div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium">Photo (jpg/png, max 5MB)</label>
                      <input
                        className="mt-2 block w-full text-sm"
                        type="file"
                        accept="image/png,image/jpeg"
                        onChange={(e) => {
                          const f = e.target.files?.[0]
                          if (!f) return
                          if (f.size > 5 * 1024 * 1024) {
                            toast.error('File too large', 'Max 5MB.')
                            return
                          }
                          const url = URL.createObjectURL(f)
                          setPhotoSrc(url)
                          setCropOpen(true)
                        }}
                      />
                      {form.getValues('photoDataUrl') ? (
                        <img
                          src={form.getValues('photoDataUrl')}
                          alt="Cropped profile preview"
                          className="mt-3 h-24 w-24 rounded-full object-cover"
                        />
                      ) : null}
                      {form.formState.errors.photoDataUrl ? (
                        <p className="mt-1 text-sm text-tn-error">{form.formState.errors.photoDataUrl.message}</p>
                      ) : null}
                    </div>

                    <div>
                      <label className="text-sm font-medium">Hourly fee range (₹200–₹5000)</label>
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        <Input inputMode="numeric" {...form.register('feeMin')} />
                        <Input inputMode="numeric" {...form.register('feeMax')} />
                      </div>
                      <input
                        className="mt-3 w-full"
                        type="range"
                        min={200}
                        max={5000}
                        value={Number(form.watch('feeMin'))}
                        onChange={(e) => form.setValue('feeMin', Number(e.target.value))}
                        aria-label="Fee min"
                      />
                      <input
                        className="mt-2 w-full"
                        type="range"
                        min={200}
                        max={5000}
                        value={Number(form.watch('feeMax'))}
                        onChange={(e) => form.setValue('feeMax', Number(e.target.value))}
                        aria-label="Fee max"
                      />
                    </div>
                  </div>
                </div>
              ) : null}

              {step === 1 ? (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium">10th %</label>
                      <Input className="mt-1" inputMode="numeric" {...form.register('tenthPercent')} />
                    </div>
                    <div>
                      <label className="text-sm font-medium">12th %</label>
                      <Input className="mt-1" inputMode="numeric" {...form.register('twelfthPercent')} />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Degrees</label>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => degrees.append({ name: '', college: '', year: new Date().getFullYear(), grade: '' })}
                      >
                        Add degree
                      </Button>
                    </div>
                    <div className="mt-2 space-y-3">
                      {degrees.fields.map((f, idx) => (
                        <div key={f.id} className="rounded-xl border border-tn-border bg-white p-4">
                          <div className="grid gap-2 md:grid-cols-2">
                            <Input placeholder="Degree name" {...form.register(`degrees.${idx}.name`)} />
                            <Input placeholder="College" {...form.register(`degrees.${idx}.college`)} />
                            <Input placeholder="Year" inputMode="numeric" {...form.register(`degrees.${idx}.year`)} />
                            <Input placeholder="Grade/%" {...form.register(`degrees.${idx}.grade`)} />
                          </div>
                          <div className="mt-3">
                            <Button type="button" variant="ghost" onClick={() => degrees.remove(idx)}>
                              Remove
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                    {form.formState.errors.degrees ? (
                      <p className="mt-1 text-sm text-tn-error">{form.formState.errors.degrees.message as string}</p>
                    ) : null}
                  </div>

                  <div>
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Certifications</label>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => certifications.append({ name: '', issuer: '', year: new Date().getFullYear() })}
                      >
                        Add
                      </Button>
                    </div>
                    <div className="mt-2 space-y-3">
                      {certifications.fields.map((f, idx) => (
                        <div key={f.id} className="rounded-xl border border-tn-border bg-white p-4">
                          <div className="grid gap-2 md:grid-cols-3">
                            <Input placeholder="Name" {...form.register(`certifications.${idx}.name`)} />
                            <Input placeholder="Issuer" {...form.register(`certifications.${idx}.issuer`)} />
                            <Input placeholder="Year" inputMode="numeric" {...form.register(`certifications.${idx}.year`)} />
                          </div>
                          <div className="mt-3">
                            <Button type="button" variant="ghost" onClick={() => certifications.remove(idx)}>
                              Remove
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-3">
                      <label className="text-sm font-medium">Upload certifications (optional, jpg/png/pdf max 5MB)</label>
                      <input
                        className="mt-2 block w-full text-sm"
                        type="file"
                        multiple
                        accept="image/png,image/jpeg,application/pdf"
                        onChange={(e) => {
                          const files = Array.from(e.target.files ?? [])
                          const tooLarge = files.find((f) => f.size > 5 * 1024 * 1024)
                          if (tooLarge) return toast.error('File too large', 'Max 5MB per file.')
                          setCertFiles(files)
                          setCertPreviews((prev) => {
                            prev.forEach((p) => p.url && URL.revokeObjectURL(p.url))
                            return files.map((f) => ({
                              name: f.name,
                              type: f.type,
                              url: f.type.startsWith('image/') ? URL.createObjectURL(f) : undefined,
                            }))
                          })
                        }}
                      />
                      {certPreviews.length ? (
                        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
                          {certPreviews.map((p) => (
                            <div key={p.name} className="rounded-xl border border-tn-border bg-white p-2">
                              <div className="h-20 overflow-hidden rounded-lg border border-tn-border bg-tn-bg">
                                {p.url ? (
                                  <img src={p.url} alt={`${p.name} preview`} className="h-20 w-full object-cover" />
                                ) : (
                                  <div className="flex h-20 items-center justify-center text-xs text-tn-muted">
                                    {p.type.includes('pdf') ? 'PDF' : 'FILE'}
                                  </div>
                                )}
                              </div>
                              <div className="mt-2 line-clamp-2 text-xs text-tn-muted">{p.name}</div>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              ) : null}

              {step === 2 ? (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium">Years teaching</label>
                      <Input className="mt-1" inputMode="numeric" {...form.register('yearsTeaching')} />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Students taught</label>
                      <Input className="mt-1" inputMode="numeric" {...form.register('studentsTaught')} />
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium">Subjects taught</label>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      {subjectOptions.map((s) => (
                        <label key={s} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={form.watch('subjectsTaught').includes(s)}
                            onChange={() => {
                              const cur = form.getValues('subjectsTaught')
                              form.setValue(
                                'subjectsTaught',
                                cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s],
                                { shouldValidate: true },
                              )
                            }}
                          />
                          <span>{s}</span>
                        </label>
                      ))}
                    </div>
                    {form.formState.errors.subjectsTaught ? (
                      <p className="mt-1 text-sm text-tn-error">{form.formState.errors.subjectsTaught.message as string}</p>
                    ) : null}
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium">Boards</label>
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        {boardOptions.map((b) => (
                          <label key={b} className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={form.watch('boards').includes(b)}
                              onChange={() => {
                                const cur = form.getValues('boards')
                                form.setValue('boards', cur.includes(b) ? cur.filter((x) => x !== b) : [...cur, b], {
                                  shouldValidate: true,
                                })
                              }}
                            />
                            <span>{b}</span>
                          </label>
                        ))}
                      </div>
                      {form.formState.errors.boards ? (
                        <p className="mt-1 text-sm text-tn-error">{form.formState.errors.boards.message as string}</p>
                      ) : null}
                    </div>
                    <div>
                      <label className="text-sm font-medium">Classes</label>
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        {classOptions
                          .filter((c) => {
                            const m = c.match(/\d+/)
                            const n = m ? Number(m[0]) : NaN
                            return Number.isFinite(n) && n >= 5 && n <= 12
                          })
                          .map((c) => (
                          <label key={c} className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={form.watch('classes').includes(c)}
                              onChange={() => {
                                const cur = form.getValues('classes')
                                form.setValue('classes', cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c], {
                                  shouldValidate: true,
                                })
                              }}
                            />
                            <span>{c}</span>
                          </label>
                        ))}
                      </div>
                      {form.formState.errors.classes ? (
                        <p className="mt-1 text-sm text-tn-error">{form.formState.errors.classes.message as string}</p>
                      ) : null}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium">Bio (max 500)</label>
                    <Textarea className="mt-1" rows={5} {...form.register('bio')} />
                    <div className="mt-1 text-right text-xs text-tn-muted">{form.watch('bio').length}/500</div>
                    {form.formState.errors.bio ? (
                      <p className="mt-1 text-sm text-tn-error">{form.formState.errors.bio.message}</p>
                    ) : null}
                  </div>

                  <div>
                    <label className="text-sm font-medium">Teaching mode</label>
                    <select
                      className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm"
                      {...form.register('teachingMode')}
                    >
                      <option>Offline</option>
                      <option>Online</option>
                      <option>Both</option>
                    </select>
                  </div>
                </div>
              ) : null}

              {step === 3 ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">Document type</label>
                    <select
                      className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm"
                      {...form.register('idDocType')}
                    >
                      <option>Aadhaar</option>
                      <option>PAN</option>
                      <option>Driving License</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-sm font-medium">Upload ID documents (jpg/png/pdf, max 5MB, up to 3)</label>
                    <input
                      className="mt-2 block w-full text-sm"
                      type="file"
                      multiple
                      accept="image/png,image/jpeg,application/pdf"
                      onChange={(e) => {
                        const files = Array.from(e.target.files ?? [])
                        const tooLarge = files.find((f) => f.size > 5 * 1024 * 1024)
                        if (tooLarge) return toast.error('File too large', 'Max 5MB per file.')
                        setIdDocs(files.slice(0, 3))
                        setIdPreviews((prev) => {
                          prev.forEach((p) => p.url && URL.revokeObjectURL(p.url))
                          return files.slice(0, 3).map((f) => ({
                            name: f.name,
                            type: f.type,
                            url: f.type.startsWith('image/') ? URL.createObjectURL(f) : undefined,
                          }))
                        })
                      }}
                    />
                    {idPreviews.length ? (
                      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
                        {idPreviews.map((p) => (
                          <div key={p.name} className="rounded-xl border border-tn-border bg-white p-2">
                            <div className="h-20 overflow-hidden rounded-lg border border-tn-border bg-tn-bg">
                              {p.url ? (
                                <img src={p.url} alt={`${p.name} preview`} className="h-20 w-full object-cover" />
                              ) : (
                                <div className="flex h-20 items-center justify-center text-xs text-tn-muted">
                                  {p.type.includes('pdf') ? 'PDF' : 'FILE'}
                                </div>
                              )}
                            </div>
                            <div className="mt-2 line-clamp-2 text-xs text-tn-muted">{p.name}</div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <label className="flex items-start gap-2 text-sm">
                    <input type="checkbox" {...form.register('consent')} />
                    <span>I consent to GharKaGuru verifying my identity documents for onboarding.</span>
                  </label>
                  {form.formState.errors.consent ? (
                    <p className="text-sm text-tn-error">{form.formState.errors.consent.message}</p>
                  ) : null}
                </div>
              ) : null}

              {step === 4 ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium">Weekly schedule</label>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => availability.append({ day: 'Sat', start: '10:00', end: '11:00' })}
                    >
                      Add slot
                    </Button>
                  </div>
                  <div className="space-y-3">
                    {availability.fields.map((f, idx) => (
                      <div key={f.id} className="grid gap-2 rounded-xl border border-tn-border bg-white p-4 md:grid-cols-[120px_1fr_1fr_auto]">
                        <select
                          className="h-10 rounded-md border border-tn-border bg-white px-3 text-sm"
                          {...form.register(`availability.${idx}.day`)}
                        >
                          <option>Mon</option>
                          <option>Tue</option>
                          <option>Wed</option>
                          <option>Thu</option>
                          <option>Fri</option>
                          <option>Sat</option>
                          <option>Sun</option>
                        </select>
                        <Input type="time" {...form.register(`availability.${idx}.start`)} />
                        <Input type="time" {...form.register(`availability.${idx}.end`)} />
                        <Button type="button" variant="ghost" onClick={() => availability.remove(idx)}>
                          Remove
                        </Button>
                      </div>
                    ))}
                  </div>
                  {form.formState.errors.availability ? (
                    <p className="text-sm text-tn-error">{form.formState.errors.availability.message as string}</p>
                  ) : null}
                </div>
              ) : null}

              {step === 5 ? (
                <div className="space-y-4">
                  <div className="rounded-xl border border-tn-border bg-tn-bg p-4 text-sm">
                    <div className="font-medium">Review</div>
                    <div className="mt-2 text-tn-muted">
                      Please review your details. You can go back to edit any section.
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-xl border border-tn-border bg-white p-4">
                      <div className="text-sm font-medium">Personal</div>
                      <div className="mt-2 text-sm text-tn-muted">
                        {form.getValues('fullName')} • {form.getValues('email')}
                      </div>
                      <div className="mt-1 text-sm text-tn-muted">{form.getValues('location')}</div>
                    </div>
                    <div className="rounded-xl border border-tn-border bg-white p-4">
                      <div className="text-sm font-medium">Experience</div>
                      <div className="mt-2 text-sm text-tn-muted">
                        {form.getValues('yearsTeaching')} yrs • {form.getValues('teachingMode')}
                      </div>
                      <div className="mt-1 text-sm text-tn-muted">
                        Subjects: {form.getValues('subjectsTaught').slice(0, 3).join(', ')}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="flex flex-col gap-2 sm:flex-row sm:justify-between">
                <Button type="button" variant="secondary" disabled={step === 0} onClick={() => setStep((s) => Math.max(0, s - 1))}>
                  Back
                </Button>

                {step < steps.length - 1 ? (
                  <Button
                    type="button"
                    onClick={async () => {
                      const ok = await validateCurrentStep()
                      if (!ok) return toast.error('Please fix errors before continuing')
                      setStep((s) => Math.min(steps.length - 1, s + 1))
                    }}
                  >
                    Continue
                  </Button>
                ) : (
                  <Button
                    type="button"
                    disabled={submitting}
                    onClick={async () => {
                      const ok = await validateCurrentStep()
                      if (!ok) return toast.error('Please fix errors before submitting')
                      setSubmitting(true)
                      try {
                        trackEvent('teacher_registration_submitted', { phone })
                        const v = form.getValues()
                        const fd = new FormData()
                        fd.set('fullName', v.fullName)
                        fd.set('email', v.email)
                        fd.set('gender', v.gender)
                        fd.set('dob', v.dob)
                        fd.set('location', v.location)
                        fd.set('feeMin', String(v.feeMin))
                        fd.set('feeMax', String(v.feeMax))

                        // photoDataUrl -> file
                        const photoBlob = dataUrlToBlob(v.photoDataUrl)
                        fd.set('photo', new File([photoBlob], 'photo.png', { type: photoBlob.type || 'image/png' }))

                        fd.set('tenthPercent', String(v.tenthPercent))
                        fd.set('twelfthPercent', String(v.twelfthPercent))
                        fd.set('degrees', JSON.stringify(v.degrees))
                        fd.set('certifications', JSON.stringify(v.certifications ?? []))

                        fd.set('yearsTeaching', String(v.yearsTeaching))
                        fd.set('subjectsTaught', JSON.stringify(v.subjectsTaught))
                        fd.set('boards', JSON.stringify(v.boards))
                        fd.set('classes', JSON.stringify(v.classes))
                        fd.set('studentsTaught', String(v.studentsTaught))
                        fd.set('bio', v.bio)
                        fd.set('teachingMode', String(v.teachingMode).toLowerCase())

                        fd.set('idDocType', v.idDocType)
                        fd.set('consent', String(Boolean(v.consent)))
                        for (const f of idDocs) fd.append('idDocs', f)
                        for (const f of certFiles) fd.append('certFiles', f)

                        fd.set('availability', JSON.stringify(v.availability))

                        const idem = crypto.randomUUID()
                        const res = await submitTeacherRegistration(fd, idem)
                        setReferenceId(res.referenceId)
                        clearTeacherDraft()
                        toast.success('Application submitted')
                      } catch (e) {
                        if (e instanceof ApiError) {
                          const details = e.details as Record<string, unknown> | undefined
                          const field = typeof details?.field === 'string' ? details.field : null
                          const reason = typeof details?.reason === 'string' ? details.reason : null
                          const issues = Array.isArray(details?.issues) ? (details?.issues as Array<{ path?: string[]; message?: string }>) : []
                          const issueText = issues[0]?.message
                          const issuePath = Array.isArray(issues[0]?.path) ? issues[0]?.path?.join('.') : null
                          const extra = field
                            ? `${field}${reason ? ` (${reason})` : ''}`
                            : issuePath
                              ? `${issuePath}: ${issueText ?? ''}`.trim()
                              : issueText
                          toast.error('Submit failed', extra ? `${e.message} • ${extra}` : e.message)
                        } else {
                          toast.error('Submit failed')
                        }
                      } finally {
                        setSubmitting(false)
                      }
                    }}
                  >
                    {submitting ? <Spinner className="border-t-white" /> : null}
                    Submit Application
                  </Button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

      {photoSrc ? (
        <PhotoCropModal
          open={cropOpen}
          onOpenChange={setCropOpen}
          imageSrc={photoSrc}
          onCropped={(dataUrl) => {
            form.setValue('photoDataUrl', dataUrl, { shouldValidate: true })
          }}
        />
      ) : null}
    </>
  )
}

function AssistanceForm({ phone, onDone }: { phone: string; onDone: (referenceId?: string) => void }) {
  const toast = useToast()
  const [name, setName] = useState('')
  const [location, setLocation] = useState('')
  const [subjects, setSubjects] = useState<string[]>([])
  const [callMe, setCallMe] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  return (
    <div className="mt-6 rounded-2xl border border-tn-border bg-white p-6">
      <h2 className="text-lg font-semibold">Request assistance</h2>
      <p className="mt-2 text-sm text-tn-muted">A customer representative will reach out to help you complete registration.</p>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Name</label>
          <Input className="mt-1" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="text-sm font-medium">Phone (verified)</label>
          <Input className="mt-1" value={phone} readOnly />
        </div>
      </div>

      <div className="mt-3">
        <label className="text-sm font-medium">Location</label>
        <Input className="mt-1" value={location} onChange={(e) => setLocation(e.target.value)} />
      </div>

      <div className="mt-3">
        <label className="text-sm font-medium">Subjects</label>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {subjectOptions.map((s) => (
            <label key={s} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={subjects.includes(s)}
                onChange={() => setSubjects((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]))}
              />
              <span>{s}</span>
            </label>
          ))}
        </div>
      </div>

      <label className="mt-4 flex items-start gap-2 text-sm">
        <input type="checkbox" checked={callMe} onChange={(e) => setCallMe(e.target.checked)} />
        <span>Call me for help</span>
      </label>

      <div className="mt-6">
        <Button
          disabled={submitting}
          onClick={async () => {
            if (!name.trim() || !location.trim() || subjects.length === 0) {
              toast.error('Please fill all required fields')
              return
            }
            setSubmitting(true)
            try {
              const out = await upsertTeacherApplicationDraft({
                contactPhone: phone,
                draftPath: 'assist',
                draftStep: 0,
                assistanceRequested: true,
                assistanceName: name.trim(),
                assistanceLocation: location.trim(),
                assistanceSubjects: subjects,
                assistanceCallMe: callMe,
                startedAtISO: new Date().toISOString(),
              })
              toast.success('We will contact you shortly', `Reference ID: ${out.referenceId}`)
              onDone(out.referenceId)
            } finally {
              setSubmitting(false)
            }
          }}
        >
          {submitting ? <Spinner className="border-t-white" /> : null}
          Submit
        </Button>
      </div>
    </div>
  )
}


import { Helmet } from 'react-helmet-async'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { useAuth } from '../../features/auth/useAuth'
import { getTeacherApplication } from '../../api/teacher'
import { getEnquiryEligibility, listMyParentEnquiries, parentPhoneForDisplay } from '../../api/parentEnquiries'

export function TeacherDashboardPage() {
  const auth = useAuth()
  const q = useQuery({
    queryKey: ['teacher-application'],
    queryFn: async () => getTeacherApplication(),
    enabled: Boolean(auth.token),
  })

  const completion = q.data?.profileCompletionPercent ?? 0
  const status = q.data?.status ?? 'NotStarted'
  const applications = useQuery({
    queryKey: ['my-parent-enquiries'],
    queryFn: listMyParentEnquiries,
    enabled: Boolean(auth.token) && auth.role === 'teacher',
  })
  const eligibility = useQuery({
    queryKey: ['enquiry-eligibility'],
    queryFn: getEnquiryEligibility,
    enabled: Boolean(auth.token) && auth.role === 'teacher',
  })
  const alreadyRegistered = Boolean(eligibility.data?.registered)
  const statusLabel = alreadyRegistered && status === 'NotStarted' ? 'Registered' : status

  return (
    <>
      <Helmet>
        <title>Teacher Dashboard | GharKaGuru</title>
        <meta name="description" content="Manage your tutor application and profile." />
      </Helmet>

      <h1 className="text-2xl font-semibold">Teacher Dashboard</h1>
      {!auth.token ? (
        <div className="mt-3 rounded-2xl border border-tn-border bg-white p-5 text-sm text-tn-muted">
          Please log in as a teacher to manage your application.
          <div className="mt-3">
            <Link to="/login" className="inline-flex">
              <Button size="sm">Go to Login</Button>
            </Link>
          </div>
        </div>
      ) : null}

      <section className="mt-6 grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Profile completion</h2>
          <div className="mt-3 h-3 w-full rounded-full bg-tn-border">
            <div className="h-3 rounded-full bg-tn-primary" style={{ width: `${completion}%` }} />
          </div>
          <div className="mt-2 text-sm text-tn-muted">{completion}% complete</div>
          <div className="mt-4 flex gap-2">
            <Link to="/teacher/register" className="inline-flex">
              <Button size="sm" disabled={!auth.token}>
                {alreadyRegistered && status === 'NotStarted' ? 'Add website profile' : status === 'NotStarted' ? 'Start application' : 'Edit profile'}
              </Button>
            </Link>
            <Link to="/teacher/register?assist=1" className="inline-flex">
              <Button size="sm" variant="secondary" disabled={!auth.token}>
                Need assistance
              </Button>
            </Link>
          </div>
        </div>

        <div className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Application status</h2>
          <div className="mt-3 inline-flex rounded-full bg-tn-bg px-3 py-1 text-sm">
            {q.isLoading ? 'Loading…' : statusLabel}
          </div>
          {q.data?.referenceId ? <div className="mt-2 text-sm text-tn-muted">Ref: {q.data.referenceId}</div> : null}
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-tn-border bg-white p-6">
        <h2 className="text-lg font-semibold">Parent enquiries</h2>
        {!applications.data?.items.length ? (
          <p className="mt-2 text-sm text-tn-muted">You have not applied for a parent enquiry yet.</p>
        ) : (
          <ul className="mt-3 space-y-3 text-sm">
            {applications.data.items.map((item) => {
              const phone = parentPhoneForDisplay(item.paymentStatus, item.parentPhone)
              return (
                <li key={item.enquiryId} className="rounded-xl border border-tn-border p-3">
                  <Link to={`/parent-enquiries/${item.enquiryId}`} className="font-medium">
                    {item.studentName || 'Student'} · {item.subject || item.classLevel}
                  </Link>
                  <p className="text-tn-muted">
                    {item.enquiryStatus} · Rs {item.amountRupees} · {item.paymentStatus}
                  </p>
                  {phone ? <p>Parent number: {phone}</p> : <p className="text-tn-muted">Parent number hidden until payment is confirmed.</p>}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-tn-border bg-white p-6 text-sm text-tn-muted">
        Once you submit your details, our customer representative will reach out to help if needed.
        Your profile will appear on GharKaGuru after verification and approval.
      </section>
    </>
  )
}


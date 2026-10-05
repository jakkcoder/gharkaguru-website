import { Helmet } from 'react-helmet-async'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import {
  applyForParentEnquiry,
  getEnquiryEligibility,
  getEnquiryPolicy,
  getParentContact,
  getParentEnquiry,
  listMyParentEnquiries,
  parentPhoneForDisplay,
} from '../../api/parentEnquiries'
import { ApiError } from '../../api/http'
import { Button } from '../../components/ui/Button'
import { OtpPanel } from '../../features/auth/OtpPanel'
import { useAuth } from '../../features/auth/useAuth'
import { EnquiryCard } from '../../features/parentEnquiries/EnquiryCard'
import { PolicyAcknowledgements } from '../../features/parentEnquiries/PolicyAcknowledgements'
import { useToast } from '../../components/ui/toast/useToast'

export function ParentEnquiryPage() {
  const { enquiryId = '' } = useParams()
  const auth = useAuth()
  const toast = useToast()
  const queryClient = useQueryClient()
  const enquiry = useQuery({
    queryKey: ['parent-enquiry', enquiryId],
    queryFn: () => getParentEnquiry(enquiryId),
    enabled: Boolean(enquiryId),
  })
  const policy = useQuery({ queryKey: ['enquiry-policy'], queryFn: getEnquiryPolicy })
  const teacher = auth.role === 'teacher' && Boolean(auth.token)
  const eligibility = useQuery({
    queryKey: ['enquiry-eligibility'],
    queryFn: getEnquiryEligibility,
    enabled: teacher,
  })
  const mine = useQuery({
    queryKey: ['my-parent-enquiries'],
    queryFn: listMyParentEnquiries,
    enabled: teacher,
  })
  const application = mine.data?.items.find((item) => item.enquiryId === enquiryId)
  const apply = useMutation({
    mutationFn: () =>
      applyForParentEnquiry(enquiryId, {
        isTutor: true,
        acceptNoRefund: true,
        acceptCommission: true,
        policyVersion: policy.data?.version || '',
      }),
    onSuccess: async () => {
      toast.success('Application saved', 'Payment is pending review.')
      await queryClient.invalidateQueries({ queryKey: ['my-parent-enquiries'] })
    },
    onError: (error) => {
      toast.error('Could not continue', error instanceof ApiError ? error.message : 'Try again.')
    },
  })
  const contact = useQuery({
    queryKey: ['parent-contact', enquiryId],
    queryFn: () => getParentContact(enquiryId),
    enabled: teacher && application?.paymentStatus === 'paid',
    retry: false,
  })
  const revealed = parentPhoneForDisplay(application?.paymentStatus || '', contact.data?.parentPhone || application?.parentPhone || '')
  const returnTo = `/teacher/register?next=${encodeURIComponent(`/parent-enquiries/${enquiryId}`)}`

  return (
    <>
      <Helmet>
        <title>Parent enquiry | GharKaGuru</title>
      </Helmet>
      <Link to="/parent-enquiries" className="text-sm text-tn-primary">
        All running enquiries
      </Link>
      {enquiry.isLoading || (teacher && mine.isLoading) ? <p className="mt-6 text-sm text-tn-muted">Loading enquiry…</p> : null}
      {enquiry.isError && !mine.isLoading && !application ? (
        <p className="mt-6 text-sm text-tn-error">This enquiry is no longer open.</p>
      ) : null}
      {enquiry.isError && application ? (
        <section className="mt-4 rounded-2xl border border-tn-border bg-white p-5">
          <h1 className="text-xl font-semibold">{application.studentName || 'Student'} · {application.subject || application.classLevel}</h1>
          <p className="mt-2 text-sm text-tn-muted">
            This enquiry is {application.enquiryStatus}. Access fee Rs {application.amountRupees} is {application.paymentStatus}.
          </p>
          {parentPhoneForDisplay(application.paymentStatus, application.parentPhone) ? (
            <p className="mt-3 text-sm font-medium">
              Parent number: {parentPhoneForDisplay(application.paymentStatus, application.parentPhone)}
              {application.parentName ? ` · ${application.parentName}` : ''}
            </p>
          ) : (
            <p className="mt-3 text-sm">The parent number stays hidden until the access fee is confirmed.</p>
          )}
        </section>
      ) : null}
      {enquiry.data ? (
        <div className="mt-4 grid gap-4">
          <EnquiryCard enquiry={enquiry.data} showLink={false} />
          {!teacher ? (
            <OtpPanel
              role="teacher"
              onVerified={(token, role, phone) => {
                auth.login(token, role, phone)
              }}
            />
          ) : null}
          {teacher && eligibility.data && !eligibility.data.registered ? (
            <section className="rounded-2xl border border-tn-border bg-white p-5">
              <h2 className="text-lg font-semibold">Teacher registration required</h2>
              <p className="mt-2 text-sm text-tn-muted">
                Complete every required teacher field. You will return to this enquiry afterwards.
              </p>
              <Link to={returnTo} className="mt-4 inline-flex">
                <Button type="button">Fill teacher details</Button>
              </Link>
            </section>
          ) : null}
          {teacher && eligibility.data?.registered && !application && policy.data ? (
            <PolicyAcknowledgements
              policy={policy.data}
              feeRupees={eligibility.data.nextFeeRupees}
              submitting={apply.isPending}
              onAccept={() => apply.mutate()}
            />
          ) : null}
          {application ? (
            <section className="rounded-2xl border border-tn-border bg-white p-5">
              <h2 className="text-lg font-semibold">Your application</h2>
              <p className="mt-2 text-sm text-tn-muted">
                Access fee: Rs {application.amountRupees}. Status: {application.paymentStatus}. Enquiry: {application.enquiryStatus}.
              </p>
              {application.paymentStatus !== 'paid' ? (
                <p className="mt-2 text-sm">Payment pending review. The parent number stays hidden until GharKaGuru confirms it.</p>
              ) : null}
              {revealed ? (
                <p className="mt-3 text-sm font-medium">
                  Parent number: {revealed}
                  {contact.data?.parentName || application.parentName ? ` · ${contact.data?.parentName || application.parentName}` : ''}
                </p>
              ) : null}
            </section>
          ) : null}
        </div>
      ) : null}
    </>
  )
}

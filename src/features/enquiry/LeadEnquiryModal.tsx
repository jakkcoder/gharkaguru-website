import { useMemo, useState } from 'react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { submitLeadInquiry } from '../../api/enquiry'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Spinner } from '../../components/ui/Spinner'
import { useToast } from '../../components/ui/toast/useToast'
import { trackEvent } from '../../lib/analytics'
import { useAppForm } from '../../lib/forms'

/** Sent on every lead inquiry; backend unchanged — same defaults as previous form pre-selections. */
const DEFAULT_CLASS_LEVEL = 'Class 8'
const DEFAULT_SUBJECT = 'Maths'

export function LeadEnquiryModal({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)
  const [successId, setSuccessId] = useState<string | null>(null)

  const schema = useMemo(
    () =>
      z.object({
        contactPhone: z.string().min(8, 'Contact number is required').max(20, 'Invalid contact number'),
      }),
    [],
  )

  const form = useAppForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      contactPhone: '',
    },
  })

  return (
    <Modal
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          setSuccessId(null)
          form.reset()
        }
        onOpenChange(o)
      }}
      title="Enquiry to Find Tutors"
      description="Enter your phone number and we’ll reach out soon."
    >
      {successId ? (
        <div className="space-y-3">
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-sm font-medium text-tn-text">Thanks! We will reach out to you soon.</div>
            <div className="mt-1 text-sm text-tn-muted">Reference: {successId}</div>
          </div>
          <Button onClick={() => onOpenChange(false)}>Back</Button>
        </div>
      ) : (
        <form
          className="space-y-4"
          onSubmit={form.handleSubmit(async (values) => {
            setSubmitting(true)
            try {
              trackEvent('lead_enquiry_submitted', {
                classLevel: DEFAULT_CLASS_LEVEL,
                subject: DEFAULT_SUBJECT,
              })
              const res = await submitLeadInquiry({
                contactPhone: values.contactPhone.trim(),
                classLevel: DEFAULT_CLASS_LEVEL,
                subject: DEFAULT_SUBJECT,
              })
              setSuccessId(res.inquiryId)
              toast.success('Enquiry sent')
            } catch {
              toast.error('Failed to submit enquiry')
            } finally {
              setSubmitting(false)
            }
          })}
        >
          <div>
            <label className="text-sm font-medium">Your contact number</label>
            <Input className="mt-1" {...form.register('contactPhone')} error={!!form.formState.errors.contactPhone} />
            {form.formState.errors.contactPhone ? (
              <p className="mt-1 text-sm text-tn-error">{form.formState.errors.contactPhone.message}</p>
            ) : null}
          </div>

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? <Spinner className="border-t-white" /> : null}
            Submit Enquiry
          </Button>
        </form>
      )}
    </Modal>
  )
}

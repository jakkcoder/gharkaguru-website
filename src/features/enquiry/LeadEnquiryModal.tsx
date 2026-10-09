import { useMemo, useState } from 'react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { submitLeadInquiry } from '../../api/enquiry'
import { ApiError } from '../../api/http'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Spinner } from '../../components/ui/Spinner'
import { useToast } from '../../components/ui/toast/useToast'
import { trackEvent } from '../../lib/analytics'
import { useAppForm } from '../../lib/forms'

// Accept "+91 98765 43210" and similar, keeping the 10-digit mobile number.
function toMobile(raw: string) {
  const digits = raw.replace(/\D/g, '')
  return digits.length === 12 && digits.startsWith('91') ? digits.slice(2) : digits
}

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
        contactPhone: z
          .string()
          .max(20, 'Enter a valid 10-digit mobile number')
          .transform(toMobile)
          .pipe(z.string().regex(/^[6-9]\d{9}$/, 'Enter a valid 10-digit mobile number')),
      }),
    [],
  )

  const form = useAppForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      contactPhone: '',
    },
  })

  // Back and the close button both clear the last enquiry, so reopening shows an empty form.
  const close = () => {
    setSuccessId(null)
    form.reset()
    onOpenChange(false)
  }

  return (
    <Modal
      open={open}
      onOpenChange={(o) => (o ? onOpenChange(true) : close())}
      title="Enquiry to Find Tutors"
      description="Enter your phone number and we’ll reach out soon."
    >
      {successId ? (
        <div className="space-y-3">
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-sm font-medium text-tn-text">Thanks! We will reach out to you soon.</div>
            <div className="mt-1 text-sm text-tn-muted">Reference: {successId}</div>
          </div>
          <Button onClick={close}>Back</Button>
        </div>
      ) : (
        <form
          className="space-y-4"
          onSubmit={form.handleSubmit(async (values) => {
            setSubmitting(true)
            try {
              trackEvent('lead_enquiry_submitted', {})
              // Class and subject are not asked here; the team collects them on the call.
              const res = await submitLeadInquiry({ contactPhone: values.contactPhone, classLevel: '', subject: '' })
              setSuccessId(res.inquiryId)
              toast.success('Enquiry sent')
            } catch (error) {
              toast.error('Failed to submit enquiry', error instanceof ApiError ? error.message : undefined)
            } finally {
              setSubmitting(false)
            }
          })}
        >
          <div>
            <label className="text-sm font-medium">Your contact number</label>
            <Input
              className="mt-1"
              type="tel"
              inputMode="numeric"
              autoComplete="tel-national"
              placeholder="10-digit mobile number"
              {...form.register('contactPhone')} error={!!form.formState.errors.contactPhone} />
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

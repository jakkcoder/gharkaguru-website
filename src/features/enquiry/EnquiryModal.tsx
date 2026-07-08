import { useMemo, useState } from 'react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { submitInquiry } from '../../api/enquiry'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Textarea } from '../../components/ui/Textarea'
import { Spinner } from '../../components/ui/Spinner'
import { useToast } from '../../components/ui/toast/useToast'
import { trackEvent } from '../../lib/analytics'
import { useAppForm } from '../../lib/forms'

export function EnquiryModal({
  open,
  onOpenChange,
  tutorId,
  tutorName,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  tutorId: string
  tutorName: string
}) {
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)
  const [successId, setSuccessId] = useState<string | null>(null)

  const schema = useMemo(
    () =>
      z.object({
        contactPhone: z.string().min(8, 'Contact number is required').max(20, 'Invalid contact number'),
        message: z.string().max(300, 'Max 300 characters').optional().or(z.literal('')),
      }),
    [],
  )

  const form = useAppForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      contactPhone: '',
      message: '',
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
      title={`Enquiry for ${tutorName}`}
      description="Enter your contact number and we’ll reach out soon."
    >
      {successId ? (
        <div className="space-y-3">
          <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
            <div className="text-sm font-medium text-tn-text">Thank you! Your enquiry has been sent.</div>
            <div className="mt-1 text-sm text-tn-muted">
              Our customer executive will reach out to you soon. Reference: {successId}
            </div>
          </div>
          <Button onClick={() => onOpenChange(false)}>Back</Button>
        </div>
      ) : (
        <form
          className="space-y-4"
          onSubmit={form.handleSubmit(async (values) => {
            setSubmitting(true)
            try {
              trackEvent('enquiry_submitted', { tutorId })
              const res = await submitInquiry({
                tutorId,
                contactPhone: values.contactPhone.trim(),
                message: values.message?.trim() || undefined,
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

          <div>
            <label className="text-sm font-medium">Message (optional, 0–300)</label>
            <Textarea className="mt-1" rows={4} {...form.register('message')} />
            <div className="mt-1 text-right text-xs text-tn-muted">
              {(form.watch('message') ?? '').length}/300
            </div>
          </div>

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? <Spinner className="border-t-white" /> : null}
            Enquire Now
          </Button>
        </form>
      )}
    </Modal>
  )
}


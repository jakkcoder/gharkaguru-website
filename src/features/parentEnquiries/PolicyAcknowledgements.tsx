import { useState } from 'react'
import type { EnquiryPolicy } from '../../api/parentEnquiries'
import { Button } from '../../components/ui/Button'

export function PolicyAcknowledgements({
  policy,
  feeRupees,
  submitting,
  onAccept,
}: {
  policy: EnquiryPolicy
  feeRupees: number
  submitting: boolean
  onAccept: () => void
}) {
  const [isTutor, setIsTutor] = useState(false)
  const [noRefund, setNoRefund] = useState(false)
  const [commission, setCommission] = useState(false)
  const ready = isTutor && noRefund && commission && !submitting

  return (
    <section className="rounded-2xl border border-tn-border bg-white p-5">
      <h2 className="text-lg font-semibold">Tutor acknowledgement</h2>
      <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-xl bg-tn-bg p-4 text-sm text-tn-text">{policy.text}</pre>
      <p className="mt-3 text-sm text-tn-muted">
        This parent number costs Rs {feeRupees}. The first unlock is Rs {policy.firstFeeRupees}. Later unlocks are Rs {policy.nextFeeRupees}.
      </p>
      <label className="mt-4 flex items-start gap-2 text-sm">
        <input type="checkbox" checked={isTutor} onChange={(event) => setIsTutor(event.target.checked)} />
        I am a tutor and I want to move forward with this enquiry.
      </label>
      <label className="mt-2 flex items-start gap-2 text-sm">
        <input type="checkbox" checked={noRefund} onChange={(event) => setNoRefund(event.target.checked)} />
        I understand no refund is provided if the demo fails.
      </label>
      <label className="mt-2 flex items-start gap-2 text-sm">
        <input type="checkbox" checked={commission} onChange={(event) => setCommission(event.target.checked)} />
        I will submit {policy.commissionPercent}% of my first tuition payment to GharKaGuru.
      </label>
      <div className="mt-4">
        <Button type="button" disabled={!ready} onClick={onAccept}>
          {submitting ? 'Saving…' : 'Acknowledge and continue'}
        </Button>
      </div>
    </section>
  )
}

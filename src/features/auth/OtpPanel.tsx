import { useEffect, useMemo, useState } from 'react'
import { phoneLogin, type AuthRole } from '../../api/auth'
import { ApiError } from '../../api/http'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Spinner } from '../../components/ui/Spinner'
import { useToast } from '../../components/ui/toast/useToast'

function normalizeIndianPhone(raw: string) {
  const digits = raw.replace(/[^\d]/g, '')
  if (digits.length <= 10) return digits
  return digits.slice(-10)
}

export function OtpPanel({
  role,
  onVerified,
}: {
  role: AuthRole
  onVerified: (token: string, role: AuthRole, phone: string) => void
}) {
  const toast = useToast()
  const [phone, setPhone] = useState('')
  const [verified, setVerified] = useState(false)
  const [loggingIn, setLoggingIn] = useState(false)
  const phoneDigits = useMemo(() => normalizeIndianPhone(phone), [phone])
  const validPhone = phoneDigits.length === 10
  useEffect(() => {}, [])

  const login = async () => {
    if (!validPhone) {
      toast.error('Enter a valid phone number', 'Use a 10-digit Indian mobile number.')
      return
    }
    if (loggingIn || verified) return
    setLoggingIn(true)
    try {
      const res = await phoneLogin(`+91${phoneDigits}`, role)
      setVerified(true)
      toast.success('Logged in')
      onVerified(res.token, res.role, `+91${phoneDigits}`)
    } catch (e) {
      if (e instanceof ApiError) {
        toast.error('Login failed', e.message)
      } else {
        toast.error('Login failed')
      }
    } finally {
      setLoggingIn(false)
    }
  }

  return (
    <div className="rounded-2xl border border-tn-border bg-white p-5">
      <div className="text-sm font-medium">Continue with Phone</div>
      <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto]">
        <div>
          <label className="text-sm font-medium">Phone</label>
          <div className="mt-1 flex">
            <div className="inline-flex h-10 items-center rounded-l-md border border-tn-border bg-tn-bg px-3 text-sm text-tn-muted">
              +91
            </div>
            <Input
              className="rounded-l-none"
              placeholder="10-digit mobile number"
              inputMode="numeric"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={verified}
              aria-label="Phone number"
            />
          </div>
        </div>
        <div className="flex items-end">
          <Button type="button" variant="secondary" onClick={login} disabled={!validPhone || verified || loggingIn} className="w-full">
            {loggingIn ? <Spinner className="border-t-white" /> : null}
            {verified ? 'Done' : 'Continue'}
          </Button>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-sm">
        {verified ? (
          <span className="rounded-full bg-tn-success px-2 py-1 text-white">Verified</span>
        ) : (
          <span className="text-tn-muted">No OTP required</span>
        )}
        <button
          type="button"
          className="text-tn-primary hover:underline"
          onClick={() => {
            setPhone('')
            setVerified(false)
          }}
        >
          Change number
        </button>
      </div>
    </div>
  )
}


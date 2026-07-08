import { Helmet } from 'react-helmet-async'
import { useNavigate, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { useToast } from '../components/ui/toast/useToast'
import { type AuthRole } from '../api/auth'
import { useAuth } from '../features/auth/useAuth'
import { OtpPanel } from '../features/auth/OtpPanel'

export function AuthPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const auth = useAuth()

  const isSignup = location.pathname === '/signup'
  const [role, setRole] = useState<AuthRole>('student')

  const onDone = (token: string, r: AuthRole) => {
    auth.login(token, r)
    toast.success('Logged in')
    navigate(r === 'teacher' ? '/teacher/dashboard' : '/student/dashboard')
  }

  return (
    <>
      <Helmet>
        <title>{isSignup ? 'Signup' : 'Login'} | GharKaGuru</title>
        <meta name="description" content="Login to GharKaGuru to manage enquiries and shortlist tutors." />
      </Helmet>

      <div className="mx-auto max-w-xl">
        <div className="rounded-2xl border border-tn-border bg-white p-6 shadow-soft">
          <h1 className="text-2xl font-semibold">{isSignup ? 'Create your account' : 'Welcome back'}</h1>
          <p className="mt-2 text-tn-muted">
            Continue with your phone number.
          </p>

          <div className="mt-4">
            <label className="text-sm font-medium">I am a</label>
            <select
              className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm"
              value={role}
              onChange={(e) => setRole(e.target.value as AuthRole)}
            >
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
            </select>
          </div>

          <div className="mt-5 grid gap-3">
            <OtpPanel
              role={role}
              onVerified={(token, r) => {
                onDone(token, r)
              }}
            />
          </div>

          <div className="mt-6 text-sm text-tn-muted">
            By continuing, you agree to our Terms and Privacy Policy.
          </div>
        </div>
      </div>
    </>
  )
}


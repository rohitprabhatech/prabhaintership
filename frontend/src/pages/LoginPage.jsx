import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { ArrowRight, Building2, LockKeyhole } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import { ApiError } from '../lib/api.js'
import { Button, ErrorState, TextField } from '../components/ui.jsx'

export default function LoginPage() {
  const { signIn, status, expired } = useAuth()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (status === 'authenticated') return <Navigate to={location.state?.from || '/'} replace />
  if (status === 'checking') return <div className="grid min-h-screen place-items-center text-sm text-muted" role="status">Checking administrator session…</div>

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!username.trim() || !password) {
      setError('Enter your username and password to continue.')
      return
    }
    if (username.trim().length > 128 || password.length > 1024) {
      setError('Username or password exceeds the allowed length.')
      return
    }

    setSubmitting(true)
    try {
      await signIn(username.trim(), password)
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 429) {
        const retry = cause.requestId ? ` Reference: ${cause.requestId}` : ''
        setError(`Too many sign-in attempts. Wait before trying again.${retry}`)
      } else if (cause instanceof ApiError && cause.status === 401) {
        setError('The username or password is incorrect.')
      } else {
        setError(cause.message || 'Unable to sign in. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-canvas grid min-h-screen lg:grid-cols-[minmax(20rem,0.85fr)_minmax(30rem,1.15fr)]">
      <section className="relative hidden overflow-hidden bg-orange-600 p-12 text-white lg:flex lg:flex-col lg:justify-between xl:p-16">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full border border-white/15" />
        <div className="absolute -bottom-40 -left-20 h-[28rem] w-[28rem] rounded-full border border-white/15" />
        <div className="relative flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-md bg-white text-orange-700"><Building2 aria-hidden="true" className="h-6 w-6" /></div>
          <div><p className="text-sm font-bold">Prabha Technology Pvt. Ltd.</p><p className="text-xs text-orange-100">Internship administration</p></div>
        </div>
        <div className="relative max-w-lg">
          <p className="mb-4 text-xs font-bold uppercase text-orange-100">Internal portal</p>
          <h1 className="font-display text-5xl leading-[1.05] xl:text-6xl">Keep every internship in good order.</h1>
          <p className="mt-6 max-w-md text-base leading-7 text-orange-50">A focused workspace for authorized administrators to manage student and program records.</p>
        </div>
        <p className="relative text-xs text-orange-100">Prabha Technology Pvt. Ltd. · Administration</p>
      </section>

      <section className="flex min-h-screen items-center justify-center px-5 py-12 sm:px-10">
        <div className="w-full max-w-[26rem]">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-orange-600 text-white"><Building2 aria-hidden="true" className="h-5 w-5" /></div>
            <div><p className="text-sm font-bold text-ink">Prabha Technology</p><p className="text-xs text-muted">Administration</p></div>
          </div>
          <div className="mb-8">
            <div className="mb-5 grid h-11 w-11 place-items-center rounded-md bg-orange-50 text-orange-700"><LockKeyhole aria-hidden="true" className="h-5 w-5" /></div>
            <p className="text-xs font-bold uppercase text-orange-700">Administrator access</p>
            <h2 className="mt-2 font-display text-4xl text-ink">Sign in</h2>
            <p className="mt-2 text-sm leading-6 text-muted">Use your provisioned administrator credentials to continue.</p>
          </div>

          {expired && <div role="status" className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-900">Your session expired. Sign in again to continue.</div>}
          {error && <div className="mb-4"><ErrorState title="Sign-in unsuccessful" message={error} /></div>}

          <form onSubmit={handleSubmit} className="grid gap-5" noValidate>
            <TextField id="username" name="username" label="Username" autoComplete="username" autoCapitalize="none" spellCheck="false" maxLength={128} required value={username} onChange={(event) => setUsername(event.target.value)} />
            <TextField id="password" name="password" label="Password" type="password" autoComplete="current-password" maxLength={1024} required value={password} onChange={(event) => setPassword(event.target.value)} />
            <Button type="submit" disabled={submitting} className="mt-1 w-full">
              {submitting ? 'Signing in…' : <>Sign in securely <ArrowRight aria-hidden="true" className="h-4 w-4" /></>}
            </Button>
          </form>
          <p className="mt-6 text-center text-xs leading-5 text-muted">Administrator accounts are provisioned by an operator. Registration is not available.</p>
        </div>
      </section>
    </main>
  )
}
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, KeyRound } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import { Button, ErrorState } from '../components/ui.jsx'
import { ApiError, apiRequest } from '../lib/api.js'

function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  visible,
  onToggle,
  minLength,
  hint,
}) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold text-ink">{label}</label>
      <div className="relative">
        <input
          id={id}
          name={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          minLength={minLength}
          maxLength={1024}
          required
          aria-describedby={hint ? `${id}-hint` : undefined}
          className="min-h-11 w-full rounded-md border border-line bg-white px-3 pr-12 text-sm text-ink outline-none transition focus:border-orange-500 focus:ring-2 focus:ring-orange-100"
        />
        <button
          type="button"
          onClick={onToggle}
          aria-label={`${visible ? 'Hide' : 'Show'} ${label}`}
          aria-pressed={visible}
          className="absolute inset-y-0 right-1 grid w-10 place-items-center rounded-md text-muted hover:bg-canvas hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
        >
          {visible
            ? <EyeOff aria-hidden="true" className="h-4 w-4" />
            : <Eye aria-hidden="true" className="h-4 w-4" />}
        </button>
      </div>
      {hint && <p id={`${id}-hint`} className="text-xs text-muted">{hint}</p>}
    </div>
  )
}

const fields = [
  { key: 'currentPassword', label: 'Current password', autoComplete: 'current-password' },
  { key: 'newPassword', label: 'New password', autoComplete: 'new-password', minLength: 12 },
  { key: 'confirmPassword', label: 'Confirm new password', autoComplete: 'new-password' },
]

export default function ChangePasswordPage() {
  const { token, signOut } = useAuth()
  const navigate = useNavigate()
  const [passwords, setPasswords] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })
  const [visibility, setVisibility] = useState({})
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function updatePassword(key, value) {
    setPasswords((previous) => ({ ...previous, [key]: value }))
    setError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return
    if (!passwords.currentPassword || !passwords.newPassword || !passwords.confirmPassword) {
      setError('Complete all three password fields.')
      return
    }
    if (passwords.newPassword.length < 12) {
      setError('New password must contain at least 12 characters.')
      return
    }
    if (passwords.newPassword !== passwords.confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const result = await apiRequest('auth/change-password', {
        method: 'POST',
        token,
        body: JSON.stringify({
          current_password: passwords.currentPassword,
          new_password: passwords.newPassword,
          confirm_password: passwords.confirmPassword,
        }),
      })
      setPasswords({ currentPassword: '', newPassword: '', confirmPassword: '' })
      signOut()
      navigate('/login', {
        replace: true,
        state: { notice: result.message || 'Password changed. Sign in again with your new password.' },
      })
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === 'current_password_incorrect') {
        setError('Current password is incorrect.')
      } else if (cause instanceof ApiError && cause.code === 'password_mismatch') {
        setError('New password and confirmation do not match.')
      } else if (cause instanceof ApiError && cause.code === 'invalid_password_length') {
        setError('New password must contain 12-1024 characters.')
      } else if (cause instanceof ApiError && cause.code === 'password_unchanged') {
        setError('Choose a new password that differs from your current password.')
      } else if (cause instanceof ApiError && cause.status === 401) {
        setError('Your session has expired. Sign in again and retry.')
      } else if (cause instanceof ApiError && cause.status === 429) {
        setError('Too many password verification attempts. Wait before trying again.')
      } else {
        setError('Password could not be changed. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="animate-enter">
      <div className="mb-7">
        <p className="text-xs font-bold uppercase text-orange-700">Account settings</p>
        <h1 className="mt-2 font-display text-4xl text-ink">Change password</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Update your administrator password. You will need to sign in again after it changes.
        </p>
      </div>
      <section className="max-w-2xl rounded-lg border border-line bg-white p-5 sm:p-7">
        <div className="mb-6 flex items-start gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-orange-50 text-orange-700">
            <KeyRound aria-hidden="true" className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-ink">Password security</h2>
            <p className="mt-1 text-sm leading-6 text-muted">
              Use at least 12 characters. Your current password is required to confirm this change.
            </p>
          </div>
        </div>

        {error && <div className="mb-5"><ErrorState title="Password not changed" message={error} /></div>}

        <form onSubmit={handleSubmit} className="grid gap-5" noValidate>
          {fields.map((field) => (
            <PasswordField
              key={field.key}
              id={field.key}
              label={field.label}
              value={passwords[field.key]}
              onChange={(event) => updatePassword(field.key, event.target.value)}
              autoComplete={field.autoComplete}
              minLength={field.minLength}
              hint={field.key === 'newPassword' ? 'Must be 12-1024 characters and differ from your current password.' : undefined}
              visible={Boolean(visibility[field.key])}
              onToggle={() => setVisibility((previous) => ({
                ...previous,
                [field.key]: !previous[field.key],
              }))}
            />
          ))}
          <div className="flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="secondary"
              disabled={submitting}
              onClick={() => navigate('/')}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Changing password…' : 'Change password'}
            </Button>
          </div>
        </form>
      </section>
    </div>
  )
}

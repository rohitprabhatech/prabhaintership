import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { signOut, apiRequest } = vi.hoisted(() => ({
  signOut: vi.fn(),
  apiRequest: vi.fn(),
}))

vi.mock('../auth/AuthProvider.jsx', () => ({
  useAuth: () => ({ token: 'test-admin-token', signOut }),
}))

vi.mock('../lib/api.js', () => ({
  ApiError: class ApiError extends Error {
    constructor(message, options = {}) {
      super(message)
      Object.assign(this, options)
    }
  },
  apiRequest,
}))

import ChangePasswordPage from '../pages/ChangePasswordPage.jsx'

function LoginNotice() {
  const location = useLocation()
  return <div>{location.state?.notice || 'Login page'}</div>
}

function renderChangePassword() {
  return render(
    <MemoryRouter initialEntries={['/change-password']}>
      <Routes>
        <Route path="/change-password" element={<ChangePasswordPage />} />
        <Route path="/login" element={<LoginNotice />} />
        <Route path="/" element={<div>Dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Change password page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('validates locally, shows/hides inputs, then submits and requires a new login', async () => {
    apiRequest.mockResolvedValue({
      message: 'Password changed. Sign in again with your new password.',
      reauthenticate: true,
    })
    renderChangePassword()

    const currentPassword = screen.getByLabelText('Current password')
    const newPassword = screen.getByLabelText('New password')
    const confirmPassword = screen.getByLabelText('Confirm new password')
    fireEvent.change(currentPassword, { target: { value: 'Current-test-password-123!' } })
    fireEvent.change(newPassword, { target: { value: 'Changed-test-password-456!' } })
    fireEvent.change(confirmPassword, { target: { value: 'Different-confirmation-789!' } })
    fireEvent.click(screen.getByRole('button', { name: 'Change password' }))

    expect(screen.getByText('New password and confirmation do not match.')).toBeInTheDocument()
    expect(apiRequest).not.toHaveBeenCalled()

    fireEvent.change(confirmPassword, { target: { value: 'Changed-test-password-456!' } })
    fireEvent.click(screen.getByRole('button', { name: 'Show Current password' }))
    expect(currentPassword).toHaveAttribute('type', 'text')
    fireEvent.click(screen.getByRole('button', { name: 'Hide Current password' }))
    expect(currentPassword).toHaveAttribute('type', 'password')

    fireEvent.click(screen.getByRole('button', { name: 'Change password' }))

    expect(await screen.findByText('Password changed. Sign in again with your new password.')).toBeInTheDocument()
    expect(apiRequest).toHaveBeenCalledWith('auth/change-password', {
      method: 'POST',
      token: 'test-admin-token',
      body: JSON.stringify({
        current_password: 'Current-test-password-123!',
        new_password: 'Changed-test-password-456!',
        confirm_password: 'Changed-test-password-456!',
      }),
    })
    expect(signOut).toHaveBeenCalledOnce()
    expect(sessionStorage.length).toBe(0)
  })

  it('shows safe server errors without echoing supplied passwords', async () => {
    const { ApiError } = await import('../lib/api.js')
    apiRequest.mockRejectedValue(
      new ApiError('Request failed', { status: 400, code: 'current_password_incorrect' }),
    )
    renderChangePassword()
    fireEvent.change(screen.getByLabelText('Current password'), {
      target: { value: 'Secret-current-password!' },
    })
    fireEvent.change(screen.getByLabelText('New password'), {
      target: { value: 'Secret-new-password-123!' },
    })
    fireEvent.change(screen.getByLabelText('Confirm new password'), {
      target: { value: 'Secret-new-password-123!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Change password' }))

    const error = await screen.findByRole('alert')
    expect(error).toHaveTextContent('Current password is incorrect.')
    expect(error).not.toHaveTextContent('Secret')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Change password' })).toBeEnabled())
  })
})

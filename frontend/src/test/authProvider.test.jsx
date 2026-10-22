import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from '../auth/AuthProvider.jsx'

const storageKey = 'prabhatech.admin.session'

function AuthControls() {
  const { status, signIn, signOut } = useAuth()

  return (
    <div>
      <span>{status}</span>
      <button onClick={() => signIn('prabhatech', 'test-password')}>Sign in</button>
      <button onClick={signOut}>Sign out</button>
    </div>
  )
}

describe('Admin authentication session', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('clears the stored session and returns to anonymous state on sign out', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            access_token: 'test-session-token',
            expires_in: 900,
            admin: { admin_id: 1, username: 'prabhatech', email: 'prabhatech@gmail.com' },
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        ),
      ),
    )

    render(
      <AuthProvider>
        <AuthControls />
      </AuthProvider>,
    )

    await waitFor(() => expect(screen.getByText('anonymous')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(screen.getByText('authenticated')).toBeInTheDocument())
    expect(JSON.parse(sessionStorage.getItem(storageKey)).accessToken).toBe(
      'test-session-token',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(screen.getByText('anonymous')).toBeInTheDocument()
    expect(sessionStorage.getItem(storageKey)).toBeNull()
  })
})

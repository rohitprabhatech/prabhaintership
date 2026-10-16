import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { ApiError, apiRequest } from '../lib/api.js'

const AuthContext = createContext(null)
const STORAGE_KEY = 'prabhatech.admin.session'

function readStoredSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null')
    if (!session?.accessToken || !session?.expiresAt) return null
    if (session.expiresAt <= Date.now()) {
      sessionStorage.removeItem(STORAGE_KEY)
      return null
    }
    return session
  } catch {
    sessionStorage.removeItem(STORAGE_KEY)
    return null
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [admin, setAdmin] = useState(null)
  const [status, setStatus] = useState('checking')
  const [expired, setExpired] = useState(false)

  function clearSession(showExpiry = false) {
    sessionStorage.removeItem(STORAGE_KEY)
    setSession(null)
    setAdmin(null)
    setExpired(showExpiry)
    setStatus('anonymous')
  }

  useEffect(() => {
    let active = true
    const stored = readStoredSession()
    if (!stored) {
      setStatus('anonymous')
      return () => { active = false }
    }

    setSession(stored)
    apiRequest('auth/me', { token: stored.accessToken })
      .then((currentAdmin) => {
        if (!active) return
        setAdmin(currentAdmin)
        setStatus('authenticated')
      })
      .catch((error) => {
        if (active) clearSession(error instanceof ApiError && error.status === 401)
      })

    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!session?.expiresAt || status !== 'authenticated') return undefined
    const remaining = session.expiresAt - Date.now()
    if (remaining <= 0) {
      clearSession(true)
      return undefined
    }
    const timer = window.setTimeout(() => clearSession(true), remaining)
    return () => window.clearTimeout(timer)
  }, [session, status])

  useEffect(() => {
    const handleUnauthorized = () => clearSession(true)
    window.addEventListener('admin-session-expired', handleUnauthorized)
    return () => window.removeEventListener('admin-session-expired', handleUnauthorized)
  }, [])

  async function signIn(username, password) {
    const result = await apiRequest('auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    const nextSession = {
      accessToken: result.access_token,
      expiresAt: Date.now() + result.expires_in * 1000,
    }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession))
    setSession(nextSession)
    setAdmin(result.admin)
    setExpired(false)
    setStatus('authenticated')
  }

  function signOut() {
    clearSession(false)
  }

  const value = useMemo(() => ({
    admin,
    token: session?.accessToken || null,
    status,
    expired,
    signIn,
    signOut,
  }), [admin, session, status, expired])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
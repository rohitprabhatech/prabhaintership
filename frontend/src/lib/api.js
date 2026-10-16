const configuredBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const normalizedBase = configuredBase.replace(/\/+$/, '')
const apiRoot = normalizedBase.endsWith('/api/v1')
  ? normalizedBase
  : `${normalizedBase}/api/v1`

export class ApiError extends Error {
  constructor(message, { status, code, requestId, errors } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.errors = errors
  }
}

export function apiUrl(path) {
  return `${apiRoot}/${path.replace(/^\/+/, '')}`
}

async function readResponse(response) {
  if (response.status === 204) return null

  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) return null

  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function apiRequest(path, { token, ...options } = {}) {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response
  try {
    response = await fetch(apiUrl(path), { ...options, headers })
  } catch {
    throw new ApiError('The server could not be reached. Check your connection and try again.')
  }

  const payload = await readResponse(response)
  if (!response.ok) {
    if (response.status === 401 && token) {
      window.dispatchEvent(new Event('admin-session-expired'))
    }
    const message = payload?.title || payload?.detail || 'The request could not be completed.'
    throw new ApiError(message, {
      status: response.status,
      code: payload?.code,
      requestId: payload?.request_id,
      errors: payload?.errors,
    })
  }

  return payload
}

export function getApiBaseUrl() {
  return apiRoot
}
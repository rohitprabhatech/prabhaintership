import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, apiUrl } from '../lib/api.js'
import { decimalToMinorUnits, formatInrMinorUnits, loadDashboard } from '../lib/adminData.js'
import { loadStudentList, loadStudentProfile } from '../lib/studentData.js'

describe('API client', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('uses the configured API root and normalizes route paths', () => {
    expect(apiUrl('/auth/me')).toBe('http://localhost:8000/api/v1/auth/me')
  })

  it('sends bearer credentials and parses the approved JSON response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ admin_id: 7 }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiRequest('auth/me', { token: 'session-token' })).resolves.toEqual({ admin_id: 7 })
    expect(fetchMock.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer session-token')
  })

  it('uses documented dashboard routes and sums API fee summaries in minor units', async () => {
    const requested = []
    const responses = {
      '/students?status=all&page=1&page_size=1': { items: [], total: 2, page: 1, page_size: 1, pages: 2 },
      '/programs?status=active&page=1&page_size=1': { items: [], total: 1, page: 1, page_size: 1, pages: 1 },
      '/batches?status=active&page=1&page_size=1': { items: [], total: 1, page: 1, page_size: 1, pages: 1 },
      '/enrollments?status=completed&page=1&page_size=1': { items: [], total: 1, page: 1, page_size: 1, pages: 1 },
      '/certificates?status=issued&page=1&page_size=1': { items: [], total: 1, page: 1, page_size: 1, pages: 1 },
      '/enrollments?status=all&page=1&page_size=100': { items: [{ enrollment_id: 4, student_id: 3, program_id: 2, batch_id: null, enrollment_number: 'EN-4', status: 'active', created_at: '2026-01-01T00:00:00Z' }], total: 1, page: 1, page_size: 100, pages: 1 },
      '/enrollments/4/fees': { net_paid: '125.50', pending_balance: '74.50' },
      '/students/3': { student_id: 3, full_name: 'Ada Student', student_number: 'ST-3' },
      '/programs/2': { program_id: 2, name: 'Engineering' },
    }
    vi.stubGlobal('fetch', vi.fn(async (url) => {
      const pathname = new URL(url).pathname.replace('/api/v1', '')
      const query = new URL(url).search
      const key = `${pathname}${query}`
      requested.push(key)
      return new Response(JSON.stringify(responses[key]), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    }))

    const result = await loadDashboard('session-token')
    expect(result.counts.students).toBe(2)
    expect(result.counts.collected).toBe(12550n)
    expect(result.counts.outstanding).toBe(7450n)
    expect(result.recentEnrollments[0].student.full_name).toBe('Ada Student')
    expect(requested).not.toContain('/payments')
    expect(decimalToMinorUnits('0.01')).toBe(1n)
    expect(formatInrMinorUnits(123456789012345678901n)).toBe('₹12,34,56,78,90,12,34,56,789.01')
  })

  it('enriches a student page through documented enrollment, program, and batch reads', async () => {
    const requestedPaths = []
    const fetchMock = vi.fn(async (url) => {
      const parsed = new URL(url)
      const path = parsed.pathname.replace('/api/v1', '')
      requestedPaths.push(path)
      const body = path === '/students'
        ? { items: [{ student_id: 3, full_name: 'Ada Student' }], total: 1, page: 1, page_size: 20, pages: 1 }
        : path === '/programs'
          ? { items: [{ program_id: 2, name: 'Engineering' }], total: 1, page: 1, page_size: 100, pages: 1 }
          : path === '/batches'
            ? { items: [{ batch_id: 5, name: 'Cohort A' }], total: 1, page: 1, page_size: 100, pages: 1 }
            : path === '/enrollments'
              ? { items: [{ enrollment_id: 9, program_id: 2, batch_id: 5 }], total: 1, page: 1, page_size: 100, pages: 1 }
              : null
      return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } })
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await loadStudentList({ token: 'session-token', page: 1, pageSize: 20, query: '', status: 'all' })
    expect(result.items[0].program.name).toBe('Engineering')
    expect(result.items[0].batch.name).toBe('Cohort A')
    expect(requestedPaths).toEqual(expect.arrayContaining(['/students', '/programs', '/batches', '/enrollments']))
  })

  it('loads profile history only through the documented enrollment-scoped routes', async () => {
    const requestedPaths = []
    vi.stubGlobal('fetch', vi.fn(async (url) => {
      const path = new URL(url).pathname.replace('/api/v1', '')
      requestedPaths.push(path)
      let body = {}
      if (path === '/students/7') body = { student_id: 7, full_name: 'Ada Student' }
      else if (path === '/enrollments') body = { items: [{ enrollment_id: 9, program_id: 2, batch_id: null }], total: 1, page: 1, page_size: 100, pages: 1 }
      else if (path === '/programs' || path === '/batches') body = { items: [], total: 0, page: 1, page_size: 100, pages: 0 }
      else if (path.endsWith('/fees')) body = { effective_fee: '100.00', net_paid: '50.00', pending_balance: '50.00' }
      else if (path.endsWith('/fee-terms') || path.endsWith('/fee-adjustments')) body = []
      else if (path === '/enrollments/9/payments') body = { items: [{ payment_id: 12 }], total: 1, page: 1, page_size: 100, pages: 1 }
      else if (path === '/payments/12/adjustments') body = [{ adjustment_id: 4, reason: 'Partial refund' }]
      else if (path === '/project-assignments' || path === '/certificates') body = { items: [], total: 0, page: 1, page_size: 100, pages: 0 }
      return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } })
    }))

    const result = await loadStudentProfile(7, 'session-token')
    expect(result.history).toHaveLength(1)
    expect(result.history[0].payments[0].adjustments[0].reason).toBe('Partial refund')
    expect(requestedPaths).toEqual(expect.arrayContaining([
      '/students/7', '/enrollments', '/programs', '/batches',
      '/enrollments/9/fees', '/enrollments/9/fee-terms', '/enrollments/9/fee-adjustments',
      '/enrollments/9/payments', '/payments/12/adjustments', '/project-assignments', '/certificates',
    ]))
  })
})
import { apiRequest } from './api.js'
import { getAllPages, mapWithConcurrency } from './adminData.js'

export async function loadFinanceEnrollments({ token, page, pageSize, query, status }) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), status })
  if (query) params.set('q', query)
  const [enrollments, programs] = await Promise.all([
    apiRequest(`enrollments?${params}`, { token }),
    getAllPages('programs', { status: 'all' }, token),
  ])
  const programById = new Map(programs.items.map((program) => [program.program_id, program]))
  const rows = await mapWithConcurrency(enrollments.items, 6, async (enrollment) => {
    const [fees, student] = await Promise.all([
      apiRequest(`enrollments/${enrollment.enrollment_id}/fees`, { token }),
      apiRequest(`students/${enrollment.student_id}`, { token }),
    ])
    return { ...enrollment, fees, student, program: programById.get(enrollment.program_id) || null }
  })
  return { ...enrollments, items: rows }
}

export async function loadFinanceDetails(enrollmentId, token) {
  const [fees, feeTerms, feeAdjustments, paymentPage] = await Promise.all([
    apiRequest(`enrollments/${enrollmentId}/fees`, { token }),
    apiRequest(`enrollments/${enrollmentId}/fee-terms`, { token }),
    apiRequest(`enrollments/${enrollmentId}/fee-adjustments`, { token }),
    getAllPages(`enrollments/${enrollmentId}/payments`, {}, token),
  ])
  const payments = await mapWithConcurrency(paymentPage.items, 4, async (payment) => ({
    ...payment,
    adjustments: await apiRequest(`payments/${payment.payment_id}/adjustments`, { token }),
  }))
  return { fees, feeTerms, feeAdjustments, payments }
}
import { apiRequest } from './api.js'
import { getAllPages, mapWithConcurrency } from './adminData.js'

export async function loadStudentList({
  token,
  page,
  pageSize,
  query,
  status,
  programId = 'all',
  batchId = 'all',
  enrollmentStatus = 'all',
  feeStatus = 'all',
}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    q: query,
    status,
  })
  if (programId !== 'all') params.set('program_id', programId)
  if (batchId !== 'all') params.set('batch_id', batchId)
  if (enrollmentStatus !== 'all') params.set('enrollment_status', enrollmentStatus)
  if (feeStatus !== 'all') params.set('fee_status', feeStatus)
  const [studentPage, programs, batches] = await Promise.all([
    apiRequest(`students?${params}`, { token }),
    getAllPages('programs', { status: 'all' }, token),
    getAllPages('batches', { status: 'all' }, token),
  ])

  const programById = new Map(programs.items.map((program) => [program.program_id, program]))
  const batchById = new Map(batches.items.map((batch) => [batch.batch_id, batch]))
  const enrollmentsByStudent = await mapWithConcurrency(studentPage.items, 6, (student) => (
    getAllPages('enrollments', { student_id: student.student_id, status: 'all' }, token)
  ))

  return {
    ...studentPage,
    programs: programs.items,
    batches: batches.items,
    items: studentPage.items.map((student, index) => {
      const latestEnrollment = enrollmentsByStudent[index].items[0]
      return {
        ...student,
        latestEnrollment,
        program: latestEnrollment ? programById.get(latestEnrollment.program_id) : null,
        batch: latestEnrollment?.batch_id ? batchById.get(latestEnrollment.batch_id) : null,
      }
    }),
  }
}

export async function loadStudentProfile(studentId, token) {
  const [student, enrollments, programs, batches, activity] = await Promise.all([
    apiRequest(`students/${studentId}`, { token }),
    getAllPages('enrollments', { student_id: studentId, status: 'all' }, token),
    getAllPages('programs', { status: 'all' }, token),
    getAllPages('batches', { status: 'all' }, token),
    apiRequest(`students/${studentId}/activity`, { token }),
  ])

  const programById = new Map(programs.items.map((program) => [program.program_id, program]))
  const batchById = new Map(batches.items.map((batch) => [batch.batch_id, batch]))
  const history = await mapWithConcurrency(enrollments.items, 4, async (enrollment) => {
    const [fees, feeTerms, feeAdjustments, payments, projects, certificates] = await Promise.all([
      apiRequest(`enrollments/${enrollment.enrollment_id}/fees`, { token }),
      apiRequest(`enrollments/${enrollment.enrollment_id}/fee-terms`, { token }),
      apiRequest(`enrollments/${enrollment.enrollment_id}/fee-adjustments`, { token }),
      getAllPages(`enrollments/${enrollment.enrollment_id}/payments`, {}, token),
      getAllPages('project-assignments', { enrollment_id: enrollment.enrollment_id, status: 'all' }, token),
      getAllPages('certificates', { enrollment_id: enrollment.enrollment_id, status: 'all' }, token),
    ])
    const paymentHistory = await mapWithConcurrency(payments.items, 4, async (payment) => ({
      ...payment,
      adjustments: await apiRequest(`payments/${payment.payment_id}/adjustments`, { token }),
    }))
    return {
      ...enrollment,
      program: programById.get(enrollment.program_id) || null,
      batch: enrollment.batch_id ? batchById.get(enrollment.batch_id) || null : null,
      fees,
      feeTerms,
      feeAdjustments,
      payments: paymentHistory,
      projects: projects.items,
      certificates: certificates.items,
    }
  })

  return { student, history, activity }
}
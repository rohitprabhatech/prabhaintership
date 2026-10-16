import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../auth/AuthProvider.jsx', () => ({
  useAuth: () => ({ token: 'admin-token' }),
}))

vi.mock('../lib/api.js', () => {
  class MockApiError extends Error {
    constructor(message, details = {}) {
      super(message)
      Object.assign(this, details)
    }
  }
  return { ApiError: MockApiError, apiRequest: vi.fn() }
})

vi.mock('../lib/studentData.js', () => ({
  loadStudentList: vi.fn(),
  loadStudentProfile: vi.fn(),
}))

vi.mock('../lib/adminData.js', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual, loadDashboard: vi.fn() }
})

import { ApiError, apiRequest } from '../lib/api.js'
import { loadDashboard } from '../lib/adminData.js'
import { loadStudentList, loadStudentProfile } from '../lib/studentData.js'
import DashboardPage from '../pages/DashboardPage.jsx'
import StudentProfilePage from '../pages/StudentProfilePage.jsx'
import StudentsPage from '../pages/StudentsPage.jsx'

const student = {
  student_id: 7,
  student_number: 'PT-007',
  full_name: 'Asha Patel',
  email: 'asha@example.com',
  phone: '+91 98765 43210',
  status: 'active',
  created_by: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
  archived_at: null,
}

const studentPage = {
  items: [{ ...student, program: { name: 'Data Engineering' }, batch: { name: 'Cohort A' } }],
  total: 21,
  page: 1,
  page_size: 20,
  pages: 2,
}

function renderStudents() {
  return render(
    <MemoryRouter initialEntries={['/students']}>
      <Routes><Route path="/students" element={<StudentsPage />} /></Routes>
    </MemoryRouter>,
  )
}

function renderProfile() {
  return render(
    <MemoryRouter initialEntries={['/students/7']}>
      <Routes><Route path="/students/:studentId" element={<StudentProfilePage />} /></Routes>
    </MemoryRouter>,
  )
}

function fillStudentForm(dialog) {
  fireEvent.change(within(dialog).getByLabelText('Student number'), { target: { value: 'PT-008' } })
  fireEvent.change(within(dialog).getByLabelText('Full name'), { target: { value: 'Ravi Kumar' } })
}

describe('admin dashboard and student workflows', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    loadStudentList.mockResolvedValue(studentPage)
    loadStudentProfile.mockResolvedValue({ student, history: [] })
  })

  it('renders dashboard metrics and the supported payment-history limitation', async () => {
    loadDashboard.mockResolvedValue({
      counts: { students: 18, programs: 3, batches: 5, collected: 125500n, outstanding: 7500n, completed: 4, certificates: 2 },
      recentEnrollments: [],
    })
    render(<DashboardPage />)

    expect(await screen.findByText(/₹1,255/)).toBeInTheDocument()
    expect(screen.getByText('Total students')).toBeInTheDocument()
    expect(screen.getByText('Recent payments')).toBeInTheDocument()
    expect(screen.getByText(/does not expose a global recent-payments list/i)).toBeInTheDocument()
  })

  it('shows server-backed student context and applies search, status, and pagination', async () => {
    const user = userEvent.setup()
    renderStudents()

    expect(await screen.findByRole('link', { name: /Asha Patel PT-007/ })).toBeInTheDocument()
    expect(screen.getByText('Data Engineering')).toBeInTheDocument()
    expect(screen.getByText('Cohort A')).toBeInTheDocument()

    await user.type(screen.getByRole('searchbox', { name: 'Search students' }), 'asha')
    await user.click(screen.getByRole('button', { name: 'Apply student search' }))
    await waitFor(() => expect(loadStudentList).toHaveBeenLastCalledWith(expect.objectContaining({ query: 'asha', page: 1 })))

    await user.selectOptions(screen.getByLabelText('Status'), 'all')
    await waitFor(() => expect(loadStudentList).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'all' })))
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(loadStudentList).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })))
  })

  it('validates and prevents duplicate student submissions while showing success', async () => {
    const user = userEvent.setup()
    let resolveRequest
    apiRequest.mockReturnValueOnce(new Promise((resolve) => { resolveRequest = resolve }))
    renderStudents()

    await screen.findByText('Data Engineering')
    await user.click(screen.getByRole('button', { name: 'Add student' }))
    const dialog = screen.getByRole('dialog', { name: 'Add student' })
    const form = dialog.querySelector('form')
    fireEvent.submit(form)
    expect(await within(dialog).findByText('Enter a student number.')).toBeInTheDocument()
    expect(apiRequest).not.toHaveBeenCalled()

    fillStudentForm(dialog)
    fireEvent.submit(form)
    fireEvent.submit(form)
    expect(apiRequest).toHaveBeenCalledTimes(1)
    expect(apiRequest).toHaveBeenCalledWith('students', expect.objectContaining({ method: 'POST', token: 'admin-token' }))

    resolveRequest({ ...student, student_id: 8, student_number: 'PT-008', full_name: 'Ravi Kumar' })
    expect(await screen.findByRole('status')).toHaveTextContent('Ravi Kumar saved successfully.')
    await waitFor(() => expect(loadStudentList).toHaveBeenCalledTimes(2))
  })

  it('surfaces duplicate API responses and edits status through the approved PATCH', async () => {
    const user = userEvent.setup()
    renderStudents()
    await screen.findByText('Data Engineering')
    await user.click(screen.getByRole('button', { name: 'Edit Asha Patel' }))
    const dialog = screen.getByRole('dialog', { name: 'Edit student' })
    await user.selectOptions(within(dialog).getByLabelText('Record status'), 'archived')
    apiRequest.mockResolvedValueOnce({ ...student, status: 'archived' })
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    expect(apiRequest).toHaveBeenCalledWith('students/7', expect.objectContaining({
      method: 'PATCH',
      body: expect.stringContaining('"status":"archived"'),
    }))
    expect(await screen.findByRole('status')).toHaveTextContent('Asha Patel updated successfully.')

    await user.click(screen.getByRole('button', { name: 'Add student' }))
    const createDialog = screen.getByRole('dialog', { name: 'Add student' })
    fillStudentForm(createDialog)
    apiRequest.mockRejectedValueOnce(new ApiError('Request failed', { status: 409, code: 'duplicate_student_number' }))
    await user.click(within(createDialog).getByRole('button', { name: 'Add student' }))
    expect(await within(createDialog).findByRole('alert')).toHaveTextContent('That student number is already in use.')
  })

  it('shows fee, payment, project, and certificate history from the profile response', async () => {
    loadStudentProfile.mockResolvedValue({
      student,
      history: [{
        enrollment_id: 9,
        enrollment_number: 'EN-009',
        student_id: student.student_id,
        program_id: 2,
        batch_id: 4,
        status: 'completed',
        starts_on: '2025-01-01',
        ends_on: '2025-06-01',
        program: { name: 'Data Engineering' },
        batch: { name: 'Cohort A' },
        fees: { effective_fee: '1000.00', net_paid: '750.00', pending_balance: '250.00' },
        feeTerms: [{ fee_term_id: 1, effective_from: '2025-01-01T00:00:00Z', agreed_amount: '1000.00', reason: 'Initial fee' }],
        feeAdjustments: [],
        payments: [{ payment_id: 12, paid_at: '2025-02-01T00:00:00Z', amount: '750.00', net_amount: '750.00', adjusted_amount: '0.00', payment_method: 'upi', derived_status: 'posted', payment_reference: 'UPI-1', adjustments: [{ adjustment_id: 4, payment_id: 12, adjustment_type: 'refund', amount: '25.00', occurred_at: '2025-03-01T00:00:00Z', reason: 'Duplicate transfer', recorded_by: 1 }] }],
        projects: [{ project_assignment_id: 1, project_id: 5, project_name: 'Student portal', status: 'completed', completed_at: '2025-05-01T00:00:00Z' }],
        certificates: [{ certificate_id: 3, certificate_number: 'CERT-3', certificate_type: 'Internship', issued_at: '2025-06-02T00:00:00Z', derived_status: 'revoked' }],
      }],
    })
    renderProfile()

    expect(await screen.findByRole('heading', { name: 'Asha Patel' })).toBeInTheDocument()
    expect(screen.getByText('EN-009')).toBeInTheDocument()
    expect(screen.getByText('Student portal')).toBeInTheDocument()
    expect(screen.getByText('CERT-3')).toBeInTheDocument()
    expect(screen.getByText('Payment history')).toBeInTheDocument()
    expect(screen.getByText('Duplicate transfer')).toBeInTheDocument()
    expect(screen.getByText(/not calculated in this profile/i)).toBeInTheDocument()
  })

  it('renders retryable student API errors', async () => {
    loadStudentList.mockRejectedValueOnce(new Error('Backend unavailable'))
    renderStudents()
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('shows loading and empty states when the server has no matching students', async () => {
    let resolveList
    loadStudentList.mockReturnValueOnce(new Promise((resolve) => { resolveList = resolve }))
    renderStudents()
    expect(screen.getByRole('status')).toHaveTextContent('Loading students')

    await act(async () => {
      resolveList({ items: [], total: 0, page: 1, page_size: 20, pages: 0 })
    })
    expect(await screen.findByText('No students in this view')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Add student' })).toHaveLength(2)
  })
})
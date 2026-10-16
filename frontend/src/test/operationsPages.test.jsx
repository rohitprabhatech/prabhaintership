import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../auth/AuthProvider.jsx', () => ({ useAuth: () => ({ token: 'admin-token' }) }))

vi.mock('../lib/api.js', () => {
  class MockApiError extends Error {
    constructor(message, details = {}) { super(message); Object.assign(this, details) }
  }
  return { ApiError: MockApiError, apiRequest: vi.fn() }
})

vi.mock('../lib/adminData.js', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual, getAllPages: vi.fn() }
})

vi.mock('../lib/financeData.js', () => ({
  loadFinanceEnrollments: vi.fn(),
  loadFinanceDetails: vi.fn(),
}))

import { apiRequest } from '../lib/api.js'
import { getAllPages } from '../lib/adminData.js'
import { loadFinanceDetails, loadFinanceEnrollments } from '../lib/financeData.js'
import BatchesPage from '../pages/BatchesPage.jsx'
import CertificatesPage from '../pages/CertificatesPage.jsx'
import EnrollmentsPage from '../pages/EnrollmentsPage.jsx'
import FinancePage from '../pages/FinancePage.jsx'
import ProgramsPage from '../pages/ProgramsPage.jsx'
import ProjectsPage from '../pages/ProjectsPage.jsx'
import ReportsPage from '../pages/ReportsPage.jsx'

const program = { program_id: 1, program_code: 'PY-01', name: 'Python Internship', description: null, status: 'active', updated_at: '2026-01-01T00:00:00Z' }
const batch = { batch_id: 4, program_id: 1, batch_code: 'COHORT-A', name: 'Cohort A', starts_on: '2026-01-01', ends_on: '2026-06-30', capacity: 20, status: 'active' }
const enrollment = { enrollment_id: 9, enrollment_number: 'EN-009', student_id: 3, program_id: 1, batch_id: 4, status: 'active', starts_on: '2026-01-01', ends_on: null, created_at: '2026-01-01T00:00:00Z' }
const certificate = { certificate_id: 5, enrollment_id: 9, certificate_number: 'CERT-005', certificate_type: 'Internship', issued_at: '2026-06-01T00:00:00Z', derived_status: 'issued', full_name: 'Asha Patel', enrollment_number: 'EN-009' }

function page(items, total = items.length) {
  return { items, total, page: 1, page_size: 20, pages: total ? 1 : 0 }
}

function renderPage(Component) {
  return render(<MemoryRouter><Component /></MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  getAllPages.mockImplementation(async (path) => {
    if (path === 'programs') return page([program])
    if (path === 'batches') return page([batch])
    if (path === 'students') return page([{ student_id: 3, student_number: 'PT-003', full_name: 'Asha Patel', status: 'active' }])
    if (path === 'enrollments') return page([enrollment])
    return page([])
  })
  apiRequest.mockImplementation(async (path, options = {}) => {
    if (path.startsWith('programs?')) return page([program])
    if (path.startsWith('batches?')) return page([batch])
    if (path.startsWith('enrollments?')) return page([enrollment])
    if (path.startsWith('project-assignments?')) return page([{ project_assignment_id: 11, project_id: 6, enrollment_id: 9, status: 'assigned', assigned_at: '2026-02-01T00:00:00Z', completed_at: null, project_name: 'Portal rebuild' }])
    if (path.startsWith('projects?')) return page([{ project_id: 6, project_code: 'PORTAL', name: 'Portal rebuild', status: 'active' }])
    if (path.startsWith('certificates?')) return page([certificate])
    if (path === 'batches/4/roster') return { ...batch, active_enrollment_count: 1, students: [{ enrollment_id: 9, enrollment_number: 'EN-009', enrollment_status: 'active', student_id: 3, student_number: 'PT-003', full_name: 'Asha Patel', email: 'asha@example.com' }] }
    if (path === 'programs/1') return { ...program, status: JSON.parse(options.body).status }
    if (path === 'batches/4') return { ...batch, status: JSON.parse(options.body).status }
    if (path === 'enrollments' && options.method === 'POST') return { ...enrollment, enrollment_id: 10, enrollment_number: 'EN-010' }
    if (path === 'enrollments/9/status') return { ...enrollment, status: JSON.parse(options.body).status }
    if (path === 'enrollments/9/projects') return { project_assignment_id: 12, project_name: 'Portal rebuild' }
    if (path === 'project-assignments/11/status') return { project_assignment_id: 11, project_name: 'Portal rebuild', status: JSON.parse(options.body).status }
    if (path === 'certificates' && options.method === 'POST') return { ...certificate, certificate_id: 8, certificate_number: 'CERT-008' }
    if (path === 'certificates/5/revocation') return { certificate_event_id: 3 }
    if (path === 'certificates/5') return certificate
    if (path === 'certificates/5/events') return []
    if (path === 'enrollments/9/payments') return { payment_id: 18 }
    return {}
  })
  loadFinanceEnrollments.mockResolvedValue(page([{ ...enrollment, student: { full_name: 'Asha Patel', student_number: 'PT-003' }, program, fees: { effective_fee: '1000.00', net_paid: '250.00', pending_balance: '750.00' } }]))
  loadFinanceDetails.mockResolvedValue({
    fees: { base_fee: '1000.00', adjustments_total: '0.00', effective_fee: '1000.00', net_paid: '250.00', pending_balance: '750.00' },
    feeTerms: [],
    feeAdjustments: [],
    payments: [],
  })
})

describe('remaining admin workflows', () => {
  it('confirms program status changes before sending the documented PATCH', async () => {
    const user = userEvent.setup()
    renderPage(ProgramsPage)
    await screen.findByText('Python Internship')
    await user.click(screen.getByRole('button', { name: 'Edit Python Internship' }))
    const dialog = screen.getByRole('dialog', { name: 'Edit program' })
    await user.selectOptions(within(dialog).getByLabelText('Status'), 'inactive')
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    const confirmation = screen.getByRole('alertdialog')
    expect(apiRequest).not.toHaveBeenCalledWith('programs/1', expect.anything())
    await user.click(within(confirmation).getByRole('button', { name: 'Save status change' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('programs/1', expect.objectContaining({ method: 'PATCH', body: expect.stringContaining('"status":"inactive"') })))
  })

  it('loads a batch roster and confirms batch status changes', async () => {
    const user = userEvent.setup()
    renderPage(BatchesPage)
    await screen.findByText('Cohort A')
    await user.click(screen.getByRole('button', { name: 'View Cohort A roster' }))
    expect(await screen.findByText('Asha Patel')).toBeInTheDocument()
    await user.click(within(screen.getByRole('dialog', { name: 'Cohort A roster' })).getByRole('button', { name: 'Close' }))
    await user.click(screen.getByRole('button', { name: 'Edit Cohort A' }))
    const editor = screen.getByRole('dialog', { name: 'Edit batch' })
    await user.selectOptions(within(editor).getByLabelText('Status'), 'cancelled')
    await user.click(within(editor).getByRole('button', { name: 'Save changes' }))
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Save status change' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('batches/4', expect.objectContaining({ method: 'PATCH', body: expect.stringContaining('"status":"cancelled"') })))
  })

  it('confirms enrollment creation and sends the initial fee as a decimal string', async () => {
    const user = userEvent.setup()
    renderPage(EnrollmentsPage)
    await screen.findByText('EN-009')
    await user.click(screen.getByRole('button', { name: 'New enrollment' }))
    const dialog = screen.getByRole('dialog', { name: 'Create enrollment' })
    fireEvent.change(within(dialog).getByLabelText('Enrollment number'), { target: { value: 'EN-010' } })
    await user.selectOptions(within(dialog).getByLabelText('Active student'), '3')
    await user.selectOptions(within(dialog).getByLabelText('Active program'), '1')
    await user.selectOptions(within(dialog).getByLabelText(/Eligible active batch/), '4')
    fireEvent.change(within(dialog).getByLabelText('Starts on'), { target: { value: '2026-07-01' } })
    fireEvent.change(within(dialog).getByLabelText('Initial agreed fee (INR)'), { target: { value: '12500.50' } })
    await user.click(within(dialog).getByRole('button', { name: 'Review enrollment' }))
    const confirmation = within(dialog).getByRole('alertdialog')
    expect(apiRequest).not.toHaveBeenCalledWith('enrollments', expect.objectContaining({ method: 'POST' }))
    await user.click(within(confirmation).getByRole('button', { name: 'Create enrollment' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('enrollments', expect.objectContaining({ method: 'POST', body: expect.stringContaining('"agreed_fee_amount":"12500.50"') })))
  })

  it('requires confirmation before an enrollment can enter a terminal state', async () => {
    const user = userEvent.setup()
    renderPage(EnrollmentsPage)
    await screen.findByText('EN-009')
    await user.click(screen.getByRole('button', { name: 'completed' }))
    const confirmation = screen.getByRole('alertdialog')
    expect(apiRequest).not.toHaveBeenCalledWith('enrollments/9/status', expect.anything())
    await user.click(within(confirmation).getByRole('button', { name: 'Mark completed' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('enrollments/9/status', expect.objectContaining({ method: 'PATCH', body: '{"status":"completed"}' })))
  })

  it('records a payment only after confirmation and sends an idempotency key', async () => {
    const user = userEvent.setup()
    renderPage(FinancePage)
    await screen.findByText('₹750.00')
    await user.click(screen.getByRole('button', { name: 'View history' }))
    await screen.findByText('Pending balance')
    await user.click(screen.getByRole('button', { name: 'Record payment' }))
    const paymentDialog = screen.getAllByRole('dialog').at(-1)
    fireEvent.change(within(paymentDialog).getByLabelText('Amount (INR)'), { target: { value: '100.00' } })
    await user.click(within(paymentDialog).getByRole('button', { name: 'Review action' }))
    const confirmation = within(paymentDialog).getByRole('alertdialog')
    expect(apiRequest).not.toHaveBeenCalledWith('enrollments/9/payments', expect.anything())
    await user.click(within(confirmation).getByRole('button', { name: 'Record payment' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('enrollments/9/payments', expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('"amount":"100.00"'),
      headers: { 'Idempotency-Key': expect.stringMatching(/^[0-9a-f-]{36}$/i) },
    })))
  })

  it('confirms project progress transitions before PATCHing supported states', async () => {
    const user = userEvent.setup()
    renderPage(ProjectsPage)
    await user.click(await screen.findByRole('button', { name: 'in progress' }))
    const confirmation = screen.getByRole('alertdialog')
    expect(apiRequest).not.toHaveBeenCalledWith('project-assignments/11/status', expect.anything())
    await user.click(within(confirmation).getByRole('button', { name: 'Set in progress' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('project-assignments/11/status', expect.objectContaining({ method: 'PATCH', body: '{"status":"in_progress"}' })))
  })

  it('issues a certificate only after confirmation and API success', async () => {
    const user = userEvent.setup()
    renderPage(CertificatesPage)
    await screen.findByText('CERT-005')
    await user.click(screen.getByRole('button', { name: 'Issue certificate' }))
    const dialog = screen.getByRole('dialog', { name: 'Issue certificate' })
    await user.selectOptions(within(dialog).getByLabelText('Enrollment'), '9')
    fireEvent.change(within(dialog).getByLabelText('Certificate number'), { target: { value: 'CERT-008' } })
    fireEvent.change(within(dialog).getByLabelText('Certificate type'), { target: { value: 'Internship' } })
    await user.click(within(dialog).getByRole('button', { name: 'Review action' }))
    const confirmation = within(dialog).getByRole('alertdialog')
    expect(apiRequest).not.toHaveBeenCalledWith('certificates', expect.objectContaining({ method: 'POST' }))
    await user.click(within(confirmation).getByRole('button', { name: 'Issue certificate' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('certificates', expect.objectContaining({ method: 'POST', body: expect.stringContaining('"certificate_number":"CERT-008"') })))
    expect(await screen.findByText(/Certificate issued successfully by the API/)).toBeInTheDocument()
  })

  it('confirms certificate revocation and reports unavailable export instead of fabricating CSV', async () => {
    const user = userEvent.setup()
    renderPage(CertificatesPage)
    await screen.findByText('CERT-005')
    await user.click(screen.getByRole('button', { name: 'Revoke' }))
    const dialog = screen.getByRole('dialog', { name: 'Revoke certificate' })
    fireEvent.change(within(dialog).getByLabelText('Reason'), { target: { value: 'Issued to the wrong enrollment' } })
    await user.click(within(dialog).getByRole('button', { name: 'Review action' }))
    const confirmation = within(dialog).getByRole('alertdialog')
    await user.click(within(confirmation).getByRole('button', { name: 'Revoke certificate' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('certificates/5/revocation', expect.objectContaining({ method: 'POST', body: '{"reason":"Issued to the wrong enrollment"}' })))

    renderPage(ReportsPage)
    expect(screen.getByText('CSV export unavailable')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /export|download/i })).not.toBeInTheDocument()
  })
})
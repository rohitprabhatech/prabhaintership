import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../auth/AuthProvider.jsx', () => ({
  useAuth: () => ({ token: 'admin-token' }),
}))

vi.mock('../lib/api.js', () => ({
  apiRequest: vi.fn(),
}))

vi.mock('../lib/adminData.js', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    getAllPages: vi.fn(),
  }
})

import { apiRequest } from '../lib/api.js'
import { getAllPages } from '../lib/adminData.js'
import StudentForm from '../components/StudentForm.jsx'
import BatchDetailsPage from '../pages/BatchDetailsPage.jsx'

const programA = { program_id: 1, program_code: 'PRG-2026-0001', name: 'Python Internship', status: 'active' }
const programB = { program_id: 2, program_code: 'PRG-2026-0002', name: 'Data Internship', status: 'active' }
const batchA = { batch_id: 4, program_id: 1, batch_code: 'BAT-2026-0001', name: 'Python Cohort', starts_on: '2026-11-01', ends_on: '2027-01-31', status: 'planned' }
const batchB = { batch_id: 5, program_id: 2, batch_code: 'BAT-2026-0002', name: 'Data Cohort', starts_on: '2026-11-10', ends_on: '2027-02-10', status: 'active' }

beforeEach(() => {
  vi.clearAllMocks()
  getAllPages.mockImplementation(async (path, params) => {
    if (path === 'programs') return { items: [programA, programB], pages: 1 }
    if (path === 'batches' && params.program_id === '1') {
      return params.status === 'planned' ? { items: [batchA], pages: 1 } : { items: [], pages: 0 }
    }
    if (path === 'batches' && params.program_id === '2') {
      return params.status === 'active' ? { items: [batchB], pages: 1 } : { items: [], pages: 0 }
    }
    return { items: [], pages: 0 }
  })
})

describe('batch-wise student management', () => {
  it('creates a student with one selected program, batch, and initial fee', async () => {
    const user = userEvent.setup()
    apiRequest.mockResolvedValue({
      student_id: 9,
      student_number: 'STU-2026-000009',
      full_name: 'Asha Patel',
      status: 'active',
    })
    const onSaved = vi.fn()
    render(<StudentForm token="admin-token" onClose={vi.fn()} onSaved={onSaved} />)

    const programSelect = await screen.findByLabelText('Active internship program')
    const batchSelect = screen.getByLabelText('Batch')
    expect(batchSelect).toBeDisabled()
    await user.selectOptions(programSelect, '1')
    await waitFor(() => expect(batchSelect).toBeEnabled())
    expect(within(batchSelect).getByRole('option', { name: /Python Cohort/ })).toBeInTheDocument()
    await user.selectOptions(batchSelect, '4')
    await user.type(screen.getByLabelText('Full name'), 'Asha Patel')
    await user.type(screen.getByLabelText('Agreed fee (INR)'), '12000.00')

    await user.click(screen.getByRole('button', { name: 'Add student' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('students', expect.objectContaining({
      method: 'POST',
      token: 'admin-token',
      body: expect.stringContaining('"program_id":1'),
    })))
    const payload = JSON.parse(apiRequest.mock.calls[0][1].body)
    expect(payload).toMatchObject({
      batch_id: 4,
      agreed_fee_amount: '12000',
      enrollment_starts_on: '2026-11-01',
    })
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ student_number: 'STU-2026-000009' }))
  })

  it('clears a selected batch when the program changes', async () => {
    const user = userEvent.setup()
    render(<StudentForm token="admin-token" onClose={vi.fn()} onSaved={vi.fn()} />)
    const programSelect = await screen.findByLabelText('Active internship program')
    const batchSelect = screen.getByLabelText('Batch')
    await user.selectOptions(programSelect, '1')
    await waitFor(() => expect(within(batchSelect).getByRole('option', { name: /Python Cohort/ })).toBeInTheDocument())
    await user.selectOptions(batchSelect, '4')
    await user.selectOptions(programSelect, '2')
    await waitFor(() => expect(batchSelect).toHaveValue(''))
    await waitFor(() => expect(within(batchSelect).getByRole('option', { name: /Data Cohort/ })).toBeInTheDocument())
    expect(within(batchSelect).queryByRole('option', { name: /Python Cohort/ })).not.toBeInTheDocument()
  })

  it('shows the paginated batch roster with real enrollment and fee details', async () => {
    apiRequest.mockImplementation(async (path) => {
      if (path === 'batches/4') return { ...batchA, capacity: 20 }
      if (path === 'programs/1') return programA
      if (path.startsWith('batches/4/students?')) {
        return {
          batch_id: 4,
          program_id: 1,
          batch_code: batchA.batch_code,
          name: batchA.name,
          starts_on: batchA.starts_on,
          ends_on: batchA.ends_on,
          capacity: 20,
          enrollment_count: 2,
          active_enrollment_count: 1,
          unique_active_student_count: 1,
          students: [{
            enrollment_id: 12,
            enrollment_number: 'ENR-2026-000012',
            enrollment_status: 'active',
            enrollment_starts_on: '2026-11-01',
            enrollment_ends_on: null,
            student_id: 9,
            student_number: 'STU-2026-000009',
            full_name: 'Asha Patel',
            email: 'asha@example.com',
            phone: '+91 98765 43210',
            fee_summary: { effective_fee: '12000.00', net_paid: '5000.00', pending_balance: '7000.00', currency: 'INR' },
          }],
          total: 1,
          page: 1,
          page_size: 20,
          pages: 1,
        }
      }
      return {}
    })
    render(
      <MemoryRouter initialEntries={['/batches/4']}>
        <Routes><Route path="/batches/:batchId" element={<BatchDetailsPage />} /></Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByRole('heading', { name: 'Python Cohort' })).toBeInTheDocument()
    expect(screen.getByText('Unique active students').parentElement).toHaveTextContent('1')
    expect(screen.getByRole('link', { name: /Asha Patel STU-2026-000009/ })).toHaveAttribute('href', '/students/9')
    expect(screen.getByText(/₹7,000\.00 pending/)).toBeInTheDocument()
    expect(apiRequest).toHaveBeenCalledWith('batches/4/students?page=1&page_size=20&status=all', expect.objectContaining({ token: 'admin-token' }))
  })
})

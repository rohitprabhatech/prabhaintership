import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Mail, Phone, SquarePen } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import StudentForm from '../components/StudentForm.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/ui.jsx'
import { formatInrMinorUnits, decimalToMinorUnits } from '../lib/adminData.js'
import { loadStudentProfile } from '../lib/studentData.js'

function displayDate(value) {
  return value ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(value)) : '—'
}

function ProfileHistory({ enrollment }) {
  const feeColumns = [
    { key: 'effective_from', label: 'Effective', render: (row) => displayDate(row.effective_from) },
    { key: 'agreed_amount', label: 'Agreed fee', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.agreed_amount)) },
    { key: 'reason', label: 'Reason' },
  ]
  const paymentColumns = [
    { key: 'paid_at', label: 'Paid', render: (row) => displayDate(row.paid_at) },
    { key: 'amount', label: 'Amount', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.amount)) },
    { key: 'net_amount', label: 'Net amount', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.net_amount)) },
    { key: 'adjusted_amount', label: 'Adjusted', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.adjusted_amount)) },
    { key: 'payment_method', label: 'Method', render: (row) => row.payment_method.replaceAll('_', ' ') },
    { key: 'derived_status', label: 'Status', render: (row) => <StatusBadge status={row.derived_status} /> },
    { key: 'payment_reference', label: 'Reference', render: (row) => row.payment_reference || '—' },
  ]
  const projectColumns = [
    { key: 'project_name', label: 'Project', render: (row) => row.project_name || `Project ${row.project_id}` },
    { key: 'status', label: 'Progress', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'completed_at', label: 'Completed', render: (row) => displayDate(row.completed_at) },
  ]
  const certificateColumns = [
    { key: 'certificate_number', label: 'Certificate' },
    { key: 'certificate_type', label: 'Type' },
    { key: 'issued_at', label: 'Issued', render: (row) => displayDate(row.issued_at) },
    { key: 'derived_status', label: 'Status', render: (row) => <StatusBadge status={row.derived_status} /> },
  ]
  const paymentAdjustmentColumns = [
    { key: 'occurred_at', label: 'Recorded', render: (row) => displayDate(row.occurred_at) },
    { key: 'adjustment_type', label: 'Type', render: (row) => row.adjustment_type },
    { key: 'amount', label: 'Amount', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.amount)) },
    { key: 'reason', label: 'Reason' },
  ]
  const paymentAdjustments = enrollment.payments.flatMap((payment) => payment.adjustments || [])

  return (
    <section className="rounded-lg border border-line bg-white p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
        <div>
          <h3 className="font-semibold text-ink">{enrollment.enrollment_number}</h3>
          <p className="mt-1 text-sm text-muted">{enrollment.program?.name || 'Program unavailable'} · {enrollment.batch?.name || 'No batch'}</p>
          <p className="mt-1 text-xs text-muted">{displayDate(enrollment.starts_on)} to {displayDate(enrollment.ends_on)}</p>
        </div>
        <StatusBadge status={enrollment.status} />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {[
          ['Effective fee', enrollment.fees.effective_fee],
          ['Net paid', enrollment.fees.net_paid],
          ['Pending balance', enrollment.fees.pending_balance],
        ].map(([label, value]) => (
          <div key={label} className="rounded-md bg-canvas p-3">
            <p className="text-xs font-medium text-muted">{label}</p>
            <p className="mt-1 tabular-nums font-semibold text-ink">{formatInrMinorUnits(decimalToMinorUnits(value))}</p>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-muted">Values are from the API fee summary, not calculated in this profile.</p>

      <div className="mt-6 grid gap-6">
        <section aria-label={`Fee terms for ${enrollment.enrollment_number}`}>
          <h4 className="mb-2 text-sm font-semibold text-ink">Fee terms</h4>
          <DataTable columns={feeColumns} rows={enrollment.feeTerms} getRowKey={(row) => row.fee_term_id} caption="Fee term history" emptyMessage="No fee-term history." />
          {enrollment.feeAdjustments.length > 0 && (
            <ul className="mt-2 divide-y divide-line rounded-md border border-line px-3 text-sm">
              {enrollment.feeAdjustments.map((adjustment) => (
                <li key={adjustment.fee_adjustment_id} className="flex flex-wrap justify-between gap-2 py-2">
                  <span className="capitalize">{adjustment.adjustment_type.replaceAll('_', ' ')} · {adjustment.reason}</span>
                  <span className="tabular-nums">{formatInrMinorUnits(decimalToMinorUnits(adjustment.amount))}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section aria-label={`Payments for ${enrollment.enrollment_number}`}>
          <h4 className="mb-2 text-sm font-semibold text-ink">Payments and adjustments</h4>
          <DataTable columns={paymentColumns} rows={enrollment.payments} getRowKey={(row) => row.payment_id} caption="Payment history" emptyMessage="No payments recorded." />
          {paymentAdjustments.length > 0 && <div className="mt-2"><DataTable columns={paymentAdjustmentColumns} rows={paymentAdjustments} getRowKey={(row) => row.adjustment_id} caption="Payment adjustment events" /></div>}
        </section>
        <section aria-label={`Projects for ${enrollment.enrollment_number}`}>
          <h4 className="mb-2 text-sm font-semibold text-ink">Project completion</h4>
          <DataTable columns={projectColumns} rows={enrollment.projects} getRowKey={(row) => row.project_assignment_id} caption="Project assignment history" emptyMessage="No projects assigned." />
        </section>
        <section aria-label={`Certificates for ${enrollment.enrollment_number}`}>
          <h4 className="mb-2 text-sm font-semibold text-ink">Certificates</h4>
          <DataTable columns={certificateColumns} rows={enrollment.certificates} getRowKey={(row) => row.certificate_id} caption="Certificate history" emptyMessage="No certificates issued." />
        </section>
      </div>
    </section>
  )
}

export default function StudentProfilePage() {
  const { studentId } = useParams()
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [success, setSuccess] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    loadStudentProfile(studentId, token)
      .then((result) => { if (active) setData(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Student profile could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [studentId, token, reloadKey])

  function saveStudent(student) {
    setEditing(false)
    setSuccess(`${student.full_name} updated successfully.`)
    setReloadKey((key) => key + 1)
  }

  return (
    <div className="animate-enter">
      <Link to="/students" className="mb-5 inline-flex min-h-9 items-center gap-2 text-sm font-semibold text-muted hover:text-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500">
        <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Students
      </Link>
      {loading ? <LoadingState label="Loading student profile and history" /> : error ? (
        <ErrorState title="Student profile could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} />
      ) : (
        <>
          {success && <p role="status" aria-live="polite" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">{success}</p>}
          <header className="mb-6 flex flex-wrap items-start justify-between gap-4 rounded-lg border border-line bg-white p-5 sm:p-7">
            <div>
              <p className="text-xs font-bold uppercase text-orange-700">Student profile</p>
              <h1 className="mt-2 font-display text-4xl text-ink">{data.student.full_name}</h1>
              <p className="mt-1 font-medium text-muted">{data.student.student_number}</p>
              <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
                {data.student.email ? <a className="inline-flex items-center gap-2 hover:text-orange-700" href={`mailto:${data.student.email}`}><Mail aria-hidden="true" className="h-4 w-4" />{data.student.email}</a> : <span>No email provided</span>}
                {data.student.phone ? <a className="inline-flex items-center gap-2 hover:text-orange-700" href={`tel:${data.student.phone}`}><Phone aria-hidden="true" className="h-4 w-4" />{data.student.phone}</a> : <span>No phone provided</span>}
              </div>
              <div className="mt-4 flex items-center gap-3"><StatusBadge status={data.student.status} /><span className="text-xs text-muted">Updated {displayDate(data.student.updated_at)}</span></div>
            </div>
            <Button variant="secondary" onClick={() => setEditing(true)}><SquarePen aria-hidden="true" className="h-4 w-4" /> Edit profile</Button>
          </header>

          <div className="mb-4 flex items-end justify-between gap-3">
            <div><h2 className="text-lg font-semibold text-ink">Enrollment history</h2><p className="mt-1 text-sm text-muted">Read-only program, fee, payment, project, and certificate records.</p></div>
            <span className="text-sm text-muted">{data.history.length} {data.history.length === 1 ? 'enrollment' : 'enrollments'}</span>
          </div>
          {data.history.length ? <div className="grid gap-4">{data.history.map((enrollment) => <ProfileHistory key={enrollment.enrollment_id} enrollment={enrollment} />)}</div> : (
            <EmptyState title="No enrollment history" description="This student does not have any enrollment records yet." />
          )}
        </>
      )}
      {editing && data && <StudentForm student={data.student} token={token} onClose={() => setEditing(false)} onSaved={saveStudent} />}
    </div>
  )
}
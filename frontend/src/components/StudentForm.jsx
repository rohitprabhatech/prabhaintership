import { useEffect, useRef, useState } from 'react'
import { ApiError, apiRequest } from '../lib/api.js'
import { getAllPages } from '../lib/adminData.js'
import ConfirmDialog from './ConfirmDialog.jsx'
import { Button, Modal, TextField } from './ui.jsx'

function getConflictMessage(error) {
  if (error.code === 'duplicate_student_email') return 'That email address is already in use.'
  if (error.code === 'student_conflict') return 'Student details conflict with an existing record.'
  return error.message || 'The student record could not be saved.'
}

export default function StudentForm({ student, token, onClose, onSaved }) {
  const submitting = useRef(false)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [confirmation, setConfirmation] = useState(null)
  const [values, setValues] = useState({
    full_name: student?.full_name || '',
    email: student?.email || '',
    phone: student?.phone || '',
    address: student?.address || '',
    city: student?.city || '',
    state: student?.state || '',
    postal_code: student?.postal_code || '',
    institution_name: student?.institution_name || '',
    course: student?.course || '',
    internship_domain: student?.internship_domain || '',
    status: student?.status || 'active',
    program_id: '',
    batch_id: '',
    enrollment_starts_on: '',
    agreed_fee_amount: '',
    fee_reason: 'Initial agreed fee',
  })
  const [programs, setPrograms] = useState([])
  const [batches, setBatches] = useState([])
  const [programsLoading, setProgramsLoading] = useState(false)
  const [batchesLoading, setBatchesLoading] = useState(false)
  const [optionsError, setOptionsError] = useState('')

  useEffect(() => {
    if (student) return undefined
    let active = true
    setProgramsLoading(true)
    getAllPages('programs', { status: 'active' }, token)
      .then((result) => { if (active) setPrograms(result.items) })
      .catch((cause) => { if (active) setOptionsError(cause.message || 'Programs could not be loaded.') })
      .finally(() => { if (active) setProgramsLoading(false) })
    return () => { active = false }
  }, [student, token])

  useEffect(() => {
    if (student || !values.program_id) {
      setBatches([])
      return undefined
    }
    let active = true
    setBatchesLoading(true)
    setOptionsError('')
    Promise.all([
      getAllPages('batches', { program_id: values.program_id, status: 'planned' }, token),
      getAllPages('batches', { program_id: values.program_id, status: 'active' }, token),
    ])
      .then(([planned, activeBatches]) => {
        if (active) setBatches([...planned.items, ...activeBatches.items])
      })
      .catch((cause) => {
        if (active) setOptionsError(cause.message || 'Eligible batches could not be loaded.')
      })
      .finally(() => { if (active) setBatchesLoading(false) })
    return () => { active = false }
  }, [student, token, values.program_id])

  function updateField(event) {
    const { name, value } = event.target
    setValues((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: '' }))
  }

  function updateProgram(event) {
    setValues((current) => ({
      ...current,
      program_id: event.target.value,
      batch_id: '',
      enrollment_starts_on: '',
      agreed_fee_amount: '',
    }))
    setBatches([])
    setFieldErrors((current) => ({ ...current, program_id: '', batch_id: '' }))
  }

  function updateBatch(event) {
    const batch = batches.find((item) => String(item.batch_id) === event.target.value)
    setValues((current) => ({
      ...current,
      batch_id: event.target.value,
      enrollment_starts_on: batch?.starts_on || '',
    }))
    setFieldErrors((current) => ({ ...current, batch_id: '', agreed_fee_amount: '' }))
  }

  async function save(payload) {
    if (submitting.current) return
    submitting.current = true
    setSaving(true)
    setFormError('')
    setFieldErrors({})
    try {
      const result = await apiRequest(student ? `students/${student.student_id}` : 'students', {
        token,
        method: student ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
      })
      onSaved(result)
    } catch (error) {
      if (error instanceof ApiError && error.errors?.length) {
        const errors = {}
        for (const issue of error.errors) {
          const field = issue.location?.at(-1)
          if (['full_name', 'email', 'phone', 'address', 'city', 'state', 'postal_code', 'institution_name', 'course', 'internship_domain', 'status'].includes(field)) {
            errors[field] = issue.message
          }
        }
        setFieldErrors(errors)
      }
      setFormError(error instanceof ApiError && error.status === 409
        ? getConflictMessage(error)
        : error.message || 'The student record could not be saved.')
    } finally {
      submitting.current = false
      setSaving(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const nextErrors = {}
    if (!values.full_name.trim()) nextErrors.full_name = 'Enter the student name.'
    if (values.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
      nextErrors.email = 'Enter a valid email address.'
    }
    if (values.batch_id) {
      if (!values.program_id) nextErrors.program_id = 'Select a program for this enrollment.'
      if (!values.agreed_fee_amount || !/^\d+(?:\.\d{1,2})?$/.test(values.agreed_fee_amount) || Number(values.agreed_fee_amount) <= 0) {
        nextErrors.agreed_fee_amount = 'Enter an agreed fee greater than zero with up to two decimal places.'
      }
    }
    if (Object.keys(nextErrors).length) {
      setFieldErrors(nextErrors)
      return
    }

    const payload = {
      full_name: values.full_name.trim(),
      email: values.email.trim() || null,
      phone: values.phone.trim() || null,
      address: values.address.trim() || null,
      city: values.city.trim() || null,
      state: values.state.trim() || null,
      postal_code: values.postal_code.trim() || null,
      institution_name: values.institution_name.trim() || null,
      course: values.course.trim() || null,
      internship_domain: values.internship_domain.trim() || null,
    }
    if (!student && values.batch_id) {
      payload.program_id = Number(values.program_id)
      payload.batch_id = Number(values.batch_id)
      payload.enrollment_starts_on = values.enrollment_starts_on || null
      payload.agreed_fee_amount = values.agreed_fee_amount
      payload.fee_reason = values.fee_reason.trim() || 'Initial agreed fee'
    }
    if (student) payload.status = values.status
    if (student && student.status !== 'archived' && values.status === 'archived') {
      setConfirmation(payload)
      return
    }
    await save(payload)
  }

  return (
    <Modal title={student ? 'Edit student' : 'Add student'} onClose={saving ? () => {} : onClose}>
      <form onSubmit={handleSubmit} noValidate className="grid gap-4">
        {formError && <div role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-900">{formError}</div>}
        <p className="rounded-md bg-orange-50 px-3 py-2 text-sm text-orange-950">{student ? <>Student number: <strong>{student.student_number}</strong></> : 'A unique student number will be generated after saving.'}</p>
        <TextField id="full-name" name="full_name" label="Full name" autoComplete="name" maxLength={200} required value={values.full_name} onChange={updateField} error={fieldErrors.full_name} />
        <TextField id="student-email" name="email" label="Email address (optional)" type="email" autoComplete="email" maxLength={254} value={values.email} onChange={updateField} error={fieldErrors.email} />
        <TextField id="student-phone" name="phone" label="Phone (optional)" type="tel" autoComplete="tel" maxLength={64} value={values.phone} onChange={updateField} error={fieldErrors.phone} />
        <TextField id="student-institution" name="institution_name" label="College or institution" maxLength={200} value={values.institution_name} onChange={updateField} error={fieldErrors.institution_name} />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField id="student-course" name="course" label="Class or course" maxLength={200} value={values.course} onChange={updateField} error={fieldErrors.course} />
          <TextField id="student-domain" name="internship_domain" label="Internship domain" maxLength={120} value={values.internship_domain} onChange={updateField} error={fieldErrors.internship_domain} />
        </div>
        {!student && (
          <section className="grid gap-4 rounded-md border border-line bg-canvas p-4" aria-labelledby="initial-enrollment-heading">
            <div>
              <h3 id="initial-enrollment-heading" className="text-sm font-semibold text-ink">Initial program enrollment <span className="font-normal text-muted">(optional)</span></h3>
              <p className="mt-1 text-xs text-muted">Choose an active program and an open batch to create the enrollment and its initial fee record with this student.</p>
            </div>
            {optionsError && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-2.5 text-sm text-red-900">{optionsError}</p>}
            <div className="grid gap-1.5">
              <label htmlFor="student-program" className="text-sm font-semibold text-ink">Active internship program</label>
              <select id="student-program" value={values.program_id} onChange={updateProgram} disabled={programsLoading || programs.length === 0} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm disabled:bg-gray-100">
                <option value="">{programsLoading ? 'Loading programs…' : programs.length ? 'Select a program' : 'No active programs available'}</option>
                {programs.map((program) => <option key={program.program_id} value={program.program_id}>{program.program_code} · {program.name}</option>)}
              </select>
              {fieldErrors.program_id && <p className="text-xs text-red-700">{fieldErrors.program_id}</p>}
            </div>
            <div className="grid gap-1.5">
              <label htmlFor="student-batch" className="text-sm font-semibold text-ink">Batch</label>
              <select id="student-batch" value={values.batch_id} onChange={updateBatch} disabled={!values.program_id || batchesLoading || batches.length === 0} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm disabled:bg-gray-100">
                <option value="">{!values.program_id ? 'Select a program first' : batchesLoading ? 'Loading eligible batches…' : batches.length ? 'Select a batch (optional)' : 'No planned or active batches available'}</option>
                {batches.map((batch) => <option key={batch.batch_id} value={batch.batch_id}>{batch.batch_code} · {batch.name} ({batch.status})</option>)}
              </select>
              {fieldErrors.batch_id && <p className="text-xs text-red-700">{fieldErrors.batch_id}</p>}
            </div>
            {values.batch_id && (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  <TextField id="enrollment-starts-on" name="enrollment_starts_on" label="Enrollment starts on" type="date" required value={values.enrollment_starts_on} onChange={updateField} />
                  <TextField id="agreed-fee-amount" name="agreed_fee_amount" label="Agreed fee (INR)" type="number" min="0.01" step="0.01" required value={values.agreed_fee_amount} onChange={updateField} error={fieldErrors.agreed_fee_amount} />
                </div>
                <TextField id="fee-reason" name="fee_reason" label="Fee note" maxLength={500} value={values.fee_reason} onChange={updateField} />
              </>
            )}
          </section>
        )}
        <div className="grid gap-1.5">
          <label htmlFor="student-address" className="text-sm font-semibold text-ink">Address</label>
          <textarea id="student-address" name="address" maxLength={4000} rows={3} value={values.address} onChange={updateField} className="rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100" />
          {fieldErrors.address && <p className="text-xs text-red-700">{fieldErrors.address}</p>}
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <TextField id="student-city" name="city" label="City" maxLength={120} value={values.city} onChange={updateField} error={fieldErrors.city} />
          <TextField id="student-state" name="state" label="State" maxLength={120} value={values.state} onChange={updateField} error={fieldErrors.state} />
          <TextField id="student-postal-code" name="postal_code" label="Postal code" maxLength={32} value={values.postal_code} onChange={updateField} error={fieldErrors.postal_code} />
        </div>
        {student && (
          <div className="grid gap-1.5">
            <label htmlFor="student-status" className="text-sm font-semibold text-ink">Record status</label>
            <select id="student-status" name="status" value={values.status} onChange={updateField} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100">
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        )}
        <div className="mt-2 flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? 'Saving…' : student ? 'Save changes' : 'Add student'}</Button>
        </div>
      </form>
      {confirmation && (
        <ConfirmDialog
          title="Archive student record?"
          message={`Archive ${student.student_number} · ${student.full_name}? Its enrollment, payment, project, and certificate history will remain available.`}
          confirmLabel="Archive student"
          reasonRequired
          reasonLabel="Reason for archiving"
          onCancel={() => setConfirmation(null)}
          onConfirm={(reason) => {
            setConfirmation(null)
            save({ ...confirmation, reason })
          }}
        />
      )}
    </Modal>
  )
}
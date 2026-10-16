import { useRef, useState } from 'react'
import { ApiError, apiRequest } from '../lib/api.js'
import { Button, Modal, TextField } from './ui.jsx'

function getConflictMessage(error) {
  if (error.code === 'duplicate_student_number') return 'That student number is already in use.'
  if (error.code === 'duplicate_student_email') return 'That email address is already in use.'
  if (error.code === 'student_conflict') return 'Student details conflict with an existing record.'
  return error.message || 'The student record could not be saved.'
}

export default function StudentForm({ student, token, onClose, onSaved }) {
  const submitting = useRef(false)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [values, setValues] = useState({
    student_number: student?.student_number || '',
    full_name: student?.full_name || '',
    email: student?.email || '',
    phone: student?.phone || '',
    status: student?.status || 'active',
  })

  function updateField(event) {
    const { name, value } = event.target
    setValues((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: '' }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting.current) return
    const nextErrors = {}
    if (!values.student_number.trim()) nextErrors.student_number = 'Enter a student number.'
    if (!values.full_name.trim()) nextErrors.full_name = 'Enter the student name.'
    if (values.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
      nextErrors.email = 'Enter a valid email address.'
    }
    if (Object.keys(nextErrors).length) {
      setFieldErrors(nextErrors)
      return
    }

    submitting.current = true
    setSaving(true)
    setFormError('')
    setFieldErrors({})
    const payload = {
      student_number: values.student_number.trim(),
      full_name: values.full_name.trim(),
      email: values.email.trim() || null,
      phone: values.phone.trim() || null,
    }
    if (student) payload.status = values.status

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
          if (['student_number', 'full_name', 'email', 'phone', 'status'].includes(field)) {
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

  return (
    <Modal title={student ? 'Edit student' : 'Add student'} onClose={saving ? () => {} : onClose}>
      <form onSubmit={handleSubmit} noValidate className="grid gap-4">
        {formError && <div role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-900">{formError}</div>}
        <TextField id="student-number" name="student_number" label="Student number" autoComplete="off" maxLength={64} required value={values.student_number} onChange={updateField} error={fieldErrors.student_number} />
        <TextField id="full-name" name="full_name" label="Full name" autoComplete="name" maxLength={200} required value={values.full_name} onChange={updateField} error={fieldErrors.full_name} />
        <TextField id="student-email" name="email" label="Email address" type="email" autoComplete="email" maxLength={254} value={values.email} onChange={updateField} error={fieldErrors.email} />
        <TextField id="student-phone" name="phone" label="Phone" type="tel" autoComplete="tel" maxLength={64} value={values.phone} onChange={updateField} error={fieldErrors.phone} />
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
    </Modal>
  )
}
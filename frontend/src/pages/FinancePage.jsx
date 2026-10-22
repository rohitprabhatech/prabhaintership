import { useEffect, useRef, useState } from 'react'
import { BadgeIndianRupee, CircleDollarSign, Plus, RefreshCw } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, Modal, StatusBadge, TextField } from '../components/ui.jsx'
import { ApiError, apiRequest } from '../lib/api.js'
import { decimalToMinorUnits, formatInrMinorUnits } from '../lib/adminData.js'
import { loadFinanceDetails, loadFinanceEnrollments } from '../lib/financeData.js'

const PAGE_SIZE = 20
const paymentMethods = ['cash', 'bank_transfer', 'upi', 'card', 'cheque', 'other']

function positiveMoney(value) {
  return /^(?=.*[1-9])\d{1,12}(?:\.\d{1,2})?$/.test(value)
}

function idempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = [...bytes].map((value) => value.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function FinanceAction({ action, enrollment, payment, pendingBalance, token, onCancel, onRefresh, onSaved }) {
  const writingRef = useRef(false)
  const [writing, setWriting] = useState(false)
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState(null)
  const [values, setValues] = useState({ amount: '', reason: '', adjustment_type: 'discount', payment_method: 'upi', payment_reference: '', paid_at: '' })
  const isPayment = action === 'payment'
  const isFeeTerm = action === 'feeTerm'
  const isFeeAdjustment = action === 'feeAdjustment'
  const isPaymentAdjustment = action === 'paymentAdjustment'
  const title = isPayment ? 'Record payment' : isFeeTerm ? 'Revise fee term' : isFeeAdjustment ? 'Approve fee adjustment' : 'Refund or reverse receipt'

  function change(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  function submit(event) {
    event.preventDefault()
    if (writingRef.current) return
    if (!positiveMoney(values.amount)) {
      setError('Enter a positive amount with no more than two decimal places.')
      return
    }
    if (
      isPayment
      && pendingBalance != null
      && decimalToMinorUnits(values.amount) > decimalToMinorUnits(pendingBalance)
    ) {
      setError(
        `Payment cannot exceed the current pending balance of ${formatInrMinorUnits(decimalToMinorUnits(pendingBalance))}. Refresh the financial history if the balance may have changed.`,
      )
      return
    }
    if ((!isPayment && !values.reason.trim()) || values.reason.trim().length > 500) {
      setError('Enter a reason of 1 to 500 characters.')
      return
    }
    if (isPaymentAdjustment && values.adjustment_type === 'reversal' && decimalToMinorUnits(values.amount) !== decimalToMinorUnits(payment.net_amount)) {
      setError(`A reversal must equal the remaining receipt amount (${formatInrMinorUnits(decimalToMinorUnits(payment.net_amount))}).`)
      return
    }
    const payload = isPayment
      ? { amount: values.amount, payment_method: values.payment_method, payment_reference: values.payment_reference.trim() || null, paid_at: values.paid_at ? new Date(values.paid_at).toISOString() : null }
      : isFeeTerm
        ? { agreed_amount: values.amount, reason: values.reason.trim() }
        : isFeeAdjustment
          ? { adjustment_type: values.adjustment_type, amount: values.amount, reason: values.reason.trim() }
          : { adjustment_type: values.adjustment_type, amount: values.amount, reason: values.reason.trim() }
    setError('')
    setConfirmation({ payload, amount: values.amount, adjustmentType: values.adjustment_type })
  }

  async function confirmWrite() {
    if (!confirmation || writingRef.current) return
    writingRef.current = true
    setWriting(true)
    setError('')
    const basePath = `enrollments/${enrollment.enrollment_id}`
    const endpoint = isPayment
      ? `${basePath}/payments`
      : isFeeTerm
        ? `${basePath}/fee-terms`
        : isFeeAdjustment
          ? `${basePath}/fee-adjustments`
          : `payments/${payment.payment_id}/adjustments`
    const headers = (isPayment || isFeeAdjustment || isPaymentAdjustment)
      ? { 'Idempotency-Key': idempotencyKey() }
      : undefined
    try {
      const result = await apiRequest(endpoint, { token, method: 'POST', headers, body: JSON.stringify(confirmation.payload) })
      onSaved(result, action)
    } catch (cause) {
      setConfirmation(null)
      if (cause instanceof ApiError && cause.code === 'overpayment_rejected') {
        setError(
          `The server rejected this payment because it exceeds the current pending balance. Refresh the financial history and enter an amount no greater than Pending.${cause.requestId ? ` Reference: ${cause.requestId}.` : ''}`,
        )
        onRefresh()
      } else {
        const reference = cause instanceof ApiError && cause.code
          ? ` Error code: ${cause.code}${cause.requestId ? `; reference: ${cause.requestId}` : ''}.`
          : ''
        setError(cause instanceof ApiError && cause.status === 409
          ? `${cause.message} The server rejected this financial change; no success is recorded.${reference}`
          : `${cause.message || 'The financial request failed. No success is recorded.'}${reference}`)
      }
    } finally {
      writingRef.current = false
      setWriting(false)
    }
  }

  const confirmationMessage = isPayment
    ? `Record ${values.amount} INR against ${enrollment.enrollment_number}? The API will validate the authoritative balance before confirming the payment.`
    : isFeeTerm
      ? `Set a new agreed fee term of ${values.amount} INR for ${enrollment.enrollment_number}? This appends history and does not overwrite earlier terms.`
      : isFeeAdjustment
        ? `Approve this ${values.adjustment_type.replaceAll('_', ' ')} of ${values.amount} INR? The adjustment is append-only and audited.`
        : `Record a ${values.adjustment_type} of ${values.amount} INR for receipt ${payment.payment_id}? This action is recorded in payment history.`

  return (
    <Modal title={title} onClose={writing ? () => {} : onCancel}>
      <form onSubmit={submit} noValidate className="grid gap-4">
        <p className="text-sm text-muted">Enrollment {enrollment.enrollment_number}{payment ? ` · receipt ${payment.payment_id}` : ''}</p>
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
        <TextField id="finance-amount" label={isFeeTerm ? 'Agreed amount (INR)' : 'Amount (INR)'} inputMode="decimal" placeholder="2500.00" required value={values.amount} onChange={(event) => setValues((current) => ({ ...current, amount: event.target.value }))} />
        {isPayment && <>
          <div className="grid gap-1.5"><label htmlFor="payment-method" className="text-sm font-semibold text-ink">Payment method</label><select id="payment-method" name="payment_method" value={values.payment_method} onChange={change} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm">{paymentMethods.map((method) => <option key={method} value={method}>{method.replaceAll('_', ' ')}</option>)}</select></div>
          <TextField id="payment-reference" name="payment_reference" label="Payment reference" maxLength={256} value={values.payment_reference} onChange={change} />
          <TextField id="payment-date" name="paid_at" label="Paid at (optional)" type="datetime-local" value={values.paid_at} onChange={change} />
        </>}
        {(isFeeAdjustment || isPaymentAdjustment) && <div className="grid gap-1.5"><label htmlFor="adjustment-type" className="text-sm font-semibold text-ink">Adjustment type</label><select id="adjustment-type" name="adjustment_type" value={values.adjustment_type} onChange={change} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm">{(isFeeAdjustment ? ['discount', 'fee_increase'] : ['refund', 'reversal']).map((type) => <option key={type} value={type}>{type.replaceAll('_', ' ')}</option>)}</select></div>}
        {isPaymentAdjustment && <p className="text-xs leading-5 text-muted">Receipt remaining amount from API: {formatInrMinorUnits(decimalToMinorUnits(payment.net_amount))}. A reversal must equal this amount.</p>}
        {!isPayment && <div className="grid gap-1.5"><label htmlFor="finance-reason" className="text-sm font-semibold text-ink">Reason</label><textarea id="finance-reason" name="reason" required maxLength={500} rows={3} value={values.reason} onChange={change} className="rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100" /></div>}
        <div className="flex justify-end gap-2 border-t border-line pt-4"><Button type="button" variant="secondary" onClick={onCancel} disabled={writing}>Cancel</Button><Button type="submit" disabled={writing}>Review action</Button></div>
      </form>
      {confirmation && <ConfirmDialog title={`Confirm ${title.toLowerCase()}?`} message={confirmationMessage} confirmLabel={title} busy={writing} onCancel={() => setConfirmation(null)} onConfirm={confirmWrite} />}
    </Modal>
  )
}

function FinanceDetails({ enrollment, token, onClose, onMutation }) {
  const [details, setDetails] = useState(null)
  const [error, setError] = useState('')
  const [action, setAction] = useState(null)
  const [selectedPayment, setSelectedPayment] = useState(null)
  const [success, setSuccess] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  useEffect(() => {
    let active = true
    setDetails(null)
    setError('')
    loadFinanceDetails(enrollment.enrollment_id, token)
      .then((result) => { if (active) setDetails(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Financial history could not be loaded.') })
    return () => { active = false }
  }, [enrollment.enrollment_id, token, reloadKey])

  function saved(_result, actionType) {
    setAction(null)
    setSelectedPayment(null)
    setSuccess(`${actionType === 'payment' ? 'Payment recorded' : actionType === 'feeTerm' ? 'Fee term added' : actionType === 'feeAdjustment' ? 'Fee adjustment recorded' : 'Payment adjustment recorded'} successfully by the API.`)
    setReloadKey((key) => key + 1)
    onMutation()
  }

  const feeColumns = [
    { key: 'effective_from', label: 'Effective from', render: (row) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(row.effective_from)) },
    { key: 'agreed_amount', label: 'Agreed amount', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.agreed_amount)) },
    { key: 'reason', label: 'Reason' },
  ]
  const adjustmentColumns = [
    { key: 'adjustment_type', label: 'Type', render: (row) => row.adjustment_type.replaceAll('_', ' ') },
    { key: 'amount', label: 'Amount', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.amount)) },
    { key: 'reason', label: 'Reason' },
    { key: 'approved_at', label: 'Approved', render: (row) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(row.approved_at)) },
  ]
  const paymentColumns = [
    { key: 'paid_at', label: 'Paid at', render: (row) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(row.paid_at)) },
    { key: 'amount', label: 'Amount', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.amount)) },
    { key: 'net_amount', label: 'Net amount', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.net_amount)) },
    { key: 'payment_method', label: 'Method', render: (row) => row.payment_method.replaceAll('_', ' ') },
    { key: 'derived_status', label: 'Status', render: (row) => <StatusBadge status={row.derived_status} /> },
    { key: 'actions', label: 'Actions', render: (row) => row.net_amount !== '0.00' && row.derived_status !== 'reversed' && row.derived_status !== 'refunded' ? <Button variant="quiet" className="min-h-8 px-2 text-xs" onClick={() => { setSelectedPayment(row); setAction('paymentAdjustment') }}>Refund / reverse</Button> : '—' },
  ]

  return (
    <Modal title={`${enrollment.enrollment_number} · Financial history`} onClose={onClose}>
      {success && <p role="status" className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">{success}</p>}
      {error ? <ErrorState title="Financial history unavailable" message={error} onRetry={() => setReloadKey((key) => key + 1)} /> : !details ? <LoadingState label="Loading authoritative fee and payment history" /> : (
        <div className="max-h-[70vh] overflow-y-auto pr-1">
          <section aria-label="Authoritative fee summary" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ['Base fee', details.fees.base_fee], ['Adjustments', details.fees.adjustments_total], ['Effective fee', details.fees.effective_fee],
              ['Net paid', details.fees.net_paid], ['Pending balance', details.fees.pending_balance],
            ].map(([label, amount]) => <div key={label} className="rounded-md bg-canvas p-3"><p className="text-xs text-muted">{label}</p><p className="mt-1 tabular-nums font-semibold text-ink">{formatInrMinorUnits(decimalToMinorUnits(amount))}</p></div>)}
          </section>
          <p className="mt-2 text-xs text-muted">The API is authoritative for each fee summary and pending balance. No balance is calculated here.</p>
          <div className="my-4 flex flex-wrap gap-2">
            <Button onClick={() => setAction('payment')}><Plus aria-hidden="true" className="h-4 w-4" /> Record payment</Button>
            <Button variant="secondary" onClick={() => setAction('feeTerm')}>Revise fee term</Button>
            <Button variant="secondary" onClick={() => setAction('feeAdjustment')}>Fee discount / increase</Button>
          </div>
          <div className="grid gap-5">
            <section><h3 className="mb-2 text-sm font-semibold text-ink">Agreed fee terms</h3><DataTable columns={feeColumns} rows={details.feeTerms} getRowKey={(row) => row.fee_term_id} caption="Agreed fee term history" emptyMessage="No fee terms." /></section>
            <section><h3 className="mb-2 text-sm font-semibold text-ink">Approved fee adjustments</h3><DataTable columns={adjustmentColumns} rows={details.feeAdjustments} getRowKey={(row) => row.fee_adjustment_id} caption="Fee adjustment history" emptyMessage="No fee adjustments." /></section>
            <section><h3 className="mb-2 text-sm font-semibold text-ink">Payments and refunds</h3><DataTable columns={paymentColumns} rows={details.payments} getRowKey={(row) => row.payment_id} caption="Payments for enrollment" emptyMessage="No payments recorded." />
              {details.payments.some((payment) => payment.adjustments.length) && <ul className="mt-2 divide-y divide-line rounded-md border border-line px-3 text-sm">{details.payments.flatMap((payment) => payment.adjustments.map((event) => <li key={event.adjustment_id} className="flex flex-wrap justify-between gap-2 py-2"><span>{event.adjustment_type} · {event.reason}</span><span className="tabular-nums">{formatInrMinorUnits(decimalToMinorUnits(event.amount))}</span></li>))}</ul>}
            </section>
          </div>
        </div>
      )}
      <div className="mt-4 flex justify-end border-t border-line pt-3"><Button variant="secondary" onClick={onClose}>Close</Button></div>
      {action && <FinanceAction action={action} enrollment={enrollment} payment={selectedPayment} pendingBalance={details?.fees.pending_balance} token={token} onCancel={() => { setAction(null); setSelectedPayment(null) }} onRefresh={() => setReloadKey((key) => key + 1)} onSaved={saved} />}
    </Modal>
  )
}

export default function FinancePage() {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [queryDraft, setQueryDraft] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    loadFinanceEnrollments({ token, page, pageSize: PAGE_SIZE, query, status })
      .then((result) => { if (active) setData(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Fee records could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, page, query, status, reloadKey])

  const columns = [
    { key: 'enrollment_number', label: 'Enrollment' },
    { key: 'student', label: 'Student', render: (row) => `${row.student.full_name} · ${row.student.student_number}` },
    { key: 'program', label: 'Program', render: (row) => row.program?.name || '—' },
    { key: 'effective_fee', label: 'Effective fee', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.fees.effective_fee)) },
    { key: 'net_paid', label: 'Net paid', render: (row) => formatInrMinorUnits(decimalToMinorUnits(row.fees.net_paid)) },
    { key: 'pending_balance', label: 'Pending', render: (row) => <span className="font-semibold tabular-nums">{formatInrMinorUnits(decimalToMinorUnits(row.fees.pending_balance))}</span> },
    { key: 'status', label: 'Enrollment', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'actions', label: 'History', render: (row) => <Button variant="secondary" className="min-h-9 px-3" onClick={() => setSelected(row)}>View history</Button> },
  ]

  return (
    <div className="animate-enter">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Finance</p><h1 className="mt-2 font-display text-4xl text-ink">Fees and payments</h1><p className="mt-2 text-sm text-muted">Enrollment-linked fee terms, payment history, and API-authoritative pending balances.</p></div><Button variant="secondary" onClick={() => setReloadKey((key) => key + 1)} disabled={loading}><RefreshCw aria-hidden="true" className="h-4 w-4" /> Refresh</Button></div>
      <div className="mb-4 flex items-start gap-3 rounded-md border border-orange-200 bg-orange-50 p-3 text-sm text-orange-950"><CircleDollarSign aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" /><p>Financial records are append-only. The server checks payment balance and idempotency; this screen never reports a payment success before the API confirms it.</p></div>
      <form onSubmit={(event) => { event.preventDefault(); setPage(1); setQuery(queryDraft.trim()) }} className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-white p-4">
        <TextField id="finance-search" label="Search enrollments" type="search" maxLength={100} value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} placeholder="Enrollment or student" className="min-w-[min(100%,18rem)] flex-1" />
        <div className="grid min-w-40 gap-1.5"><label htmlFor="finance-status" className="text-xs font-semibold text-muted">Enrollment status</label><select id="finance-status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">{['all', 'active', 'completed', 'withdrawn', 'cancelled'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></div>
        <Button type="submit" variant="secondary">Search</Button>
      </form>
      {loading ? <LoadingState label="Loading authoritative fee records" /> : error ? <ErrorState title="Fee records could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} /> : data.total === 0 ? <EmptyState title="No fee records found" description="No enrollments match these filters." /> : (
        <><div className="mb-3 flex justify-between text-sm text-muted"><span>{data.total.toLocaleString('en-IN')} enrollments</span><span>Page {data.page} of {data.pages}</span></div><DataTable columns={columns} rows={data.items} getRowKey={(row) => row.enrollment_id} caption="Enrollment fee summaries" /><div className="mt-4 flex justify-between"><Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>Previous</Button><Button variant="secondary" disabled={page >= data.pages || loading} onClick={() => setPage((value) => value + 1)}>Next</Button></div></>
      )}
      {selected && <FinanceDetails enrollment={selected} token={token} onClose={() => setSelected(null)} onMutation={() => setReloadKey((key) => key + 1)} />}
    </div>
  )
}
import { FileDown, FileSearch } from 'lucide-react'
import { EmptyState } from '../components/ui.jsx'

export default function ReportsPage() {
  return (
    <div className="animate-enter">
      <div className="mb-7"><p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Reporting</p><h1 className="mt-2 font-display text-4xl text-ink">Reports</h1><p className="mt-2 text-sm text-muted">Operational reporting and data exports.</p></div>
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-lg border border-line bg-white p-5 sm:p-7"><div className="mb-4 grid h-10 w-10 place-items-center rounded-md bg-orange-50 text-orange-700"><FileSearch aria-hidden="true" className="h-5 w-5" /></div><h2 className="text-base font-semibold text-ink">Report API unavailable</h2><p className="mt-2 text-sm leading-6 text-muted">The approved backend contract does not currently provide a general report endpoint. No report is synthesized from a partial page of records.</p><EmptyState title="No report data available" description="The reporting workflow is deferred until a report API is approved." /></section>
        <section className="rounded-lg border border-line bg-white p-5 sm:p-7"><div className="mb-4 grid h-10 w-10 place-items-center rounded-md bg-orange-50 text-orange-700"><FileDown aria-hidden="true" className="h-5 w-5" /></div><h2 className="text-base font-semibold text-ink">CSV export unavailable</h2><p className="mt-2 text-sm leading-6 text-muted">There is no approved export endpoint or export-audit workflow. The portal will not download a misleading current-page-only CSV.</p><p className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">Exports require a backend contract that defines filters, all-matching-pages semantics, permitted fields, size limits, and audit behavior.</p></section>
      </div>
    </div>
  )
}
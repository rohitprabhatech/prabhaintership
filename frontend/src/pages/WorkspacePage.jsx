import { Link, useLocation } from 'react-router-dom'
import { ArrowUpRight, CircleHelp } from 'lucide-react'
import { EmptyState } from '../components/ui.jsx'

const resourceDetails = {
  '/students': ['Students', 'Student profiles and contact details'],
  '/programs': ['Programs', 'Internship program definitions and lifecycle'],
  '/batches': ['Batches', 'Program schedules, capacities, and rosters'],
  '/enrollments': ['Enrollments', 'Student enrollment history and status'],
  '/finance': ['Finance', 'Enrollment fee terms, adjustments, and payments'],
  '/projects': ['Projects', 'Project definitions and enrollment assignments'],
  '/certificates': ['Certificates', 'Issuance, replacement, and event history'],
}

export default function WorkspacePage() {
  const { pathname } = useLocation()
  const [title, subtitle] = resourceDetails[pathname] || ['Overview', 'Internship administration']
  const isOverview = pathname === '/'

  return (
    <div className="animate-enter">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Workspace</p>
          <h1 className="mt-2 font-display text-4xl text-ink">{title}</h1>
          <p className="mt-2 text-sm text-muted">{subtitle}</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-muted">
          <span className="h-2 w-2 rounded-full bg-amber-500" aria-hidden="true" /> API workflows not connected
        </span>
      </div>

      {isOverview ? (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(18rem,0.65fr)]">
          <section className="rounded-lg border border-line bg-white p-5 sm:p-7">
            <div className="mb-7 flex items-start justify-between gap-4">
              <div><p className="text-sm font-semibold text-ink">Workspace overview</p><p className="mt-1 text-sm text-muted">Your administrator session is active.</p></div>
              <div className="grid h-10 w-10 place-items-center rounded-md bg-orange-50 text-orange-700"><CircleHelp aria-hidden="true" className="h-5 w-5" /></div>
            </div>
            <EmptyState
              title="Operational data will appear here"
              description="The approved API does not currently provide a dashboard KPI or report endpoint. No figures are fabricated in this view."
            />
          </section>
          <section className="rounded-lg border border-line bg-white p-5 sm:p-7">
            <h2 className="text-sm font-semibold text-ink">Administration areas</h2>
            <p className="mt-1 text-sm text-muted">Available areas are listed in the navigation.</p>
            <div className="mt-5 grid gap-2">
              {Object.entries(resourceDetails).slice(0, 4).map(([path, [label]]) => (
                <Link key={path} to={path} className="flex min-h-11 items-center justify-between border-b border-line py-2 text-sm font-medium text-ink hover:text-orange-700">
                  {label}<ArrowUpRight aria-hidden="true" className="h-4 w-4 text-muted" />
                </Link>
              ))}
            </div>
          </section>
        </div>
      ) : (
        <EmptyState
          title={`${title} workflows are not connected yet`}
          description="This foundation does not load or change records until the approved API workflow for this area is integrated."
        />
      )}
      <p className="mt-5 text-xs text-muted">Preview state: no mock business records are used.</p>
    </div>
  )
}
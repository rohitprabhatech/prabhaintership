import { apiRequest } from './api.js'

const PAGE_SIZE = 100

function queryPath(path, params) {
  const query = new URLSearchParams(params)
  return `${path}?${query.toString()}`
}

export function decimalToMinorUnits(value) {
  const match = String(value).match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/)
  if (!match) throw new TypeError(`Invalid API money value: ${value}`)
  const fraction = (match[3] || '').padEnd(2, '0')
  const cents = BigInt(match[2]) * 100n + BigInt(fraction || '0')
  return match[1] ? -cents : cents
}

export function formatInrMinorUnits(value) {
  const minorUnits = typeof value === 'bigint' ? value : BigInt(value)
  const sign = minorUnits < 0n ? '-' : ''
  const absoluteUnits = minorUnits < 0n ? -minorUnits : minorUnits
  const rupees = absoluteUnits / 100n
  const paise = String(absoluteUnits % 100n).padStart(2, '0')
  const formattedRupees = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(rupees)
  return `${sign}${formattedRupees}.${paise}`
}

export async function getAllPages(path, params, token) {
  const firstPage = await apiRequest(queryPath(path, {
    ...params,
    page: 1,
    page_size: PAGE_SIZE,
  }), { token })
  const items = [...firstPage.items]

  for (let page = 2; page <= firstPage.pages; page += 1) {
    const result = await apiRequest(queryPath(path, {
      ...params,
      page,
      page_size: PAGE_SIZE,
    }), { token })
    items.push(...result.items)
  }

  return { ...firstPage, items }
}

async function getTotal(path, params, token) {
  const result = await apiRequest(queryPath(path, {
    ...params,
    page: 1,
    page_size: 1,
  }), { token })
  return result.total
}

export async function mapWithConcurrency(items, limit, callback) {
  const results = new Array(items.length)
  let cursor = 0
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor
      cursor += 1
      results[index] = await callback(items[index])
    }
  })
  await Promise.all(workers)
  return results
}

export async function loadDashboard(token) {
  const [studentCount, programCount, batchCount, completedCount, certificateCount, enrollments] = await Promise.all([
    getTotal('students', { status: 'all' }, token),
    getTotal('programs', { status: 'active' }, token),
    getTotal('batches', { status: 'active' }, token),
    getTotal('enrollments', { status: 'completed' }, token),
    getTotal('certificates', { status: 'issued' }, token),
    getAllPages('enrollments', { status: 'all' }, token),
  ])

  const feeSummaries = await mapWithConcurrency(enrollments.items, 8, (enrollment) => (
    apiRequest(`enrollments/${enrollment.enrollment_id}/fees`, { token })
  ))
  const collected = feeSummaries.reduce((total, summary) => total + decimalToMinorUnits(summary.net_paid), 0n)
  const outstanding = feeSummaries.reduce((total, summary) => total + decimalToMinorUnits(summary.pending_balance), 0n)

  const latestEnrollments = enrollments.items.slice(0, 6)
  const lookups = await Promise.all(latestEnrollments.map(async (enrollment) => {
    const [student, program, batch] = await Promise.all([
      apiRequest(`students/${enrollment.student_id}`, { token }),
      apiRequest(`programs/${enrollment.program_id}`, { token }),
      enrollment.batch_id ? apiRequest(`batches/${enrollment.batch_id}`, { token }) : null,
    ])
    return { ...enrollment, student, program, batch }
  }))

  return {
    counts: {
      students: studentCount,
      programs: programCount,
      batches: batchCount,
      collected,
      outstanding,
      completed: completedCount,
      certificates: certificateCount,
    },
    recentEnrollments: lookups,
  }
}
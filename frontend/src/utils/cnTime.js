const CN_OFFSET_MS = 8 * 60 * 60 * 1000

function hasTimezone(value) {
  return /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
}

export function parseCnDate(value) {
  if (!value) return null

  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }

  if (typeof value === 'number') {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? null : date
  }

  const raw = String(value).trim()
  if (!raw) return null

  const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T')
  const parsed = hasTimezone(normalized) ? new Date(normalized) : new Date(`${normalized}+08:00`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function toCnTimestamp(value) {
  const parsed = parseCnDate(value)
  return parsed ? parsed.getTime() : Number.NaN
}

export function compareCnDateAsc(a, b) {
  return toCnTimestamp(a) - toCnTimestamp(b)
}

export function compareCnDateDesc(a, b) {
  return toCnTimestamp(b) - toCnTimestamp(a)
}

export function formatCnDateTime(value) {
  const parsed = parseCnDate(value)
  if (!parsed) return '-'

  const shifted = new Date(parsed.getTime() + CN_OFFSET_MS)
  return shifted.toISOString().slice(0, 19).replace('T', ' ')
}

export function minutesSinceCn(value) {
  const time = toCnTimestamp(value)
  if (Number.isNaN(time)) return Number.NaN
  return Math.max(0, Math.floor((Date.now() - time) / 60000))
}

export function isCnOvertime(value, minutes) {
  const time = toCnTimestamp(value)
  if (Number.isNaN(time)) return false
  return Date.now() - time >= minutes * 60 * 1000
}

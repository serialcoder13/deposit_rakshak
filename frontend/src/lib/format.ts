/**
 * format.ts: shared display helpers.
 */

/** ₹1,50,000 (en-IN grouping) */
export function money(n: number | null | undefined): string {
  return '₹' + Math.round(n ?? 0).toLocaleString('en-IN')
}

/** "12 Sep 2025" */
export function dateShort(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

/** "12 Sep, 4:05 pm" */
export function dateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

/** "2 months ago", "just now", etc. */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days} d ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months} mo ago`
  return `${Math.floor(months / 12)} y ago`
}

/** First 8 characters of a hash */
export function shortHash(h: string | null | undefined): string {
  return h ? h.slice(0, 8) : ''
}

/** "+91 98765 43210" for a 10 digit Indian mobile number */
export function prettyPhone(phone: string | null | undefined): string {
  if (!phone) return ''
  const digits = phone.replace(/\D/g, '').slice(-10)
  if (digits.length !== 10) return phone
  return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`
}

/** First name, or a friendly fallback */
export function firstName(name: string | null | undefined, fallback = 'there'): string {
  const n = (name ?? '').trim()
  return n ? n.split(/\s+/)[0] : fallback
}

/** Today as YYYY-MM-DD in local time */
export function todayISO(): string {
  const d = new Date()
  const off = d.getTimezoneOffset()
  return new Date(d.getTime() - off * 60_000).toISOString().slice(0, 10)
}

export function titleCase(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

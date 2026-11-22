/**
 * format.ts — shared display helpers used across all pages.
 */

/** ₹1,50,000 format using en-IN locale */
export function money(n: number): string {
  return '₹' + Math.round(n).toLocaleString('en-IN')
}

/** "12 Sep 2024" */
export function dateShort(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

/** "2 months ago", "just now", etc. */
export function timeAgo(iso: string): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months}mo ago`
  return `${Math.floor(months / 12)}y ago`
}

/** First 8 characters of a hash, e.g. "a1b2c3d4" */
export function shortHash(h: string | null | undefined): string {
  if (!h) return ''
  return h.slice(0, 8)
}

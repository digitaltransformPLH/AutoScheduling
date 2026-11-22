// Filters live on the URL (?store=2184&week=2026-11-09): shareable links, Back button works.
import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

export type Filters = { store: string | null; week: string | null }

export function useUrlFilters() {
  const [sp, setSp] = useSearchParams()
  const filters: Filters = { store: sp.get('store'), week: sp.get('week') }
  const setFilters = useCallback(
    (next: Partial<Filters>, replace = true) => {
      setSp((prev) => {
        const p = new URLSearchParams(prev)
        for (const [k, v] of Object.entries(next)) {
          if (v) p.set(k, v)
          else p.delete(k)
        }
        if ('store' in next && !('week' in next)) p.delete('week')   // parent filter changed -> reset child
        return p
      }, { replace })
    },
    [setSp],
  )
  return [filters, setFilters] as const
}

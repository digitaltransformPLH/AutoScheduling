import type { DaySummary, HourCoverage } from '../../api/client'
import { ddmm, fmt } from '../../lib/format'
import { coverageColors } from '../../theme/tokens'

export function CoverageHeatmap({ days, hourly, selected, onSelect }: {
  days: DaySummary[]; hourly: HourCoverage[]; selected: string | null; onSelect: (date: string) => void
}) {
  const slots = [...new Set(hourly.map((h) => h.slot))].sort((a, b) => a - b)
  const byKey = new Map(hourly.map((h) => [`${h.workDate}|${h.slot}`, h]))
  return (
    <div className="heat-wrap">
      <table className="heat">
        <thead>
          <tr><th />{slots.map((s) => <th key={s}>{String(s).padStart(2, '0')}h</th>)}</tr>
        </thead>
        <tbody>
          {days.map((d) => (
            <tr key={d.workDate} className={d.workDate === selected ? 'sel' : ''}>
              <th className="day">{d.weekday} <span style={{ color: 'var(--muted)', fontWeight: 500 }}>{ddmm(d.workDate)}</span></th>
              {slots.map((s) => {
                const h = byKey.get(`${d.workDate}|${s}`)
                if (!h) return <td key={s} />
                const c = coverageColors[h.status] ?? { bg: '#fff', fg: 'inherit' }
                return (
                  <td key={s} style={{ background: c.bg, color: c.fg }} onClick={() => onSelect(d.workDate)}
                    title={`${d.weekday} ${h.timeSlot} · TC ${fmt(h.forecastTc, 1)} · cần ${h.neededStaff}, xếp ${h.scheduledStaff}, quản lý ${h.managersOnDuty} · ${h.status}`}>
                    {h.scheduledStaff}/{h.neededStaff}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

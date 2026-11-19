import type { Overview } from '../../api/client'
import { fmt } from '../../lib/format'

export function KpiTiles({ ov }: { ov: Overview }) {
  const w = ov.week
  const days = ov.days.filter((d) => d.dayStatus === 'Mở cửa')
  const n = Math.max(days.length, 1)
  const sum = (f: (d: (typeof days)[number]) => number | null | undefined) => days.reduce((a, d) => a + (f(d) ?? 0), 0)
  const missing = sum((d) => d.missingStaffHours)
  const noMgr = sum((d) => d.hoursWithoutManager)
  const tMin = sum((d) => d.targetHoursMin)
  const tMax = sum((d) => d.targetHoursMax)
  const daysIn = days.filter((d) => d.tcphInTarget).length
  const ceil = (w.tcphTarget ?? 0) * 1.05
  const tiles: [string, string, string, string][] = [
    ['key', 'TC dự báo tuần', fmt(w.forecastTc), `Bình quân ${fmt((w.forecastTc ?? 0) / n)} bill/ngày · tc_p50`],
    ['', 'Nhân sự mở / đóng ca', `${fmt(sum((d) => d.openers) / n, 1)} / ${fmt(sum((d) => d.closers) / n, 1)}`, 'Bình quân mỗi ngày · yêu cầu ≥ 2 / ≥ 2'],
    [(w.laborHours ?? 0) > tMax ? 'alert' : '', 'Giờ công / vùng target', `${fmt(w.laborHours)}<small>h</small>`,
      `Target ${fmt(tMin)}–${fmt(tMax)}h · NSO thêm ${fmt(w.nsoHours)}h`],
    [w.tcphInTarget ? '' : 'alert', 'TCPH tuần', `${fmt(w.weeklyTcph, 2)} <small>/ ${fmt(w.tcphTarget, 2)}–${fmt(ceil, 2)}</small>`,
      `${daysIn}/${days.length} ngày trong khoảng target`],
    [(w.staffCoveragePct ?? 0) < 95 ? 'alert' : '', 'Đủ người / có quản lý', `${fmt(w.staffCoveragePct)}% <small>/ ${fmt(w.managerCoveragePct)}%</small>`,
      `Thiếu ${fmt(missing)} giờ-người · ${noMgr} giờ không quản lý`],
    [w.errorCount ? 'alert' : '', 'Đánh giá kế hoạch', w.assessment ?? '—', `${w.errorCount} lỗi · ${w.warningCount} cảnh báo`],
  ]
  return (
    <section className="kpis">
      {tiles.map(([cls, label, value, desc]) => (
        <article key={label} className={`kpi ${cls}`}>
          <div className="label">{label}</div>
          <div className="value" dangerouslySetInnerHTML={{ __html: value }} />
          <div className="desc">{desc}</div>
        </article>
      ))}
    </section>
  )
}

export function DayTypeSummary({ ov }: { ov: Overview }) {
  const target = ov.week.tcphTarget ?? 0
  const ceil = target * 1.05
  const grp = (f: (i: number) => boolean) => {
    const r = ov.days.filter((_, i) => f(i) && ov.days[i].dayStatus === 'Mở cửa')
    const n = Math.max(r.length, 1)
    const tc = r.reduce((a, d) => a + (d.forecastTc ?? 0), 0)
    const h = r.reduce((a, d) => a + (d.regularHours ?? 0) + (d.trainingHours ?? 0), 0)
    return { tc: tc / n, h: h / n, tcph: h ? tc / h : null, miss: r.reduce((a, d) => a + (d.missingStaffHours ?? 0), 0) / n,
      inT: r.filter((d) => d.tcphInTarget).length, n: r.length }
  }
  const groups: [string, string, ReturnType<typeof grp>][] = [
    ['WD', 'Ngày thường (T2–T6)', grp((i) => i < 5)], ['WK', 'Cuối tuần (T7–CN)', grp((i) => i >= 5)],
  ]
  return (
    <div className="daytype">
      {groups.map(([code, name, g]) => (
        <div key={code} className="dt">
          <span className="code">{code}</span>
          <div className="name">{name}</div>
          <div className="r"><span>TC dự báo</span><b>{fmt(g.tc)}</b></div>
          <div className="r"><span>Giờ công</span><b>{fmt(g.h, 1)}h</b></div>
          <div className="r"><span>TCPH</span>
            <b style={{ color: g.tcph !== null && g.tcph >= target && g.tcph <= ceil ? 'var(--brand)' : 'var(--rust)' }}>{fmt(g.tcph, 2)}</b></div>
          <div className="r"><span>Ngày đạt TCPH</span><b>{g.inT}/{g.n}</b></div>
          <div className="r"><span>Thiếu người</span><b>{fmt(g.miss, 1)} giờ-người</b></div>
        </div>
      ))}
    </div>
  )
}

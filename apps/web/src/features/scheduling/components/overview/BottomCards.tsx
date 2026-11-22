import type { ReactNode } from 'react'
import type { Overview } from '../../api/client'
import { fmt, isManagerPos } from '../../lib/format'
import { Pill } from '../Pill'

// plain-language label + cause for the issue codes users see most (message keeps the engine detail)
const ISSUE_VI: Record<string, [string, string]> = {
  FIXED_EMPLOYEE_MULTIPLE_FORCED_OFF_DAYS: ['FT bận cả ngày nhiều hơn 1 ngày', 'Không đủ 6 ngày làm, mất giờ FT'],
  INVALID_MANAGER_COVERAGE: ['Có giờ không có quản lý trực', 'Thiếu người nhóm quản lý / Barista Trainer'],
  TCPH_OUT_OF_BAND: ['TCPH ngày ngoài khoảng target', 'Giờ FT cố định vượt nhu cầu hoặc thiếu PT'],
  COVERAGE_SACRIFICED_FOR_TCPH_BAND: ['Chấp nhận thiếu người để giữ TCPH', 'Thêm ca PT sẽ làm TCPH dưới target'],
  STAFF_GAP_NO_AVAILABLE_STAFF: ['Thiếu người, không ai rảnh', 'Toàn bộ PT bận trong khung giờ này'],
  STORE_HOURS_NOT_ON_HOUR: ['Giờ mở/đóng không tròn giờ', 'Khung 30 phút đầu/cuối không tính độ phủ'],
  FIXED_LABOR_EXCEEDS_TCPH_BAND: ['Giờ FT vượt target cả tuần', 'PT gần như không có giờ'],
  INSUFFICIENT_MANAGER_CAPACITY: ['Không đủ quản lý cho cả tuần', 'Cần thêm người nhóm quản lý'],
  TCPH_TARGET_INFEASIBLE: ['Target TCPH không đạt được', 'TC quá thấp so với sàn 2 người/giờ'],
}

export function IssuesCard({ ov }: { ov: Overview }) {
  const real = ov.issues.filter((i) => i.severity !== 'Gợi ý')
  const sugg = ov.issues.filter((i) => i.severity === 'Gợi ý')
  const groups = new Map<string, { sev: string; n: number; ex: string }>()
  for (const i of real) {
    const key = i.issueCode ?? i.message
    const g = groups.get(key) ?? { sev: i.severity, n: 0, ex: i.message }
    g.n += 1
    groups.set(key, g)
  }
  const items = [...groups.entries()].sort((a, b) => Number(a[1].sev !== 'Lỗi') - Number(b[1].sev !== 'Lỗi') || b[1].n - a[1].n)
  return (
    <div className="card">
      <div className="card-head">
        <div><div className="card-title">Cần xử lý trước khi duyệt</div><div className="card-sub">Gom theo loại vấn đề · rê chuột để xem chi tiết</div></div>
        <Pill>{ov.week.errorCount} lỗi · {ov.week.warningCount} cảnh báo</Pill>
      </div>
      {items.length === 0 && <div className="card-sub">Không có lỗi hoặc cảnh báo.</div>}
      {items.slice(0, 6).map(([code, v]) => {
        const [what, why] = ISSUE_VI[code] ?? [code, v.ex]
        return (
          <div key={code} className="issue" title={v.ex}>
            <Pill tone={v.sev === 'Lỗi' ? 'bad' : 'warn'}>{v.sev}</Pill>
            <div><div className="what">{what}</div><div className="why">{why}</div></div>
            <span className="n">×{v.n}</span>
          </div>
        )
      })}
      <div className="sugg">
        <h4>Gợi ý</h4>
        <ul>{(sugg.length ? sugg.slice(0, 3).map((s) => s.message) : ['Không có gợi ý']).map((s) => <li key={s}>{s}</li>)}</ul>
      </div>
    </div>
  )
}

export function TargetTable({ ov }: { ov: Overview }) {
  const w = ov.week
  const days = ov.days.filter((d) => d.dayStatus === 'Mở cửa')
  const ceil = (w.tcphTarget ?? 0) * 1.05
  const daysIn = days.filter((d) => d.tcphInTarget).length
  const openOk = days.filter((d) => (d.openers ?? 0) >= 2).length
  const closeOk = days.filter((d) => (d.closers ?? 0) >= 2).length
  const st = (ok: boolean, risk: boolean) => (ok ? <Pill tone="good">Đạt</Pill> : risk ? <Pill tone="warn">Cần chú ý</Pill> : <Pill tone="bad">Chưa đạt</Pill>)
  const rowsData: [string, string, string, ReactNode][] = [
    ['TCPH tuần', `${fmt(w.tcphTarget, 2)}–${fmt(ceil, 2)}`, fmt(w.weeklyTcph, 2), st(!!w.tcphInTarget, Math.abs((w.weeklyTcph ?? 0) - (w.tcphTarget ?? 0)) < 0.3)],
    ['Ngày TCPH đạt', `${days.length}/${days.length}`, `${daysIn}/${days.length}`, st(daysIn === days.length, daysIn >= days.length - 2)],
    ['Đủ người', '100%', `${fmt(w.staffCoveragePct, 1)}%`, st((w.staffCoveragePct ?? 0) >= 100, (w.staffCoveragePct ?? 0) >= 95)],
    ['Có quản lý trực', '100%', `${fmt(w.managerCoveragePct, 1)}%`, st((w.managerCoveragePct ?? 0) >= 100, (w.managerCoveragePct ?? 0) >= 95)],
    ['Mở cửa ≥ 2 người', `${days.length}/${days.length} ngày`, `${openOk}/${days.length}`, st(openOk === days.length, false)],
    ['Đóng cửa ≥ 2 người', `${days.length}/${days.length} ngày`, `${closeOk}/${days.length}`, st(closeOk === days.length, false)],
  ]
  return (
    <div className="card">
      <div className="card-head"><div><div className="card-title">Kết quả so với mục tiêu</div><div className="card-sub">Ngưỡng theo SPEC §8.1</div></div></div>
      <table className="kt">
        <thead><tr><th>Chỉ số</th><th>Mục tiêu</th><th>Thực tế</th><th /></tr></thead>
        <tbody>{rowsData.map(([a, b, c, d]) => <tr key={a}><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>)}</tbody>
      </table>
    </div>
  )
}

export function RosterSummary({ ov }: { ov: Overview }) {
  const byEmp = new Map<string, { position: string; type: string; group: string; hours: number; borrowed: boolean }>()
  for (const r of ov.roster) {
    const e = byEmp.get(r.employeeId) ?? { position: r.position, type: r.employmentType, group: r.laborGroup, hours: 0, borrowed: !!r.homeStore }
    if (r.dayType === 'Làm') e.hours += r.hours
    byEmp.set(r.employeeId, e)
  }
  const emps = [...byEmp.values()]
  const groups: [string, (e: (typeof emps)[number]) => boolean][] = [
    ['Quản lý', (e) => isManagerPos(e.position)], ['Barista Trainer', (e) => e.position === 'Barista Trainer'],
    ['FT', (e) => e.type === 'FT' && !isManagerPos(e.position) && e.position !== 'Barista Trainer'],
    ['PT', (e) => e.type === 'PT' && e.group === 'Regular'], ['Training / NSO', (e) => e.group !== 'Regular'],
  ]
  const total = emps.reduce((a, e) => a + e.hours, 0)
  return (
    <div className="card">
      <div className="card-head"><div><div className="card-title">Tóm tắt nhân sự</div><div className="card-sub">Giờ làm tại store trong tuần</div></div></div>
      <div className="rs-grid">
        <div className="rs"><b>{emps.length}</b><span>Nhân viên</span></div>
        <div className="rs"><b>{fmt(total)}</b><span>Giờ đã xếp</span></div>
        <div className="rs"><b>{emps.filter((e) => e.hours === 0).length}</b><span>Người 0 giờ</span></div>
      </div>
      <table className="rt">
        <thead><tr><th>Nhóm</th><th className="num">Người</th><th className="num">Giờ</th><th className="num">TB/người</th></tr></thead>
        <tbody>
          {groups.map(([name, f]) => {
            const g = emps.filter(f)
            if (!g.length) return null
            const h = g.reduce((a, e) => a + e.hours, 0)
            return <tr key={name}><td>{name}</td><td className="num">{g.length}</td><td className="num">{fmt(h)}</td><td className="num">{fmt(h / g.length, 1)}</td></tr>
          })}
        </tbody>
      </table>
    </div>
  )
}

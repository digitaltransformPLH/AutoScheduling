// "Ai làm lúc nào": one bar per shift of the selected day, axis from setup (opening - 30') to cleaning (closing + 30'),
// forecast TC per hour on top, headcount vs need at the bottom.
import type { DaySummary, HourCoverage, RosterDay, ScheduleWeek } from '../../api/client'
import { ddmm, fmt, hhmm, isManagerPos, shortName, toMin } from '../../lib/format'
import { Pill } from '../Pill'

const barClass = (r: RosterDay) =>
  isManagerPos(r.position) && r.laborGroup !== 'Training' ? 'mgr'
    : r.position === 'Barista Trainer' ? 'bt' : r.laborGroup !== 'Regular' ? 'special' : r.employmentType === 'FT' ? 'ft' : 'pt'

export function DayTabs({ days, selected, onSelect }: { days: DaySummary[]; selected: string; onSelect: (d: string) => void }) {
  return (
    <div className="day-tabs">
      {days.map((d) => {
        const c = d.hoursWithoutManager ? 'var(--rust)' : d.missingStaffHours ? '#e3a58c' : '#9DB97A'
        return (
          <button key={d.workDate} type="button" className={d.workDate === selected ? 'active' : ''} onClick={() => onSelect(d.workDate)}>
            {d.weekday}<span className="dot" style={{ background: c }} />
          </button>
        )
      })}
    </div>
  )
}

export function Timeline({ week, day, roster, hourly }: { week: ScheduleWeek; day: DaySummary; roster: RosterDay[]; hourly: HourCoverage[] }) {
  const open = toMin(week.openingTime ?? '07:00')
  const close = toMin(week.closingTime ?? '22:00')
  const rows = roster
    .filter((r) => r.workDate === day.workDate && r.dayType === 'Làm' && r.startTime && r.endTime)
    .map((r) => {
      const s = toMin(r.startTime!)
      const e0 = toMin(r.endTime!)
      return { ...r, s, e: e0 <= s ? e0 + 1440 : e0 }
    })
    .sort((a, b) => a.s - b.s || a.e - b.e || a.employeeName.localeCompare(b.employeeName))
  const lo = Math.min(open - 30, ...rows.map((r) => r.s))
  const hi = Math.max(close + 30, ...rows.map((r) => r.e))
  const a0 = Math.floor(lo / 60) * 60
  const a1 = Math.ceil(hi / 60) * 60
  const span = a1 - a0
  const x = (m: number) => `${((m - a0) / span) * 100}%`
  const colW = (60 / span) * 100
  const hours = hourly.filter((h) => h.workDate === day.workDate)
  const maxTc = Math.max(1, ...hours.map((h) => h.forecastTc))
  const others = roster.filter((r) => r.workDate === day.workDate && r.dayType !== 'Làm')
  const groups: [string, RosterDay[], 'neutral' | 'warn' | 'good'][] = [
    ['OFF', others.filter((r) => r.dayType === 'OFF'), 'neutral'],
    ['Nghỉ phép', others.filter((r) => r.dayType === 'Nghỉ phép'), 'warn'],
    ['Đi hỗ trợ', others.filter((r) => r.dayType === 'Đi hỗ trợ'), 'good'],
    ['Không xếp ca', others.filter((r) => r.dayType === 'Không xếp ca'), 'neutral'],
  ]
  const cols = []
  for (let m = a0; m < a1; m += 60) cols.push(m)

  return (
    <>
      <div className="tl-wrap">
        <div className="tl">
          <div className="tl-axis">
            {[...cols, a1].map((m) => <span key={m} style={{ left: x(m) }}>{hhmm(m)}</span>)}
          </div>
          <div className="tl-body">
            <div className="tl-grid">
              {cols.map((m) => <div key={m} className={`col ${(m / 60) % 2 ? 'alt' : ''}`} style={{ left: x(m), width: `${colW}%` }} />)}
              <div className="closed" style={{ left: 0, width: x(open) }} />
              <div className="closed" style={{ left: x(close), right: 0 }} />
              <div className="mark" style={{ left: x(open) }}><b>Mở cửa {week.openingTime}</b></div>
              <div className="mark" style={{ left: x(close) }}><b>Đóng cửa {week.closingTime}</b></div>
            </div>
            <div className="tl-row fc">
              <div className="who"><b>TC dự báo</b><span>bill / giờ · tổng {fmt(day.forecastTc)}</span></div>
              <div className="lane">
                {hours.map((h) => {
                  const ht = Math.max(2, Math.round((h.forecastTc / maxTc) * 36))
                  return (
                    <span key={h.slot}>
                      <div className={`fcbar ${h.isPeakHour ? 'peak' : ''}`} title={`${h.timeSlot} · TC ${fmt(h.forecastTc, 1)} · cần ${h.neededStaff} người`}
                        style={{ left: `calc(${x(h.slot * 60)} + ${colW * 0.15}%)`, width: `${colW * 0.7}%`, height: ht }} />
                      <span className="fcval" style={{ left: x(h.slot * 60 + 30), bottom: ht + 6 }}>{fmt(h.forecastTc)}</span>
                    </span>
                  )
                })}
              </div>
            </div>
            {rows.length === 0 && <div className="tl-row"><div className="who" /><div className="lane" style={{ padding: 10, color: 'var(--muted)' }}>Không có ca làm</div></div>}
            {rows.map((r) => (
              <div key={r.employeeId} className="tl-row">
                <div className="who">
                  <b title={r.employeeName}>{r.employeeName}</b>
                  <span>{r.position} · {r.employmentType}{r.laborGroup !== 'Regular' ? ` · ${r.laborGroup}` : ''}{r.homeStore ? ` · mượn ${r.homeStore}` : ''}</span>
                </div>
                <div className="lane">
                  <div className={`bar ${barClass(r)} ${r.homeStore ? 'borrowed' : ''}`} style={{ left: x(r.s), width: `${((r.e - r.s) / span) * 100}%` }}
                    title={`${r.employeeName} · ${r.startTime}–${r.endTime} · mã ca ${r.shiftCode ?? '—'}${r.note ? ` · ${r.note}` : ''}`}>
                    <b>{shortName(r.employeeName)}</b>
                    <span className="t">{r.startTime}–{r.endTime} · {fmt((r.e - r.s) / 60)}h</span>
                    {r.shiftRole && <span className="tag">{r.shiftRole}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="tl-count">
            {hours.map((h) => (
              <span key={h.slot} style={{ left: x(h.slot * 60 + 30), color: h.status === 'Đủ người' ? 'var(--brand)' : h.status === 'Dư người' ? '#1f4b63' : 'var(--rust)' }}
                title={`${h.timeSlot} · xếp ${h.scheduledStaff} / cần ${h.neededStaff}`}>
                {h.scheduledStaff}/{h.neededStaff}
              </span>
            ))}
          </div>
        </div>
      </div>
      <div className="tl-off">
        {groups.filter(([, l]) => l.length).map(([label, list, tone]) => (
          <span key={label} style={{ display: 'contents' }}>
            <span className="lbl">{label}</span>
            {list.map((r) => <Pill key={r.employeeId} tone={tone}>{shortName(r.employeeName)}{r.note && label === 'Đi hỗ trợ' ? ` → ${r.note.replace('Hỗ trợ store ', '')}` : ''}</Pill>)}
          </span>
        ))}
      </div>
    </>
  )
}

export function timelineSubtitle(day: DaySummary, roster: RosterDay[]) {
  const n = roster.filter((r) => r.workDate === day.workDate && r.dayType === 'Làm').length
  const parts = [`${day.weekday} ${ddmm(day.workDate)}`, `${n} người đi làm`,
    `${fmt((day.regularHours ?? 0) + (day.trainingHours ?? 0) + (day.nsoHours ?? 0))} giờ công`, `TCPH ${fmt(day.tcph, 2)}`]
  if (day.hoursWithoutManager) parts.push(`${day.hoursWithoutManager} giờ không có quản lý`)
  if (day.missingStaffHours) parts.push(`thiếu ${day.missingStaffHours} giờ-người`)
  return parts.join(' · ')
}

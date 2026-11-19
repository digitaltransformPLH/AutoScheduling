// Weekly roster grid: one row per employee, one column per day (same order as the attendance upload file).
import { Empty, Segmented, Skeleton, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useMemo, useState } from 'react'
import type { RosterDay } from '../api/client'
import { useOverview } from '../api/hooks'
import { StoreWeekPicker } from '../components/StoreWeekPicker'
import { addDays, ddmm, fmt, isManagerPos, isoWeek } from '../lib/format'
import { useUrlFilters } from '../lib/useUrlFilters'

type Row = { key: string; name: string; position: string; type: string; group: string; home: string | null; days: Record<string, RosterDay>; hours: number; workDays: number }

function Cell({ d }: { d?: RosterDay }) {
  if (!d) return null
  switch (d.dayType) {
    case 'Làm':
      return <span className={`cell-shift ${isManagerPos(d.position) ? 'cell-mgr' : ''}`}>{d.startTime}–{d.endTime}<small>{d.shiftCode}{d.shiftRole ? ` · ${d.shiftRole}` : ''}</small></span>
    case 'Nghỉ phép':
      return <span className="cell-al">AL</span>
    case 'Đi hỗ trợ':
      return <span className="cell-away" title={d.note ?? ''}>{d.note?.replace('Hỗ trợ store ', 'HT ') ?? 'Hỗ trợ'}<small>{d.startTime}–{d.endTime} · {d.shiftCode}</small></span>
    case 'Ở store gốc':
      return <span className="cell-off">·</span>
    case 'OFF':
      return <span className="cell-off">OFF</span>
    default:
      return <span className="cell-off">–</span>
  }
}

export function RosterPage() {
  const [{ store, week }] = useUrlFilters()
  const ov = useOverview(store, week)
  const [group, setGroup] = useState<string>('Tất cả')

  const { rows, dates } = useMemo(() => {
    const map = new Map<string, Row>()
    const dates = new Map<string, string>()
    for (const r of [...(ov.data?.roster ?? [])].sort((a, b) => a.sortOrder - b.sortOrder)) {
      dates.set(r.workDate, r.weekday)
      const row = map.get(r.employeeId) ?? { key: r.employeeId, name: r.employeeName, position: r.position, type: r.employmentType,
        group: r.laborGroup, home: r.homeStore ?? null, days: {}, hours: 0, workDays: 0 }
      row.days[r.workDate] = r
      if (r.dayType === 'Làm' || r.dayType === 'Đi hỗ trợ') { row.hours += r.hours; row.workDays += 1 }  // hỗ trợ store khác vẫn tính giờ công
      map.set(r.employeeId, row)
    }
    return { rows: [...map.values()], dates: [...dates.entries()].sort() }
  }, [ov.data])

  const filtered = rows.filter((r) => group === 'Tất cả'
    || (group === 'Quản lý' && isManagerPos(r.position)) || (group === 'FT' && r.type === 'FT' && !isManagerPos(r.position))
    || (group === 'PT' && r.type === 'PT'))

  const columns: ColumnsType<Row> = [
    { title: 'Nhân viên', dataIndex: 'name', fixed: 'left', width: 220,
      render: (_, r) => <div><b>{r.name}</b><div style={{ fontSize: 11, color: 'var(--muted)' }}>{r.key} · {r.position} · {r.type}{r.group !== 'Regular' ? ` · ${r.group}` : ''}{r.home ? ` · mượn từ ${r.home}` : ''}</div></div> },
    ...dates.map(([d, wd]) => ({ title: <div style={{ textAlign: 'center' }}>{wd}<div style={{ fontWeight: 500, fontSize: 11 }}>{ddmm(d)}</div></div>,
      key: d, width: 128, align: 'center' as const, render: (_: unknown, r: Row) => <Cell d={r.days[d]} /> })),
    { title: 'Giờ', dataIndex: 'hours', width: 70, align: 'right', fixed: 'right', sorter: (a, b) => a.hours - b.hours, render: (v: number) => <b>{fmt(v)}</b> },
    { title: 'Ngày', dataIndex: 'workDays', width: 64, align: 'right', fixed: 'right', sorter: (a, b) => a.workDays - b.workDays },
  ]

  return (
    <main className="page">
      <div className="head">
        <div>
          <div className="kicker">Roster tuần · {week ? `Tuần ${isoWeek(week)} · ${ddmm(week)} – ${ddmm(addDays(week, 6))}` : '—'}{store ? ` · Store ${store}` : ''}</div>
          <h1 className="action-title">{ov.data ? `${rows.length} nhân viên · ${fmt(rows.reduce((a, r) => a + r.hours, 0))} giờ đã xếp trong tuần` : 'Roster tuần'}</h1>
          <div className="sub">Thứ tự giống file upload chấm công · ca in đậm xanh = quản lý · HT = đi hỗ trợ store khác</div>
        </div>
        <StoreWeekPicker />
      </div>
      <div style={{ marginBottom: 12 }}><Segmented value={group} onChange={(v) => setGroup(String(v))} options={['Tất cả', 'Quản lý', 'FT', 'PT']} /></div>
      {ov.isLoading ? <Skeleton active /> : !ov.data ? <div className="card"><Empty description="Chưa có lịch cho store-tuần này" /></div> : (
        <Table<Row> size="small" bordered rowKey="key" columns={columns} dataSource={filtered} pagination={false} scroll={{ x: 1300 }} />
      )}
    </main>
  )
}

// Busy calendar of one week: click a cell to edit (free / busy hours / busy all day / paid leave), copy a week, or upload Excel.
import { CopyOutlined } from '@ant-design/icons'
import { App, Button, DatePicker, Modal, Radio, Select, Space, Table, TimePicker } from 'antd'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import { useMemo, useState } from 'react'
import type { AvailabilityItem, InputOptions, Me, Saved } from '../../api/client'
import { fileUrl, sendJson } from '../../api/client'
import { useAvailability, useEmployees, useInputMutation } from '../../api/hooks'
import { addDays, ddmm, ddmmyyyy } from '../../lib/format'
import { ExcelImport } from './ExcelImport'

const WD = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
type Kind = 'free' | 'busy' | 'allday' | 'al'
type Cell = { employeeId: string; name: string; date: string; item?: AvailabilityItem }

const isAllDay = (a: AvailabilityItem) => !!a.busyFrom && a.busyFrom <= '07:00' && (a.busyTo ?? '') >= '22:00'
const kindOf = (a?: AvailabilityItem): Kind => (!a ? 'free' : a.isPaidLeave ? 'al' : !a.busyFrom ? 'free' : isAllDay(a) ? 'allday' : 'busy')
const monday = (d: Dayjs) => d.subtract((d.day() + 6) % 7, 'day').format('YYYY-MM-DD')

type Props = { store: string; me: Me; options?: InputOptions; week: string | null; setWeek: (w: string) => void }

export function BusyTab({ store, me, options, week, setWeek }: Props) {
  const { message } = App.useApp()
  const emps = useEmployees(store)
  const av = useAvailability(store, week)
  const [cell, setCell] = useState<Cell | null>(null)
  const [kind, setKind] = useState<Kind>('free')
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [copyFrom, setCopyFrom] = useState<string | null>(null)
  const [copyOpen, setCopyOpen] = useState(false)
  const edit = me.can.availabilityEdit

  const save = useInputMutation((items: object[]) => sendJson<Saved>(`/inputs/availability/${store}/${week}`, { items }, 'PUT'))
  const copy = useInputMutation((src: string) => sendJson<Saved>(`/inputs/availability/${store}/${week}/copy`, { sourceWeek: src }))

  const weeks = useMemo(() => {
    const ws = new Set(options?.availabilityWeeks ?? [])
    if (week) ws.add(week)
    return [...ws].sort().reverse()
  }, [options, week])

  const rows = useMemo(() => {
    const byKey = new Map((av.data ?? []).map((a) => [`${a.employeeId}|${a.workDate}`, a]))
    return (emps.data ?? []).filter((e) => e.status === 'Active').map((e) => ({
      key: e.employeeId, name: e.employeeName, position: e.position,
      days: WD.map((_, i) => byKey.get(`${e.employeeId}|${addDays(week ?? '2000-01-03', i)}`)),
    }))
  }, [emps.data, av.data, week])

  const openCell = (c: Cell) => {
    if (!edit) return
    setCell(c)
    const k = kindOf(c.item)
    setKind(k)
    setRange(k === 'busy' && c.item?.busyFrom && c.item.busyTo
      ? [dayjs(`2000-01-01T${c.item.busyFrom}`), dayjs(`2000-01-01T${c.item.busyTo}`)] : null)
  }
  const submit = () => {
    if (!cell) return
    if (kind === 'busy' && !range) { message.warning('Chọn giờ bận'); return }
    const item = {
      employeeId: cell.employeeId, workDate: cell.date, isPaidLeave: kind === 'al',
      busyFrom: kind === 'busy' ? range![0].format('HH:mm') : kind === 'allday' ? '00:00' : null,
      busyTo: kind === 'busy' ? range![1].format('HH:mm') : kind === 'allday' ? '23:59' : null,
    }
    save.mutate([item], { onSuccess: () => { message.success('Đã lưu'); setCell(null) }, onError: (e) => message.error((e as Error).message) })
  }

  const show = (a?: AvailabilityItem) => {
    const k = kindOf(a)
    if (k === 'al') return <span className="cell-al">AL</span>
    if (k === 'free') return <span style={{ color: 'var(--brand)', fontWeight: 700 }}>Rảnh</span>
    if (k === 'allday') return <span style={{ color: 'var(--rust)', fontWeight: 700 }}>Bận cả ngày</span>
    return <span style={{ fontWeight: 700 }}>Bận {a!.busyFrom}–{a!.busyTo}</span>
  }

  return (
    <>
      <div className="toolbar">
        <span>Tuần lịch bận</span>
        <Select style={{ width: 200 }} value={week ?? undefined} onChange={setWeek}
          options={weeks.map((w) => ({ value: w, label: `${ddmm(w)} – ${ddmmyyyy(addDays(w, 6))}` }))} />
        <DatePicker picker="week" placeholder="Tuần khác…" format={(d) => `Tuần ${monday(d).slice(8, 10)}/${monday(d).slice(5, 7)}`}
          onChange={(d) => d && setWeek(monday(d))} />
        <span className="grow" />
        {edit && <Button icon={<CopyOutlined />} disabled={!week} onClick={() => { setCopyFrom(weeks.find((w) => w !== week) ?? null); setCopyOpen(true) }}>
          Chép từ tuần khác</Button>}
        <ExcelImport title={`Upload lịch bận · store ${store} · tuần ${week ? ddmmyyyy(week) : ''}`} path="/inputs/excel/availability-file"
          fields={{ store, week: week ?? '', replace_employees: false, replace_busy: true }}
          downloadHref={week ? fileUrl('/inputs/excel/availability-file', { store, week }) : null} canUpload={edit}
          disabledReason={week ? null : 'Chọn tuần'}
          description={<>Dùng file Availability của store (sheet <b>Availability</b>: 7 dòng / nhân viên, "Bận từ / Bận đến" là giờ bận, để trống = rảnh,
            AL = nghỉ phép). Chỉ thay lịch bận của tuần {week ? ddmmyyyy(week) : ''}; danh sách nhân viên giữ nguyên.</>} />
      </div>
      <div className="card-sub" style={{ marginBottom: 8 }}>
        "Bận từ / Bận đến" là giờ bận; bận cả ngày = không xếp ca. {edit ? 'Bấm vào ô để sửa.' : ''}
        {week && av.data && av.data.length === 0 ? ' Tuần này chưa có dữ liệu — mọi người đang được coi là rảnh cả tuần.' : ''}
      </div>
      <Table size="small" bordered rowKey="key" loading={emps.isLoading || av.isFetching} pagination={false} dataSource={rows} scroll={{ x: 1100 }}
        columns={[
          { title: 'Nhân viên', dataIndex: 'name', fixed: 'left', width: 230,
            render: (v: string, r) => <><b>{v}</b><div className="card-sub">{r.position}</div></> },
          ...WD.map((w, i) => ({
            title: week ? `${w} ${ddmm(addDays(week, i))}` : w, key: w, align: 'center' as const,
            render: (_: unknown, r: (typeof rows)[number]) => (
              <span className={edit ? 'busy-cell' : undefined} role={edit ? 'button' : undefined}
                onClick={() => openCell({ employeeId: r.key, name: r.name, date: addDays(week!, i), item: r.days[i] })}>{show(r.days[i])}</span>),
          })),
        ]} />
      <Modal open={!!cell} title={cell ? `${cell.name} · ${WD[(new Date(`${cell.date}T00:00:00Z`).getUTCDay() + 6) % 7]} ${ddmmyyyy(cell.date)}` : ''}
        onCancel={() => setCell(null)} onOk={submit} okText="Lưu" confirmLoading={save.isPending} destroyOnHidden>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Radio.Group value={kind} onChange={(e) => setKind(e.target.value)} optionType="button" buttonStyle="solid" options={[
            { value: 'free', label: 'Rảnh' }, { value: 'busy', label: 'Bận theo giờ' }, { value: 'allday', label: 'Bận cả ngày' },
            { value: 'al', label: 'Nghỉ phép (AL)' }]} />
          {kind === 'busy' && <TimePicker.RangePicker format="HH:mm" minuteStep={30} value={range}
            onChange={(v) => setRange(v && v[0] && v[1] ? [v[0], v[1]] : null)} placeholder={['Bận từ', 'Bận đến']} />}
          <div className="card-sub">
            {kind === 'busy' && 'Engine không xếp ca chồng lên khung giờ bận.'}
            {kind === 'allday' && 'Ngày này không xếp ca.'}
            {kind === 'al' && 'Nghỉ phép: tính 8h (FT / quản lý), không xếp ca, không trùng ngày OFF.'}
          </div>
        </Space>
      </Modal>
      <Modal open={copyOpen} title={`Chép lịch bận sang tuần ${week ? ddmmyyyy(week) : ''}`} okText="Chép (thay tuần này)" okButtonProps={{ danger: true }}
        confirmLoading={copy.isPending} onCancel={() => setCopyOpen(false)}
        onOk={() => copyFrom && copy.mutate(copyFrom, { onSuccess: (r) => { message.success(r.message); setCopyOpen(false) },
          onError: (e) => message.error((e as Error).message) })}>
        <p>Lịch bận tuần {week ? ddmmyyyy(week) : ''} sẽ bị thay bằng lịch của tuần được chọn (theo thứ trong tuần, chỉ nhân viên đang làm).</p>
        <Select style={{ width: 240 }} value={copyFrom ?? undefined} onChange={setCopyFrom}
          options={weeks.filter((w) => w !== week).map((w) => ({ value: w, label: `Tuần ${ddmm(w)} – ${ddmmyyyy(addDays(w, 6))}` }))} />
      </Modal>
    </>
  )
}

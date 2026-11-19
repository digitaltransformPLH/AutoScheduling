import { Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { Link } from 'react-router-dom'
import type { Run } from '../api/client'
import { useRuns } from '../api/hooks'
import { Pill } from '../components/Pill'
import { StoreWeekPicker } from '../components/StoreWeekPicker'
import { ddmmyyyy } from '../lib/format'
import { useUrlFilters } from '../lib/useUrlFilters'
import { assessmentTone } from '../theme/tokens'

const STATUS: Record<string, [string, 'good' | 'warn' | 'bad' | 'neutral']> = {
  queued: ['Đang chờ', 'neutral'], running: ['Đang chạy', 'warn'], done: ['Xong', 'good'], failed: ['Lỗi', 'bad'],
}

export function RunsPage() {
  const [{ store }] = useUrlFilters()
  const runs = useRuns(null, true)
  const cols: ColumnsType<Run> = [
    { title: '#', dataIndex: 'runId', width: 60 },
    { title: 'Store', dataIndex: 'storeCode', width: 80, filters: [...new Set((runs.data ?? []).map((r) => r.storeCode))].map((s) => ({ text: s, value: s })),
      onFilter: (v, r) => r.storeCode === v, defaultFilteredValue: store ? [store] : undefined },
    { title: 'Tuần', dataIndex: 'weekStart', width: 110, render: (v: string, r) => <Link to={`/?store=${r.storeCode}&week=${v}`}>{ddmmyyyy(v)}</Link> },
    { title: 'Lịch bận tuần', dataIndex: 'availabilityWeek', width: 120, render: (v: string | null) => (v ? ddmmyyyy(v) : '—') },
    { title: 'Trạng thái', dataIndex: 'status', width: 110, render: (v: string) => <Pill tone={STATUS[v]?.[1]}>{STATUS[v]?.[0] ?? v}</Pill> },
    { title: 'Đánh giá', dataIndex: 'assessment', width: 110, render: (v: string | null) => (v ? <Pill tone={assessmentTone[v]}>{v}</Pill> : '—') },
    { title: 'Kết quả', dataIndex: 'message', ellipsis: true },
    { title: 'Người chạy', dataIndex: 'requestedBy', width: 110 },
    { title: 'Bắt đầu', dataIndex: 'startedAt', width: 140 }, { title: 'Xong', dataIndex: 'finishedAt', width: 140 },
  ]
  return (
    <main className="page">
      <div className="head">
        <div>
          <div className="kicker">Lịch sử chạy engine</div>
          <h1 className="action-title">Mỗi lần "Tạo lịch" là một lần chạy; lịch mới thay lịch cũ của store-tuần đó.</h1>
          <div className="sub">Tự làm mới mỗi 2 giây khi có lần chạy đang chờ / đang chạy.</div>
        </div>
        <StoreWeekPicker />
      </div>
      <div className="card"><Table<Run> size="small" rowKey="runId" loading={runs.isLoading} columns={cols} dataSource={runs.data} pagination={{ pageSize: 20 }} /></div>
    </main>
  )
}

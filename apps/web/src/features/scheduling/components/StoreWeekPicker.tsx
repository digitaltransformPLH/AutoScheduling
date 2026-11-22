// Store + week selectors shared by the pages (state on the URL), plus "Tạo lịch" (engine run) and File 2 export.
import { DownloadOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { Button, Select, Space, Tooltip, message } from 'antd'
import { useEffect, useMemo, useRef } from 'react'
import { fileUrl } from '../api/client'
import { useAuth } from '../../auth/AuthContext'
import { PermissionCodes } from '../../../shared/api/types'
import { useForecastWeeks, useRuns, useSchedules, useStartRun, useStores } from '../api/hooks'
import { addDays, ddmm, isoWeek } from '../lib/format'
import { useUrlFilters } from '../lib/useUrlFilters'

type Props = { showActions?: boolean; showWeek?: boolean; readyOnly?: boolean }

export function StoreWeekPicker({ showActions = true, showWeek = true, readyOnly = true }: Props) {
  const [{ store, week }, setFilters] = useUrlFilters()
  const { hasPermission } = useAuth()
  const canRun = hasPermission(PermissionCodes.PublishSchedule)
  const stores = useStores(readyOnly)
  const schedules = useSchedules(showWeek ? store : null)
  const fweeks = useForecastWeeks()
  const runs = useRuns(store, showActions && canRun)
  const start = useStartRun()

  // default store / week: first ready store the user may see (also when the URL names a store outside their list),
  // its latest scheduled week (else latest forecast week)
  useEffect(() => {
    if (!stores.data?.length) return
    if (!store || !stores.data.some((s) => s.storeCode === store)) setFilters({ store: stores.data[0].storeCode })
  }, [store, stores.data, setFilters])
  useEffect(() => {
    if (showWeek && store && !week && schedules.data && fweeks.data) {
      const w = schedules.data[0]?.weekStart ?? fweeks.data[0]?.weekStart
      if (w) setFilters({ week: w })
    }
  }, [store, week, schedules.data, fweeks.data, setFilters, showWeek])

  const weekOptions = useMemo(() => {
    const done = new Map((schedules.data ?? []).map((s) => [s.weekStart, s]))
    const all = new Set([...(fweeks.data ?? []).map((f) => f.weekStart), ...done.keys()])
    return [...all].sort().reverse().map((w) => {
      const s = done.get(w)
      return {
        value: w,
        label: `Tuần ${isoWeek(w)} · ${ddmm(w)} – ${ddmm(addDays(w, 6))}${s ? '' : ' · chưa có lịch'}`,
      }
    })
  }, [schedules.data, fweeks.data])

  const active = runs.data?.find((r) => r.storeCode === store && r.weekStart === week && (r.status === 'queued' || r.status === 'running'))
  const lastRunId = useRef<number | null>(null)
  useEffect(() => {
    // tell the user when the run started from this page finishes
    const r = runs.data?.find((x) => x.runId === lastRunId.current)
    if (r && (r.status === 'done' || r.status === 'failed')) {
      if (r.status === 'done') message.success(`Đã xếp lịch store ${r.storeCode} (${r.assessment ?? ''})`)
      else message.error(`Xếp lịch thất bại: ${r.message ?? ''}`)
      lastRunId.current = null
    }
  }, [runs.data])

  const hasSchedule = !!schedules.data?.some((s) => s.weekStart === week)
  const run = () => {
    if (!store || !week) return
    start.mutate({ storeCode: store, weekStart: week }, {
      onSuccess: (r) => { lastRunId.current = r.data.runId; message.info(`Đang xếp lịch store ${store}…`) },
      onError: (e) => message.error(String((e as Error).message)),
    })
  }

  return (
    <div className="filters">
      <div className="field">
        <label>Cửa hàng</label>
        <Select style={{ minWidth: 260 }} value={store ?? undefined} loading={stores.isLoading} showSearch optionFilterProp="label"
          onChange={(v) => setFilters({ store: v }, false)}
          options={(stores.data ?? []).map((s) => ({ value: s.storeCode, label: `${s.storeCode} · ${s.storeName}` }))} />
      </div>
      {showWeek && (
        <div className="field">
          <label>Tuần</label>
          <Select style={{ minWidth: 250 }} value={week ?? undefined} onChange={(v) => setFilters({ week: v }, false)} options={weekOptions} />
        </div>
      )}
      {showActions && (
        <Space>
          {canRun && (
            <Tooltip title="Chạy engine cho store-tuần này (lịch cũ sẽ bị thay)">
              <Button type="primary" icon={<ThunderboltOutlined />} loading={!!active || start.isPending} onClick={run} disabled={!store || !week}>
                {active ? 'Đang xếp lịch…' : hasSchedule ? 'Tạo lại lịch' : 'Tạo lịch'}
              </Button>
            </Tooltip>
          )}
          <Button icon={<DownloadOutlined />} disabled={!hasSchedule} href={hasSchedule ? fileUrl(`/schedules/${store}/${week}/file2`) : undefined}>
            File upload chấm công
          </Button>
        </Space>
      )}
    </div>
  )
}

import { useMemo, useRef, useState } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { PermissionCodes } from '../../shared/api/types'
import type { EmployeeAvailabilitySlotListItemDto } from '../../shared/api/types'
import * as storesApi from '../stores/api'
import * as availabilityApi from './api'
import { EmployeeAvailabilityFormModal } from './EmployeeAvailabilityFormModal'
import { addDays, fmtViDate, snapToMonday, toDateInputValue, weekEndSunday } from './weekUtils'

function defaultAnchor() {
  return snapToMonday(toDateInputValue(new Date()))
}

export function EmployeeAvailabilityPage() {
  const { me, hasPermission } = useAuth()
  const canManage = hasPermission(PermissionCodes.EmployeeAvailabilityManage)
  const qc = useQueryClient()

  const [anchorDate, setAnchorDate] = useState(defaultAnchor)
  const weekMonday = useMemo(() => snapToMonday(anchorDate), [anchorDate])
  const weekSunday = useMemo(() => weekEndSunday(weekMonday), [weekMonday])

  const [plantFilter, setPlantFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<EmployeeAvailabilitySlotListItemDto | null>(null)
  const [importing, setImporting] = useState(false)
  const importRef = useRef<HTMLInputElement>(null)

  const storesQuery = useQuery({
    queryKey: ['stores', 'simple'],
    queryFn: () => storesApi.listStoresSimple(),
    enabled: me?.allStores ?? false,
  })

  const storeOptions = useMemo(() => {
    if (me?.allStores) return storesQuery.data ?? []
    return me?.stores ?? []
  }, [me, storesQuery.data])

  const effectivePlant = plantFilter || storeOptions[0]?.code || ''

  const weekQuery = useQuery({
    queryKey: ['employee-availability', effectivePlant, weekMonday, page, pageSize, search],
    queryFn: () =>
      availabilityApi.getEmployeeAvailabilityWeek(effectivePlant, weekMonday, page, pageSize, search),
    enabled: Boolean(effectivePlant),
  })

  const items = weekQuery.data?.items ?? []
  const totalPages = weekQuery.data?.totalPages ?? 0

  function shiftWeek(delta: number) {
    setAnchorDate(addDays(weekMonday, delta))
    setPage(1)
  }

  async function onExport() {
    if (!effectivePlant) return
    try {
      const { blob, fileName } = await availabilityApi.exportEmployeeAvailabilityExcel(
        effectivePlant,
        weekMonday,
      )
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = fileName
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Export thất bại')
    }
  }

  async function onImportFile(file: File) {
    setImporting(true)
    try {
      const result = await availabilityApi.importEmployeeAvailabilityExcel(weekMonday, file)
      await qc.invalidateQueries({ queryKey: ['employee-availability'] })
      const errText =
        result.errors.length > 0
          ? `\nLỗi:\n${result.errors.slice(0, 10).map((e) => `Dòng ${e.row}: ${e.message}`).join('\n')}`
          : ''
      alert(`Import xong. Thêm: ${result.created}, Lỗi: ${result.failed}.${errText}`)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Import thất bại')
    } finally {
      setImporting(false)
      if (importRef.current) importRef.current.value = ''
    }
  }

  async function onDelete(row: EmployeeAvailabilitySlotListItemDto) {
    if (!window.confirm(`Xóa lịch bận ${row.employeeName} ngày ${fmtViDate(row.workDate)}?`)) return
    try {
      await availabilityApi.deleteEmployeeAvailabilitySlot(row.id)
      await qc.invalidateQueries({ queryKey: ['employee-availability'] })
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Lỗi xóa')
    }
  }

  return (
    <>
      <div className="pl-admin-shell">
        <div className="pl-admin-toolbar">
          <h3>Lịch bận nhân viên</h3>
          {canManage && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn primary"
                disabled={!effectivePlant}
                onClick={() => {
                  setEditing(null)
                  setModalOpen(true)
                }}
              >
                Thêm bận
              </button>
              <button type="button" className="btn" disabled={!effectivePlant} onClick={() => void onExport()}>
                Export Excel
              </button>
              <button
                type="button"
                className="btn"
                disabled={importing || !effectivePlant}
                onClick={() => importRef.current?.click()}
              >
                {importing ? 'Đang import...' : 'Import Excel'}
              </button>
              <input
                ref={importRef}
                type="file"
                accept=".xlsx,.xlsm"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) void onImportFile(f)
                }}
              />
            </div>
          )}
        </div>

        <div
          style={{
            marginBottom: 16,
            padding: '12px 16px',
            background: 'var(--surface-2, #f5f5f5)',
            borderRadius: 8,
          }}
        >
          <strong>
            Tuần từ {fmtViDate(weekQuery.data?.weekStartMonday ?? weekMonday)} đến{' '}
            {fmtViDate(weekQuery.data?.weekEndSunday ?? weekSunday)}
          </strong>
        </div>

        <div className="pl-admin-filters" style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            Plant
            <select
              value={effectivePlant}
              onChange={(e) => {
                setPlantFilter(e.target.value)
                setPage(1)
              }}
            >
              {storeOptions.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.code}
                  {s.name ? ` — ${s.name}` : ''}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            Ngày trong tuần
            <input
              type="date"
              value={anchorDate}
              onChange={(e) => {
                setAnchorDate(e.target.value)
                setPage(1)
              }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, justifyContent: 'flex-end' }}>
            <span style={{ visibility: 'hidden' }}>.</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="btn" onClick={() => shiftWeek(-7)}>
                ← Tuần trước
              </button>
              <button type="button" className="btn" onClick={() => shiftWeek(7)}>
                Tuần sau →
              </button>
            </div>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 200px' }}>
            Tìm nhân viên
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                placeholder="Tên hoặc Employee ID..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setSearch(searchInput)
                    setPage(1)
                  }
                }}
              />
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setSearch(searchInput)
                  setPage(1)
                }}
              >
                Tìm
              </button>
            </div>
          </label>
        </div>

        {!effectivePlant ? (
          <p>Chọn Plant để xem lịch bận.</p>
        ) : weekQuery.isLoading ? (
          <PageLoading compact />
        ) : (
          <>
            <div className="pl-table-wrap">
              <table className="pl-table">
                <thead>
                  <tr>
                    <th>Employee ID</th>
                    <th>Tên</th>
                    <th>Ngày</th>
                    <th>Bận từ</th>
                    <th>Bận đến</th>
                    {canManage && <th />}
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={canManage ? 6 : 5} style={{ textAlign: 'center', padding: 24 }}>
                        Không có lịch bận trong tuần (nhân viên không có dòng = available cả tuần).
                      </td>
                    </tr>
                  ) : (
                    items.map((row) => (
                      <tr key={row.id}>
                        <td>{row.employeeNumber}</td>
                        <td>{row.employeeName}</td>
                        <td>
                          {row.weekdayLabel} — {fmtViDate(row.workDate)}
                        </td>
                        <td>{row.isPaidLeave ? 'AL' : row.busyFrom}</td>
                        <td>{row.isPaidLeave ? 'AL' : row.busyTo}</td>
                        {canManage && (
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={() => {
                                setEditing(row)
                                setModalOpen(true)
                              }}
                            >
                              Sửa
                            </button>{' '}
                            <button type="button" className="btn btn-sm" onClick={() => void onDelete(row)}>
                              Xóa
                            </button>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className="pl-pagination" style={{ marginTop: 16 }}>
                <button
                  type="button"
                  className="btn"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Trang trước
                </button>
                <span>
                  Trang {page} / {totalPages}
                </span>
                <button
                  type="button"
                  className="btn"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Trang sau
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <EmployeeAvailabilityFormModal
        open={modalOpen}
        weekDate={weekMonday}
        plantCode={effectivePlant}
        editing={editing}
        onClose={() => {
          setModalOpen(false)
          setEditing(null)
        }}
        onSaved={() => void qc.invalidateQueries({ queryKey: ['employee-availability'] })}
      />
    </>
  )
}
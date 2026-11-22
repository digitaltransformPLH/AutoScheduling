import { useRef, useState } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import type { EmployeeSecondmentListItemDto } from '../../shared/api/types'
import { PermissionCodes } from '../../shared/api/types'
import * as storesApi from '../stores/api'
import * as employeesApi from './api'
import { EmployeeFormModal } from './EmployeeFormModal'
import { EmployeeSecondmentFormModal } from './EmployeeSecondmentFormModal'

type MainTab = 'employees' | 'secondments'

function fmtDt(iso: string) {
  try {
    return new Date(iso).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('vi-VN')
  } catch {
    return iso.slice(0, 10)
  }
}

export function EmployeesPage() {
  const { me, hasPermission } = useAuth()
  const canManage = hasPermission(PermissionCodes.EmployeeManage)

  const qc = useQueryClient()
  const [mainTab, setMainTab] = useState<MainTab>('employees')

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [plantFilter, setPlantFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [importing, setImporting] = useState(false)
  const importFileRef = useRef<HTMLInputElement>(null)

  const [secPage, setSecPage] = useState(1)
  const [secPageSize, setSecPageSize] = useState(20)
  const [secSearch, setSecSearch] = useState('')
  const [secSearchInput, setSecSearchInput] = useState('')
  const [secPlantFilter, setSecPlantFilter] = useState('')
  const [secStatusFilter, setSecStatusFilter] = useState('')

  const [secondmentModalOpen, setSecondmentModalOpen] = useState(false)
  const [secondmentEmployeeId, setSecondmentEmployeeId] = useState<number | null>(null)
  const [editingSecondment, setEditingSecondment] = useState<EmployeeSecondmentListItemDto | null>(
    null,
  )

  const storesQuery = useQuery({
    queryKey: ['stores', 'simple'],
    queryFn: () => storesApi.listStoresSimple(),
    enabled: me?.allStores ?? false,
  })

  const lookupsQuery = useQuery({
    queryKey: ['employees', 'lookups'],
    queryFn: () => employeesApi.getEmployeeLookups(),
  })

  const employeesQuery = useQuery({
    queryKey: ['employees', 'paged', page, pageSize, search, plantFilter],
    queryFn: () => employeesApi.listEmployeesPaged(page, pageSize, search, plantFilter || undefined),
    enabled: mainTab === 'employees',
  })

  const secondmentsQuery = useQuery({
    queryKey: [
      'employee-secondments',
      'paged',
      secPage,
      secPageSize,
      secSearch,
      secPlantFilter,
      secStatusFilter,
    ],
    queryFn: () =>
      employeesApi.listEmployeeSecondmentsPaged(
        secPage,
        secPageSize,
        secSearch,
        secPlantFilter || undefined,
        secStatusFilter || undefined,
      ),
    enabled: mainTab === 'secondments',
  })

  const data = employeesQuery.data
  const items = data?.items ?? []
  const totalPages = data?.totalPages ?? 0

  const secData = secondmentsQuery.data
  const secItems = secData?.items ?? []
  const secTotalPages = secData?.totalPages ?? 0

  const stores = me?.allStores
    ? (storesQuery.data ?? [])
    : (me?.stores ?? []).map((s) => ({ id: s.id, code: s.code, name: s.name, isActive: true }))

  const secondmentEmployee =
    secondmentEmployeeId != null
      ? items.find((e) => e.id === secondmentEmployeeId) ?? null
      : null

  function runSearch() {
    setSearch(searchInput.trim())
    setPage(1)
  }

  function runSecSearch() {
    setSecSearch(secSearchInput.trim())
    setSecPage(1)
  }

  async function onExportExcel() {
    try {
      const { blob, fileName } = await employeesApi.exportEmployeesExcel(plantFilter || undefined)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Xuất Excel thất bại')
    }
  }

  async function onImportFile(file: File) {
    setImporting(true)
    try {
      const result = await employeesApi.importEmployeesExcel(file)
      if (
        plantFilter &&
        me &&
        !me.allStores &&
        !me.stores.some((s) => s.code.toLowerCase() === plantFilter.toLowerCase())
      ) {
        setPlantFilter('')
      }
      await qc.invalidateQueries({ queryKey: ['employees'] })
      const errLines = result.errors
        .slice(0, 8)
        .map((x) => `Dòng ${x.row}: ${x.message}`)
        .join('\n')
      alert(
        `Import xong.\nThêm mới: ${result.created}\nCập nhật: ${result.updated}\nLỗi: ${result.failed}` +
          (errLines ? `\n\n${errLines}${result.errors.length > 8 ? '\n...' : ''}` : ''),
      )
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Import thất bại')
    } finally {
      setImporting(false)
      if (importFileRef.current) importFileRef.current.value = ''
    }
  }

  async function onDelete(id: number, name: string) {
    if (!window.confirm(`Xóa nhân viên ${name}?`)) return
    try {
      await employeesApi.deleteEmployee(id)
      await qc.invalidateQueries({ queryKey: ['employees'] })
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Lỗi')
    }
  }

  async function onCancelSecondment(row: EmployeeSecondmentListItemDto) {
    if (!window.confirm(`Hủy điều động của ${row.fullName}?`)) return
    try {
      await employeesApi.cancelEmployeeSecondment(row.id)
      await qc.invalidateQueries({ queryKey: ['employee-secondments'] })
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Lỗi')
    }
  }

  function onEmployeeAction(employeeId: number, action: string, fullName: string) {
    if (action === 'edit') {
      setEditingId(employeeId)
      setModalOpen(true)
    } else if (action === 'delete') {
      void onDelete(employeeId, fullName)
    } else if (action === 'secondment') {
      setSecondmentEmployeeId(employeeId)
      setEditingSecondment(null)
      setSecondmentModalOpen(true)
    }
  }

  function onSavedSecondment() {
    void qc.invalidateQueries({ queryKey: ['employee-secondments'] })
    void qc.invalidateQueries({ queryKey: ['employees'] })
  }

  return (
    <>
      <div className="pl-admin-shell">
        <div className="pl-admin-toolbar">
          <h3>Quản lý nhân viên</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {mainTab === 'employees' && (
              <>
                <button type="button" className="btn" onClick={() => void onExportExcel()}>
                  Xuất Excel
                </button>
                {canManage && (
                  <>
                    <input
                      ref={importFileRef}
                      type="file"
                      accept=".xlsx,.xlsm"
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        const f = e.target.files?.[0]
                        if (f) void onImportFile(f)
                      }}
                    />
                    <button
                      type="button"
                      className="btn"
                      disabled={importing}
                      onClick={() => importFileRef.current?.click()}
                    >
                      {importing ? 'Đang import...' : 'Import Excel'}
                    </button>
                    <button
                      type="button"
                      className="btn primary"
                      onClick={() => {
                        setEditingId(null)
                        setModalOpen(true)
                      }}
                    >
                      + Thêm nhân viên
                    </button>
                  </>
                )}
              </>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 12, padding: '0 4px' }}>
          <button
            type="button"
            className={`btn${mainTab === 'employees' ? ' primary' : ''}`}
            onClick={() => setMainTab('employees')}
          >
            Danh sách nhân viên
          </button>
          <button
            type="button"
            className={`btn${mainTab === 'secondments' ? ' primary' : ''}`}
            onClick={() => setMainTab('secondments')}
          >
            Điều động tạm
          </button>
        </div>

        {mainTab === 'employees' && (
          <>
            <div className="pl-admin-toolbar pl-admin-filters">
              <input
                type="search"
                placeholder="Tìm tên, Employee ID, plant..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runSearch()}
                style={{ minWidth: 220, flex: 1 }}
              />
              <label>
                Plant{' '}
                <select
                  value={plantFilter}
                  onChange={(e) => {
                    setPlantFilter(e.target.value)
                    setPage(1)
                  }}
                >
                  <option value="">Tất cả</option>
                  {stores.map((s) => (
                    <option key={s.id} value={s.code}>
                      {s.code}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Số dòng{' '}
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value))
                    setPage(1)
                  }}
                >
                  {[10, 20, 50, 100].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="btn" onClick={runSearch}>
                Tìm
              </button>
            </div>
            <div className="pl-admin-card">
              {employeesQuery.isLoading && <PageLoading compact />}
              {!employeesQuery.isLoading && (
                <>
                  <table className="pl-admin-table">
                    <thead>
                      <tr>
                        <th>Employee ID</th>
                        <th>Tên</th>
                        <th>Plant</th>
                        <th>Position</th>
                        <th>Employment Type</th>
                        <th>Labor group</th>
                        <th>Status</th>
                        <th>CreatedAt</th>
                        <th>UpdatedAt</th>
                        {canManage && <th>Thao tác</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {items.length === 0 ? (
                        <tr>
                          <td colSpan={canManage ? 10 : 9}>Không có dữ liệu</td>
                        </tr>
                      ) : (
                        items.map((e) => (
                          <tr key={e.id}>
                            <td>{e.employeeNumber}</td>
                            <td>{e.fullName}</td>
                            <td>
                              {e.plantCode}
                              {e.plantName ? ` — ${e.plantName}` : ''}
                            </td>
                            <td>{e.position}</td>
                            <td>{e.employmentType}</td>
                            <td>{e.laborGroup}</td>
                            <td>
                              <span className={`pill ${e.status === 'Active' ? 'on' : 'off'}`}>
                                {e.status}
                              </span>
                            </td>
                            <td>{fmtDt(e.createdAt)}</td>
                            <td>{fmtDt(e.updatedAt)}</td>
                            {canManage && (
                              <td>
                                <select
                                  defaultValue=""
                                  title="Thao tác"
                                  onChange={(ev) => {
                                    const action = ev.target.value
                                    ev.target.value = ''
                                    if (action) onEmployeeAction(e.id, action, e.fullName)
                                  }}
                                  style={{ minWidth: 120 }}
                                >
                                  <option value="">— Chọn —</option>
                                  <option value="edit">Sửa</option>
                                  <option value="secondment">Điều động tạm</option>
                                  <option value="delete">Xóa</option>
                                </select>
                              </td>
                            )}
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                  <div className="pl-admin-pagination">
                    <div className="info">
                      Trang {page}
                      {totalPages > 0 ? ` / ${totalPages}` : ''}
                      {data ? ` — ${data.total} nhân viên` : ''}
                    </div>
                    <div className="pages">
                      <button
                        type="button"
                        className="btn"
                        disabled={page <= 1}
                        onClick={() => setPage((p) => p - 1)}
                      >
                        Trước
                      </button>
                      <button
                        type="button"
                        className="btn"
                        disabled={totalPages > 0 ? page >= totalPages : items.length < pageSize}
                        onClick={() => setPage((p) => p + 1)}
                      >
                        Sau
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </>
        )}

        {mainTab === 'secondments' && (
          <>
            <div className="pl-admin-toolbar pl-admin-filters">
              <input
                type="search"
                placeholder="Tìm tên, Employee ID, store..."
                value={secSearchInput}
                onChange={(e) => setSecSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runSecSearch()}
                style={{ minWidth: 220, flex: 1 }}
              />
              <label>
                Plant{' '}
                <select
                  value={secPlantFilter}
                  onChange={(e) => {
                    setSecPlantFilter(e.target.value)
                    setSecPage(1)
                  }}
                >
                  <option value="">Tất cả</option>
                  {stores.map((s) => (
                    <option key={s.id} value={s.code}>
                      {s.code}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Trạng thái{' '}
                <select
                  value={secStatusFilter}
                  onChange={(e) => {
                    setSecStatusFilter(e.target.value)
                    setSecPage(1)
                  }}
                >
                  <option value="">Tất cả</option>
                  <option value="Active">Active</option>
                  <option value="Cancelled">Cancelled</option>
                </select>
              </label>
              <label>
                Số dòng{' '}
                <select
                  value={secPageSize}
                  onChange={(e) => {
                    setSecPageSize(Number(e.target.value))
                    setSecPage(1)
                  }}
                >
                  {[10, 20, 50, 100].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="btn" onClick={runSecSearch}>
                Tìm
              </button>
            </div>
            <div className="pl-admin-card">
              {secondmentsQuery.isLoading && <PageLoading compact />}
              {!secondmentsQuery.isLoading && (
                <>
                  <table className="pl-admin-table">
                    <thead>
                      <tr>
                        <th>Employee ID</th>
                        <th>Tên</th>
                        <th>Plant gốc</th>
                        <th>Store nhận</th>
                        <th>Từ ngày</th>
                        <th>Đến ngày</th>
                        <th>Trạng thái</th>
                        <th>Cập nhật</th>
                        <th>Người cập nhật</th>
                        {canManage && <th />}
                      </tr>
                    </thead>
                    <tbody>
                      {secItems.length === 0 ? (
                        <tr>
                          <td colSpan={canManage ? 10 : 9}>Không có dữ liệu</td>
                        </tr>
                      ) : (
                        secItems.map((row) => (
                          <tr key={row.id}>
                            <td>{row.employeeNumber}</td>
                            <td>{row.fullName}</td>
                            <td>
                              {row.homePlantCode}
                              {row.homePlantName ? ` — ${row.homePlantName}` : ''}
                            </td>
                            <td>
                              {row.receivingStoreCode}
                              {row.receivingStoreName ? ` — ${row.receivingStoreName}` : ''}
                            </td>
                            <td>{fmtDate(row.startDate)}</td>
                            <td>{fmtDate(row.endDate)}</td>
                            <td>
                              <span
                                className={`pill ${row.status === 'Active' ? 'on' : 'off'}`}
                              >
                                {row.status}
                              </span>
                            </td>
                            <td>{fmtDt(row.updatedAt)}</td>
                            <td>{row.updatedBy}</td>
                            {canManage && (
                              <td>
                                {row.status === 'Active' && (
                                  <>
                                    <button
                                      type="button"
                                      className="btn link"
                                      onClick={() => {
                                        setSecondmentEmployeeId(null)
                                        setEditingSecondment(row)
                                        setSecondmentModalOpen(true)
                                      }}
                                    >
                                      Sửa
                                    </button>
                                    {' · '}
                                    <button
                                      type="button"
                                      className="btn link danger"
                                      onClick={() => void onCancelSecondment(row)}
                                    >
                                      Hủy
                                    </button>
                                  </>
                                )}
                              </td>
                            )}
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                  <div className="pl-admin-pagination">
                    <div className="info">
                      Trang {secPage}
                      {secTotalPages > 0 ? ` / ${secTotalPages}` : ''}
                      {secData ? ` — ${secData.total} bản ghi` : ''}
                    </div>
                    <div className="pages">
                      <button
                        type="button"
                        className="btn"
                        disabled={secPage <= 1}
                        onClick={() => setSecPage((p) => p - 1)}
                      >
                        Trước
                      </button>
                      <button
                        type="button"
                        className="btn"
                        disabled={
                          secTotalPages > 0
                            ? secPage >= secTotalPages
                            : secItems.length < secPageSize
                        }
                        onClick={() => setSecPage((p) => p + 1)}
                      >
                        Sau
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </>
        )}
      </div>

      {canManage && (
        <>
          <EmployeeFormModal
            open={modalOpen}
            employeeId={editingId}
            stores={stores}
            lookups={lookupsQuery.data}
            onClose={() => setModalOpen(false)}
            onSaved={() => void qc.invalidateQueries({ queryKey: ['employees'] })}
          />
          <EmployeeSecondmentFormModal
            open={secondmentModalOpen}
            employee={secondmentEmployee}
            secondment={editingSecondment}
            stores={stores}
            onClose={() => setSecondmentModalOpen(false)}
            onSaved={onSavedSecondment}
          />
        </>
      )}
    </>
  )
}
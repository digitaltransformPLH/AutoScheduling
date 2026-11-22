import { useRef, useState } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { PermissionCodes } from '../../shared/api/types'
import * as storeConfigApi from './api'
import { StoreConfigFormModal } from './StoreConfigFormModal'

function fmtNum(value: number | null | undefined, digits = 2) {
  if (value == null) return '—'
  return Number.isInteger(value) ? String(value) : value.toFixed(digits)
}

export function StoreConfigPage() {
  const qc = useQueryClient()
  const { hasPermission } = useAuth()
  const canManage = hasPermission(PermissionCodes.StoreConfigManage)

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingStoreId, setEditingStoreId] = useState<number | null>(null)
  const [importing, setImporting] = useState(false)
  const [exporting, setExporting] = useState(false)
  const importFileRef = useRef<HTMLInputElement>(null)

  const listQuery = useQuery({
    queryKey: ['store-configs', page, pageSize, search],
    queryFn: () => storeConfigApi.listStoreConfigsPaged(page, pageSize, search),
  })

  const data = listQuery.data
  const items = data?.items ?? []
  const totalPages = data?.totalPages ?? 0

  function runSearch() {
    setSearch(searchInput.trim())
    setPage(1)
  }

  async function onExport() {
    setExporting(true)
    try {
      const { blob, fileName } = await storeConfigApi.exportStoreConfigsExcel()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Export thất bại')
    } finally {
      setExporting(false)
    }
  }

  async function onImportFile(file: File) {
    setImporting(true)
    try {
      const result = await storeConfigApi.importStoreConfigsExcel(file)
      const errPreview =
        result.errors.length > 0
          ? `\n\nChi tiết lỗi (tối đa 5 dòng đầu):\n${result.errors
              .slice(0, 5)
              .map((e) => `- Dòng ${e.row}${e.plantCode ? ` (${e.plantCode})` : ''}: ${e.message}`)
              .join('\n')}`
          : ''
      alert(
        `Import xong.\nThêm mới: ${result.created}\nCập nhật: ${result.updated}\nLỗi: ${result.failed}${errPreview}`,
      )
      await qc.invalidateQueries({ queryKey: ['store-configs'] })
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Import thất bại')
    } finally {
      setImporting(false)
      if (importFileRef.current) importFileRef.current.value = ''
    }
  }

  return (
    <>
      <div className="pl-admin-shell">
        <div className="pl-admin-toolbar">
          <h3>Cấu hình cửa hàng (OPS)</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn"
              disabled={exporting}
              onClick={() => void onExport()}
            >
              {exporting ? 'Đang tải file…' : 'Tải mẫu Excel'}
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
                  className="btn primary"
                  disabled={importing}
                  onClick={() => importFileRef.current?.click()}
                >
                  {importing ? 'Đang import…' : 'Import Excel'}
                </button>
              </>
            )}
          </div>
        </div>
        <div className="pl-admin-toolbar pl-admin-filters">
          <input
            type="search"
            placeholder="Tìm mã hoặc tên cửa hàng..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runSearch()}
            style={{ minWidth: 220, flex: 1 }}
          />
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
          {listQuery.isLoading && <PageLoading compact />}
          {!listQuery.isLoading && (
            <>
              <table className="pl-admin-table">
                <thead>
                  <tr>
                    <th>Mã</th>
                    <th>Tên</th>
                    <th>TCPH target</th>
                    <th>Ceiling mult</th>
                    <th>Open</th>
                    <th>Close</th>
                    <th>Min/slot</th>
                    <th>Trạng thái</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={9}>Không có dữ liệu</td>
                    </tr>
                  ) : (
                    items.map((row) => (
                      <tr key={row.storeId}>
                        <td>{row.storeCode}</td>
                        <td>{row.storeName}</td>
                        <td>{fmtNum(row.tcphTarget)}</td>
                        <td>{fmtNum(row.tcphCeilingMult)}</td>
                        <td>{fmtNum(row.openStaff, 0)}</td>
                        <td>{fmtNum(row.closeStaff, 0)}</td>
                        <td>{fmtNum(row.minStaffPerSlot, 0)}</td>
                        <td>
                          <span className={`pill ${row.isConfigured ? 'on' : 'off'}`}>
                            {row.isConfigured ? 'Đã cấu hình' : 'Chưa cấu hình'}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn link"
                            onClick={() => {
                              setEditingStoreId(row.storeId)
                              setModalOpen(true)
                            }}
                          >
                            {canManage ? 'Sửa' : 'Xem'}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              <div className="pl-admin-pagination">
                <div className="info">
                  Trang {page}
                  {totalPages > 0 ? ` / ${totalPages}` : ''}
                  {data ? ` — ${data.total} cửa hàng` : ''}
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
      </div>

      <StoreConfigFormModal
        open={modalOpen}
        storeId={editingStoreId}
        onClose={() => setModalOpen(false)}
        onSaved={() => void qc.invalidateQueries({ queryKey: ['store-configs'] })}
      />
    </>
  )
}
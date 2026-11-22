import { useState } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import * as storesApi from './api'
import { StoreFormModal } from './StoreFormModal'

export function StoresPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)

  const storesQuery = useQuery({
    queryKey: ['stores', 'paged', page, pageSize, search],
    queryFn: () => storesApi.listStoresPaged(page, pageSize, search),
  })

  const amQuery = useQuery({
    queryKey: ['persons', 'AM'],
    queryFn: () => storesApi.listPersons('AM'),
  })

  const data = storesQuery.data
  const items = data?.items ?? []
  const totalPages = data?.totalPages ?? 0

  function runSearch() {
    setSearch(searchInput.trim())
    setPage(1)
  }

  async function onDelete(id: number, code: string) {
    if (!window.confirm(`Xóa cửa hàng ${code}?`)) return
    try {
      await storesApi.deleteStore(id)
      await qc.invalidateQueries({ queryKey: ['stores'] })
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Lỗi')
    }
  }

  return (
    <>
      <div className="pl-admin-shell">
        <div className="pl-admin-toolbar">
          <h3>Quản lý cửa hàng</h3>
          <button
            type="button"
            className="btn primary"
            onClick={() => {
              setEditingId(null)
              setModalOpen(true)
            }}
          >
            + Thêm cửa hàng
          </button>
        </div>
        <div className="pl-admin-toolbar pl-admin-filters">
          <input
            type="search"
            placeholder="Tìm mã, tên, thành phố, AM..."
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
          {storesQuery.isLoading && <PageLoading compact />}
          {!storesQuery.isLoading && (
            <>
              <table className="pl-admin-table">
                <thead>
                  <tr>
                    <th>Mã</th>
                    <th>Tên</th>
                    <th>AM</th>
                    <th>OM</th>
                    <th>Thành phố</th>
                    <th>Trạng thái</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={7}>Không có dữ liệu</td>
                    </tr>
                  ) : (
                    items.map((s) => (
                      <tr key={s.id}>
                        <td>{s.code}</td>
                        <td>{s.name}</td>
                        <td>{s.areaManagerName ?? '—'}</td>
                        <td>{s.operationManagerName ?? '—'}</td>
                        <td>{s.city ?? '—'}</td>
                        <td>
                          <span className={`pill ${s.isActive ? 'on' : 'off'}`}>
                            {s.isActive ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn link"
                            onClick={() => {
                              setEditingId(s.id)
                              setModalOpen(true)
                            }}
                          >
                            Sửa
                          </button>
                          {' · '}
                          <button
                            type="button"
                            className="btn link danger"
                            onClick={() => void onDelete(s.id, s.code)}
                          >
                            Xóa
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

      <StoreFormModal
        open={modalOpen}
        storeId={editingId}
        areaManagers={amQuery.data ?? []}
        onClose={() => setModalOpen(false)}
        onSaved={() => void qc.invalidateQueries({ queryKey: ['stores'] })}
      />
    </>
  )
}

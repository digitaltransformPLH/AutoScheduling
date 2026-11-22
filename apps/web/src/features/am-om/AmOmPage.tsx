import { useState } from 'react'
import { PageLoading } from '../../shared/components/PageLoading'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listPersons } from '../stores/api'
import * as amOmApi from './api'
import { AmOmFormModal } from './AmOmFormModal'
import type { AmOmAssignmentDto } from '../../shared/api/types'

export function AmOmPage() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AmOmAssignmentDto | null>(null)

  const listQuery = useQuery({ queryKey: ['am-om'], queryFn: amOmApi.listAmOm })
  const amQuery = useQuery({ queryKey: ['persons', 'AM'], queryFn: () => listPersons('AM') })
  const omQuery = useQuery({ queryKey: ['persons', 'ROM'], queryFn: () => listPersons('ROM') })

  const rows = listQuery.data ?? []

  return (
    <>
      <div className="pl-admin-shell">
        <div className="pl-admin-toolbar">
          <h3>Mapping AM → OM</h3>
          <button
            type="button"
            className="btn primary"
            onClick={() => {
              setEditing(null)
              setModalOpen(true)
            }}
          >
            + Thêm mapping
          </button>
        </div>
        <div className="pl-admin-card">
          {listQuery.isLoading && <PageLoading compact />}
          {!listQuery.isLoading && (
            <table className="pl-admin-table">
              <thead>
                <tr>
                  <th>Area Manager</th>
                  <th>Operation Manager</th>
                  <th>Hiệu lực từ</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={4}>Chưa có mapping</td>
                  </tr>
                ) : (
                  rows.map((r) => (
                    <tr key={r.id}>
                      <td>{r.areaManagerName}</td>
                      <td>{r.operationManagerName}</td>
                      <td>{r.effectiveFrom}</td>
                      <td>
                        <button
                          type="button"
                          className="btn link"
                          onClick={() => {
                            setEditing(r)
                            setModalOpen(true)
                          }}
                        >
                          Sửa
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <AmOmFormModal
        open={modalOpen}
        row={editing}
        areaManagers={amQuery.data ?? []}
        operationManagers={omQuery.data ?? []}
        onClose={() => setModalOpen(false)}
        onSaved={() => void qc.invalidateQueries({ queryKey: ['am-om'] })}
      />
    </>
  )
}

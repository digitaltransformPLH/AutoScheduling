// Engine inputs: view + edit (form or Excel upload) [19-Nov-2026: editing moved here from the .NET app].
// Each tab shows its edit buttons only when the user has the matching .NET permission; the API checks again.
import { Alert, Tabs } from 'antd'
import { useEffect, useState } from 'react'
import { useEmployees, useInputOptions, useMe, useMeta, useSecondments } from '../api/hooks'
import { ddmmyyyy } from '../lib/format'
import { StoreWeekPicker } from '../components/StoreWeekPicker'
import { BusyTab } from '../components/inputs/BusyTab'
import { ConfigTab } from '../components/inputs/ConfigTab'
import { EmployeesTab } from '../components/inputs/EmployeesTab'
import { SecondmentsTab } from '../components/inputs/SecondmentsTab'
import { useUrlFilters } from '../lib/useUrlFilters'

export function InputsPage() {
  const [{ store }] = useUrlFilters()
  const me = useMe().data
  const meta = useMeta()
  const options = useInputOptions(store)
  const emps = useEmployees(store)
  const sec = useSecondments(store)
  const [busyWeek, setBusyWeek] = useState<string | null>(null)
  useEffect(() => { setBusyWeek(null) }, [store])
  useEffect(() => {
    if (!busyWeek && options.data?.availabilityWeeks.length) setBusyWeek(options.data.availabilityWeeks[0])
  }, [busyWeek, options.data])

  if (!me) return null
  const canEditAny = me.can.employeeEdit || me.can.availabilityEdit || me.can.configEdit
  const nActive = (emps.data ?? []).filter((e) => e.status === 'Active').length
  return (
    <main className="page">
      <div className="head">
        <div>
          <div className="kicker">Dữ liệu đầu vào · Store {store ?? '—'}</div>
          <h1 className="action-title">Dữ liệu engine dùng để xếp lịch</h1>
          <div className="sub">{canEditAny
            ? 'Sửa trực tiếp hoặc tải Excel về, sửa rồi upload lại (thay dữ liệu cũ). Sau khi sửa, bấm "Tạo lại lịch" ở trang Tổng quan.'
            : 'Chỉ xem — tài khoản của bạn chưa có quyền sửa dữ liệu.'}</div>
        </div>
        <StoreWeekPicker showActions={false} showWeek={false} readyOnly={false} />
      </div>
      {meta.data?.backTest && (
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
          message={`Chế độ back-test: được xếp lịch cho tuần đã qua${meta.data.availabilityWeek
            ? `; lịch bận tuần ${ddmmyyyy(meta.data.availabilityWeek)} được dùng lại theo thứ trong tuần cho tuần đang xếp` : ''}.`} />
      )}
      {store && (
        <div className="card">
          <Tabs items={[
            { key: 'emp', label: `Nhân viên (${nActive})`, children: <EmployeesTab store={store} me={me} options={options.data} busyWeek={busyWeek} /> },
            { key: 'busy', label: 'Lịch bận', children: <BusyTab store={store} me={me} options={options.data} week={busyWeek} setWeek={setBusyWeek} /> },
            { key: 'sec', label: `Cho mượn nhân sự (${sec.data?.length ?? 0})`, children: <SecondmentsTab store={store} me={me} /> },
            { key: 'cfg', label: 'Cấu hình store', children: <ConfigTab store={store} me={me} /> },
          ]} />
        </div>
      )}
    </main>
  )
}

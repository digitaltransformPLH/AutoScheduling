// Employees of the store: add / edit / set Inactive, or replace the list with the store's "Availability File".
import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { App, Button, Checkbox, Form, Input, Modal, Popconfirm, Segmented, Select, Space, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import type { EmployeeIn, EmployeeItem, InputOptions, Me, Saved } from '../../api/client'
import { fileUrl, sendJson } from '../../api/client'
import { useEmployees, useInputMutation } from '../../api/hooks'
import { Pill } from '../Pill'
import { ExcelImport } from './ExcelImport'

type Props = { store: string; me: Me; options?: InputOptions; busyWeek: string | null }

export function EmployeesTab({ store, me, options, busyWeek }: Props) {
  const { message } = App.useApp()
  const emps = useEmployees(store)
  const [show, setShow] = useState<'Active' | 'Tất cả'>('Active')
  const [editing, setEditing] = useState<EmployeeItem | 'new' | null>(null)
  const [form] = Form.useForm<EmployeeIn>()
  const [repEmp, setRepEmp] = useState(me.can.employeeEdit)
  const [repBusy, setRepBusy] = useState(me.can.availabilityEdit)
  const save = useInputMutation((v: EmployeeIn) => editing === 'new'
    ? sendJson<Saved>('/inputs/employees', { ...v, storeCode: store })
    : sendJson<Saved>(`/inputs/employees/${v.employeeId}`, v, 'PUT'))
  const setStatus = useInputMutation((e: EmployeeItem) => sendJson<Saved>(`/inputs/employees/${e.employeeId}`, {
    employeeName: e.employeeName, position: e.position, employmentType: e.employmentType, laborGroup: e.laborGroup,
    status: e.status === 'Active' ? 'Inactive' : 'Active',
  }, 'PUT'))

  const open = (e: EmployeeItem | 'new') => {
    setEditing(e)
    form.setFieldsValue(e === 'new'
      ? { employeeId: '', employeeName: '', position: 'Crew member', employmentType: 'PT', laborGroup: 'Regular', status: 'Active' } as EmployeeIn
      : { ...e } as unknown as EmployeeIn)
  }
  const submit = () => form.validateFields().then((v) => save.mutate(v, {
    onSuccess: (r) => { message.success(r.message); setEditing(null) },
    onError: (e) => message.error((e as Error).message),
  }))
  const opt = (xs?: string[]) => (xs ?? []).map((x) => ({ value: x, label: x }))
  const data = (emps.data ?? []).filter((e) => show === 'Tất cả' || e.status === 'Active')
  const nActive = (emps.data ?? []).filter((e) => e.status === 'Active').length

  const cols: ColumnsType<EmployeeItem> = [
    { title: 'Mã NV', dataIndex: 'employeeId', width: 100 }, { title: 'Họ tên', dataIndex: 'employeeName' },
    { title: 'Vị trí', dataIndex: 'position', filters: [...new Set(data.map((e) => e.position))].map((p) => ({ text: p, value: p })),
      onFilter: (v, r) => r.position === v },
    { title: 'FT/PT', dataIndex: 'employmentType', width: 70 }, { title: 'Nhóm', dataIndex: 'laborGroup', width: 100 },
    { title: 'Trạng thái', dataIndex: 'status', width: 110, render: (v) => <Pill tone={v === 'Active' ? 'good' : 'neutral'}>{v === 'Active' ? 'Đang làm' : 'Ngừng làm'}</Pill> },
    { title: 'Cập nhật', dataIndex: 'updatedAt', width: 140, render: (v) => <span className="card-sub">{v ?? ''}</span> },
    ...(me.can.employeeEdit ? [{
      title: '', key: 'act', width: 170, render: (_: unknown, r: EmployeeItem) => (
        <Space size={4}>
          <Button size="small" icon={<EditOutlined />} onClick={() => open(r)}>Sửa</Button>
          <Popconfirm title={r.status === 'Active' ? `Chuyển ${r.employeeName} sang Ngừng làm?` : `${r.employeeName} đi làm lại?`}
            description={r.status === 'Active' ? 'Không xếp lịch cho người này nữa; dữ liệu cũ vẫn giữ.' : undefined} okText="Đồng ý"
            onConfirm={() => setStatus.mutate(r, { onSuccess: (x) => message.success(x.message), onError: (e) => message.error((e as Error).message) })}>
            <Button size="small" type="link" danger={r.status === 'Active'} loading={setStatus.isPending && setStatus.variables?.employeeId === r.employeeId}>
              {r.status === 'Active' ? 'Cho nghỉ' : 'Đi làm lại'}
            </Button>
          </Popconfirm>
        </Space>),
    }] : []),
  ]

  return (
    <>
      <div className="toolbar">
        <Segmented value={show} onChange={(v) => setShow(v as typeof show)} options={[
          { value: 'Active', label: `Đang làm (${nActive})` }, { value: 'Tất cả', label: `Tất cả (${emps.data?.length ?? 0})` }]} />
        <span className="grow" />
        {me.can.employeeEdit && <Button type="primary" icon={<PlusOutlined />} onClick={() => open('new')}>Thêm nhân viên</Button>}
        <ExcelImport title={`Upload Availability File · store ${store}`} path="/inputs/excel/availability-file"
          fields={{ store, week: busyWeek ?? '', replace_employees: repEmp, replace_busy: repBusy }}
          downloadHref={busyWeek ? fileUrl('/inputs/excel/availability-file', { store, week: busyWeek }) : null}
          canUpload={me.can.employeeEdit || me.can.availabilityEdit}
          disabledReason={!repEmp && !repBusy ? 'Chọn ít nhất 1 phần cần thay' : !busyWeek ? 'Chọn tuần lịch bận ở tab Lịch bận' : null}
          description={<>File cùng mẫu store đang dùng (sheet <b>Employee Master</b> + <b>Availability</b>). Nhân viên không có trong file sẽ chuyển
            <b> Ngừng làm</b> (không xóa); lịch bận tuần {busyWeek ?? '—'} được thay toàn bộ.</>}
          options={<Space style={{ marginBottom: 10 }}>
            <Checkbox checked={repEmp} disabled={!me.can.employeeEdit} onChange={(e) => setRepEmp(e.target.checked)}>Thay danh sách nhân viên</Checkbox>
            <Checkbox checked={repBusy} disabled={!me.can.availabilityEdit} onChange={(e) => setRepBusy(e.target.checked)}>Thay lịch bận tuần {busyWeek ?? ''}</Checkbox>
          </Space>} />
      </div>
      <Table size="small" rowKey="employeeId" loading={emps.isLoading} columns={cols} dataSource={data} pagination={false} />
      <Modal open={!!editing} title={editing === 'new' ? `Thêm nhân viên · store ${store}` : 'Sửa nhân viên'} onCancel={() => setEditing(null)}
        onOk={submit} okText="Lưu" confirmLoading={save.isPending} destroyOnHidden>
        <Form form={form} layout="vertical" requiredMark={false} preserve={false}>
          <Form.Item name="employeeId" label="Mã nhân viên" rules={[{ required: true, pattern: /^\d{1,15}$/, message: 'Mã nhân viên là số' }]}>
            <Input disabled={editing !== 'new'} />
          </Form.Item>
          <Form.Item name="employeeName" label="Họ tên" rules={[{ required: true, message: 'Nhập họ tên' }]}><Input /></Form.Item>
          <Space style={{ width: '100%' }} styles={{ item: { flex: 1 } }}>
            <Form.Item name="position" label="Vị trí" rules={[{ required: true }]}><Select options={opt(options?.positions)} /></Form.Item>
            <Form.Item name="employmentType" label="FT/PT" rules={[{ required: true }]}><Select options={opt(options?.employmentTypes)} /></Form.Item>
          </Space>
          <Space style={{ width: '100%' }} styles={{ item: { flex: 1 } }}>
            <Form.Item name="laborGroup" label="Nhóm" rules={[{ required: true }]}><Select options={opt(options?.laborGroups)} /></Form.Item>
            <Form.Item name="status" label="Trạng thái" rules={[{ required: true }]}>
              <Select options={[{ value: 'Active', label: 'Đang làm' }, { value: 'Inactive', label: 'Ngừng làm' }]} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </>
  )
}

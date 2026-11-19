// Employees lent to another store: add / edit / delete, or replace the store's list with an Excel file.
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import { App, Button, DatePicker, Form, Modal, Popconfirm, Select, Space, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import type { Me, Saved, SecondmentItem } from '../../api/client'
import { fileUrl, sendJson } from '../../api/client'
import { useEmployees, useInputMutation, useSecondments, useStores } from '../../api/hooks'
import { ddmmyyyy } from '../../lib/format'
import { Pill } from '../Pill'
import { ExcelImport } from './ExcelImport'

type FormVals = { employeeId: string; receivingStore: string; dates: [Dayjs, Dayjs] }

export function SecondmentsTab({ store, me }: { store: string; me: Me }) {
  const { message } = App.useApp()
  const sec = useSecondments(store)
  const emps = useEmployees(store)
  const allStores = useStores(false)
  const [editing, setEditing] = useState<SecondmentItem | 'new' | null>(null)
  const [form] = Form.useForm<FormVals>()
  const edit = me.can.employeeEdit
  const save = useInputMutation((v: FormVals) => {
    const body = { receivingStore: v.receivingStore, startDate: v.dates[0].format('YYYY-MM-DD'), endDate: v.dates[1].format('YYYY-MM-DD') }
    return editing === 'new'
      ? sendJson<Saved>('/inputs/secondments', { ...body, employeeId: v.employeeId, homeStore: store })
      : sendJson<Saved>(`/inputs/secondments/${(editing as SecondmentItem).id}`, body, 'PUT')
  })
  const del = useInputMutation((id: number) => sendJson<Saved>(`/inputs/secondments/${id}`, undefined, 'DELETE'))

  const open = (s: SecondmentItem | 'new') => {
    setEditing(s)
    form.setFieldsValue(s === 'new' ? { employeeId: undefined, receivingStore: undefined, dates: undefined } as unknown as FormVals
      : { employeeId: s.employeeId, receivingStore: s.receivingStore, dates: [dayjs(s.startDate), dayjs(s.endDate)] })
  }
  const submit = () => form.validateFields().then((v) => save.mutate(v, {
    onSuccess: (r) => { message.success(r.message); setEditing(null) }, onError: (e) => message.error((e as Error).message),
  }))

  const cols: ColumnsType<SecondmentItem> = [
    { title: 'Nhân viên', dataIndex: 'employeeName', render: (v, r) => <><b>{v}</b> <span className="card-sub">{r.employeeId} · {r.position}</span></> },
    { title: 'Store gốc', dataIndex: 'homeStore', width: 95 }, { title: 'Store nhận', dataIndex: 'receivingStore', width: 95 },
    { title: 'Từ', dataIndex: 'startDate', width: 100, render: ddmmyyyy }, { title: 'Đến', dataIndex: 'endDate', width: 100, render: ddmmyyyy },
    { title: '', dataIndex: 'homeStore', key: 'dir', width: 110,
      render: (h) => <Pill tone={h === store ? 'warn' : 'good'}>{h === store ? 'Cho mượn đi' : 'Được mượn về'}</Pill> },
    { title: 'Cập nhật', key: 'upd', width: 190, render: (_, r) => <span className="card-sub">{r.updatedBy ?? ''} {r.updatedAt ?? ''}</span> },
    ...(edit ? [{
      title: '', key: 'act', width: 120, render: (_: unknown, r: SecondmentItem) => r.homeStore !== store ? null : (
        <Space size={4}>
          <Button size="small" icon={<EditOutlined />} onClick={() => open(r)} />
          <Popconfirm title="Xóa dòng cho mượn này?" okText="Xóa" okButtonProps={{ danger: true }}
            onConfirm={() => del.mutate(r.id, { onSuccess: (x) => message.success(x.message), onError: (e) => message.error((e as Error).message) })}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>),
    }] : []),
  ]

  return (
    <>
      <div className="toolbar">
        <span className="card-sub">Store gốc: ngày đi hỗ trợ vẫn tính giờ công (07:00–15:00 · 1180), không xếp ca, không thành OFF. Store nhận: chỉ xếp ca vào ngày được mượn.</span>
        <span className="grow" />
        {edit && <Button type="primary" icon={<PlusOutlined />} onClick={() => open('new')}>Thêm cho mượn</Button>}
        <ExcelImport title={`Upload danh sách cho mượn · store ${store}`} path="/inputs/excel/secondments" fields={{ store }}
          downloadHref={fileUrl('/inputs/excel/secondments', { store })} canUpload={edit}
          description={<>Sheet <b>Cho mượn</b>: Mã NV · Họ tên · Store gốc · Store nhận · Từ ngày · Đến ngày. Upload sẽ <b>thay toàn bộ</b> danh sách
            nhân viên store {store} cho mượn.</>} />
      </div>
      <Table size="small" rowKey="id" loading={sec.isLoading} columns={cols} dataSource={sec.data} pagination={false} />
      <Modal open={!!editing} title={editing === 'new' ? `Cho mượn nhân viên store ${store}` : 'Sửa cho mượn'} onCancel={() => setEditing(null)}
        onOk={submit} okText="Lưu" confirmLoading={save.isPending} destroyOnHidden>
        <Form form={form} layout="vertical" requiredMark={false} preserve={false}>
          <Form.Item name="employeeId" label="Nhân viên" rules={[{ required: true, message: 'Chọn nhân viên' }]}>
            <Select showSearch optionFilterProp="label" disabled={editing !== 'new'}
              options={(emps.data ?? []).filter((e) => e.status === 'Active').map((e) => ({ value: e.employeeId, label: `${e.employeeName} · ${e.position}` }))} />
          </Form.Item>
          <Form.Item name="receivingStore" label="Store nhận" rules={[{ required: true, message: 'Chọn store nhận' }]}>
            <Select showSearch optionFilterProp="label" loading={allStores.isLoading}
              options={(allStores.data ?? []).filter((s) => s.storeCode !== store).map((s) => ({ value: s.storeCode, label: `${s.storeCode} · ${s.storeName}` }))} />
          </Form.Item>
          <Form.Item name="dates" label="Thời gian" rules={[{ required: true, message: 'Chọn ngày' }]}>
            <DatePicker.RangePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
          </Form.Item>
          {!me.allStores && <div className="card-sub">Danh sách store nhận chỉ gồm các store bạn được phân quyền.</div>}
        </Form>
      </Modal>
    </>
  )
}

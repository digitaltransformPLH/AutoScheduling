// Store config (TCPH target, staff minimums, opening hours): edit a row or upload an Excel file for several stores.
import { EditOutlined } from '@ant-design/icons'
import { App, Button, Form, InputNumber, Modal, Segmented, Space, Table, TimePicker } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import type { Me, Saved, StoreConfig } from '../../api/client'
import { fileUrl, sendJson } from '../../api/client'
import { useInputMutation, useStoreConfig } from '../../api/hooks'
import { fmt } from '../../lib/format'
import { ExcelImport } from './ExcelImport'

type FormVals = { hours?: [Dayjs, Dayjs]; tcphTarget: number; tcphCeilingMult: number; openStaff: number; closeStaff: number; minStaffPerSlot: number }

export function ConfigTab({ store, me }: { store: string; me: Me }) {
  const { message } = App.useApp()
  const [scope, setScope] = useState<'configured' | 'all'>('configured')
  const cfg = useStoreConfig(scope === 'all')
  const [editing, setEditing] = useState<StoreConfig | null>(null)
  const [form] = Form.useForm<FormVals>()
  // hours are sent only when changed here (they need the store-manage permission)
  const save = useInputMutation((v: FormVals & { hoursChanged: boolean }) => sendJson<Saved>(`/inputs/store-config/${editing!.storeCode}`, {
    openingTime: v.hoursChanged ? v.hours?.[0].format('HH:mm') ?? null : null,
    closingTime: v.hoursChanged ? v.hours?.[1].format('HH:mm') ?? null : null, tcphTarget: v.tcphTarget,
    tcphCeilingMult: v.tcphCeilingMult, openStaff: v.openStaff, closeStaff: v.closeStaff, minStaffPerSlot: v.minStaffPerSlot,
  }, 'PUT'))
  const t = (s?: string | null) => (s ? dayjs(`2000-01-01T${s === '24:00' ? '23:59' : s}`) : undefined)
  const open = (r: StoreConfig) => {
    setEditing(r)
    form.setFieldsValue({
      hours: r.openingTime && r.closingTime ? [t(r.openingTime)!, t(r.closingTime)!] : undefined, tcphTarget: r.tcphTarget ?? undefined,
      tcphCeilingMult: r.tcphCeilingMult ?? 1.05, openStaff: r.openStaff ?? 2, closeStaff: r.closeStaff ?? 2, minStaffPerSlot: r.minStaffPerSlot ?? 2,
    } as FormVals)
  }
  const submit = () => form.validateFields().then((v) => save.mutate({ ...v, hoursChanged: form.isFieldTouched('hours') }, {
    onSuccess: (r) => { message.success(r.message); setEditing(null) }, onError: (e) => message.error((e as Error).message),
  }))

  const cols: ColumnsType<StoreConfig> = [
    { title: 'Store', dataIndex: 'storeCode', width: 80, render: (v) => (v === store ? <b>{v}</b> : v) }, { title: 'Tên', dataIndex: 'storeName' },
    { title: 'Mở cửa', dataIndex: 'openingTime', width: 85 }, { title: 'Đóng cửa', dataIndex: 'closingTime', width: 90 },
    { title: 'TCPH target', dataIndex: 'tcphTarget', width: 105, render: (v) => <b>{fmt(v, 2)}</b> },
    { title: 'Trần (x)', dataIndex: 'tcphCeilingMult', width: 80 }, { title: 'Mở ca ≥', dataIndex: 'openStaff', width: 80 },
    { title: 'Đóng ca ≥', dataIndex: 'closeStaff', width: 90 }, { title: 'Tối thiểu/giờ', dataIndex: 'minStaffPerSlot', width: 105 },
    { title: 'Cập nhật', key: 'upd', width: 190, render: (_, r) => <span className="card-sub">{r.updatedBy ?? ''} {r.updatedAt ?? ''}</span> },
    ...(me.can.configEdit ? [{ title: '', key: 'act', width: 70,
      render: (_: unknown, r: StoreConfig) => <Button size="small" icon={<EditOutlined />} onClick={() => open(r)} /> }] : []),
  ]

  return (
    <>
      <div className="toolbar">
        <Segmented value={scope} onChange={(v) => setScope(v as typeof scope)}
          options={[{ value: 'configured', label: 'Store đã có target' }, { value: 'all', label: 'Tất cả store của tôi' }]} />
        <span className="grow" />
        <ExcelImport title="Upload cấu hình store" path="/inputs/excel/store-config" fields={{}} downloadHref={fileUrl('/inputs/excel/store-config')}
          canUpload={me.can.configEdit}
          description={<>Sheet <b>Cấu hình store</b>: chỉ các store có trong file và có TCPH target được cập nhật; store không có trong file giữ nguyên.
            {me.can.hoursEdit ? '' : ' Đổi giờ mở / đóng cửa cần quyền quản lý store.'}</>} />
      </div>
      <Table size="small" rowKey="storeCode" loading={cfg.isLoading} columns={cols} dataSource={cfg.data}
        pagination={{ pageSize: 20, hideOnSinglePage: true }} />
      <Modal open={!!editing} title={editing ? `Cấu hình store ${editing.storeCode} · ${editing.storeName}` : ''} onCancel={() => setEditing(null)}
        onOk={submit} okText="Lưu" confirmLoading={save.isPending} destroyOnHidden>
        <Form form={form} layout="vertical" requiredMark={false} preserve={false}>
          <Form.Item name="hours" label="Giờ mở – đóng cửa" extra={me.can.hoursEdit ? undefined : 'Cần quyền quản lý store để đổi giờ.'}>
            <TimePicker.RangePicker format="HH:mm" minuteStep={30} disabled={!me.can.hoursEdit} />
          </Form.Item>
          <Space wrap>
            <Form.Item name="tcphTarget" label="TCPH target" rules={[{ required: true, message: 'Nhập target' }]}>
              <InputNumber min={0.5} max={50} step={0.01} decimalSeparator="," />
            </Form.Item>
            <Form.Item name="tcphCeilingMult" label="Hệ số trần"><InputNumber min={1} max={2} step={0.01} decimalSeparator="," /></Form.Item>
          </Space>
          <Space wrap>
            <Form.Item name="openStaff" label="Số người mở ca"><InputNumber min={1} max={20} /></Form.Item>
            <Form.Item name="closeStaff" label="Số người đóng ca"><InputNumber min={1} max={20} /></Form.Item>
            <Form.Item name="minStaffPerSlot" label="Tối thiểu mỗi giờ"><InputNumber min={1} max={20} /></Form.Item>
          </Space>
        </Form>
      </Modal>
    </>
  )
}

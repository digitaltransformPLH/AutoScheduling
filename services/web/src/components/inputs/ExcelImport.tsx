// Excel round-trip: "Tải Excel" (current data) + "Upload Excel" -> preview of changes -> confirm (replace).
import { DownloadOutlined, InboxOutlined, UploadOutlined } from '@ant-design/icons'
import { Alert, App, Button, Modal, Space, Table, Upload } from 'antd'
import type { ReactNode } from 'react'
import { useState } from 'react'
import type { ImportResult } from '../../api/client'
import { sendForm } from '../../api/client'
import { useInputMutation } from '../../api/hooks'
import { Pill } from '../Pill'

const TONE: Record<string, 'good' | 'warn' | 'bad' | 'neutral'> = {
  Thêm: 'good', 'Cập nhật': 'neutral', 'Chuyển store': 'warn', 'Ngừng làm': 'bad', 'Thay lịch bận': 'neutral', Xóa: 'bad',
}

type Props = {
  title: string
  path: string                                   // POST endpoint (multipart)
  fields: Record<string, string | boolean>       // extra form fields (store, week, flags)
  downloadHref: string | null
  canUpload: boolean
  description: ReactNode
  options?: ReactNode                            // e.g. checkboxes "thay nhân viên / lịch bận"
  disabledReason?: string | null
}

export function ExcelImport({ title, path, fields, downloadHref, canUpload, description, options, disabledReason }: Props) {
  const { message } = App.useApp()
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportResult | null>(null)
  const send = (apply: boolean) => {
    const f = new FormData()
    for (const [k, v] of Object.entries(fields)) f.set(k, String(v))
    f.set('apply', String(apply))
    f.set('file', file as File)
    return sendForm<ImportResult>(path, f)
  }
  const check = useInputMutation(() => send(false))
  const apply = useInputMutation(() => send(true))
  const close = () => { setOpen(false); setFile(null); setPreview(null); check.reset(); apply.reset() }

  return (
    <>
      <Button icon={<DownloadOutlined />} href={downloadHref ?? undefined} disabled={!downloadHref}>Tải Excel</Button>
      {canUpload && <Button icon={<UploadOutlined />} onClick={() => setOpen(true)}>Upload Excel</Button>}
      <Modal open={open} title={title} width={820} onCancel={close} destroyOnHidden
        footer={<Space>
          <Button onClick={close}>Đóng</Button>
          {!preview?.applied && <Button disabled={!file || !!disabledReason} loading={check.isPending}
            onClick={() => check.mutate(undefined, { onSuccess: setPreview, onError: (e) => message.error((e as Error).message) })}>Kiểm tra file</Button>}
          {!preview?.applied && <Button type="primary" danger disabled={!preview?.canApply || check.isPending} loading={apply.isPending}
            onClick={() => apply.mutate(undefined, {
              onSuccess: (r) => { setPreview(r); message.success('Đã cập nhật dữ liệu. Bấm "Tạo lại lịch" để lịch dùng dữ liệu mới.') },
              onError: (e) => message.error((e as Error).message),
            })}>Xác nhận thay</Button>}
        </Space>}>
        <div className="sub" style={{ marginTop: 0, marginBottom: 10 }}>{description}</div>
        {options}
        <Upload.Dragger accept=".xlsx" maxCount={1} beforeUpload={(f) => { setFile(f); setPreview(null); return false }}
          onRemove={() => { setFile(null); setPreview(null) }} fileList={file ? [{ uid: '1', name: file.name, status: 'done' }] : []}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">Kéo file .xlsx vào đây hoặc bấm để chọn</p>
          <p className="ant-upload-hint">Nên bấm "Tải Excel" lấy file hiện tại, sửa trên đó rồi upload lại.</p>
        </Upload.Dragger>
        {disabledReason && <Alert type="warning" showIcon style={{ marginTop: 10 }} message={disabledReason} />}
        {preview && (
          <div style={{ marginTop: 12 }}>
            {preview.applied
              ? <Alert type="success" showIcon message="Đã ghi vào hệ thống" />
              : <Alert type={preview.canApply ? 'info' : 'error'} showIcon
                  message={preview.canApply ? 'Xem trước — chưa ghi gì. Kiểm tra rồi bấm "Xác nhận thay".' : 'File còn lỗi, sửa rồi upload lại (chưa ghi gì).'} />}
            <ul className="import-summary">{preview.summary.map((s) => <li key={s}>{s}</li>)}</ul>
            {preview.errors.length > 0 && <Alert type="error" style={{ marginBottom: 8 }} message={`${preview.errors.length} lỗi`}
              description={<ul style={{ margin: 0, paddingLeft: 18 }}>{preview.errors.map((e) => <li key={e}>{e}</li>)}</ul>} />}
            {preview.warnings.map((w) => <Alert key={w} type="warning" showIcon style={{ marginBottom: 8 }} message={w} />)}
            {preview.changes.length > 0 && (
              <Table size="small" rowKey={(r) => `${r.action}-${r.key}-${r.detail}`} pagination={{ pageSize: 8, hideOnSinglePage: true }}
                dataSource={preview.changes} columns={[
                  { title: 'Thay đổi', dataIndex: 'action', width: 130, render: (v: string) => <Pill tone={TONE[v] ?? 'neutral'}>{v}</Pill> },
                  { title: 'Mã', dataIndex: 'key', width: 120 }, { title: 'Tên', dataIndex: 'name', width: 200 },
                  { title: 'Chi tiết', dataIndex: 'detail' },
                ]} />
            )}
          </div>
        )}
      </Modal>
    </>
  )
}

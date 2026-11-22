import { Alert } from 'antd'
import { PageLoading } from '../../../shared/components/PageLoading'
import { useEffect, useState } from 'react'
import { useOverview } from '../api/hooks'
import { BottomCardsRow } from '../components/overview/BottomRow'
import { CoverageHeatmap } from '../components/overview/CoverageHeatmap'
import { DailyChart } from '../components/overview/DailyChart'
import { DayTypeSummary, KpiTiles } from '../components/overview/KpiTiles'
import { DayTabs, Timeline, timelineSubtitle } from '../components/overview/Timeline'
import { Pill } from '../components/Pill'
import { StoreWeekPicker } from '../components/StoreWeekPicker'
import { addDays, ddmm, fmt, isoWeek } from '../lib/format'
import { useUrlFilters } from '../lib/useUrlFilters'
import { assessmentTone, coverageColors, plh } from '../theme/tokens'

export function OverviewPage() {
  const [{ store, week }] = useUrlFilters()
  const ov = useOverview(store, week)
  const [day, setDay] = useState<string | null>(null)
  const data = ov.data

  // default selected day = first day with a problem
  useEffect(() => {
    if (data && (!day || !data.days.some((d) => d.workDate === day))) {
      const first = data.days.find((d) => d.missingStaffHours || d.hoursWithoutManager) ?? data.days[0]
      setDay(first?.workDate ?? null)
    }
  }, [data, day])

  const notFound = (ov.error as { status?: number } | null)?.status === 404
  const w = data?.week
  const missing = data?.days.reduce((a, d) => a + (d.missingStaffHours ?? 0), 0) ?? 0
  let title = 'Chọn cửa hàng và tuần để xem lịch gợi ý.'
  if (w) {
    if (w.status !== 'Nháp') title = `${w.storeCode} chưa xếp được lịch: ${w.errorCount} lỗi đầu vào cần xử lý.`
    else if (w.errorCount) title = `${w.storeCode} chưa duyệt được: ${w.errorCount} lỗi cần xử lý và thiếu ${fmt(missing)} giờ-người (${fmt(100 - (w.staffCoveragePct ?? 0), 1)}%).`
    else if (!w.tcphInTarget) title = `${w.storeCode} đủ quản lý nhưng TCPH tuần ${fmt(w.weeklyTcph, 2)} chưa đạt target ${fmt(w.tcphTarget, 2)}; thiếu ${fmt(missing)} giờ-người.`
    else title = `${w.storeCode} đạt TCPH ${fmt(w.weeklyTcph, 2)} (target ${fmt(w.tcphTarget, 2)}) và phủ đủ ${fmt(w.staffCoveragePct)}% giờ-người; có thể duyệt.`
  }
  const selDay = data?.days.find((d) => d.workDate === day) ?? data?.days[0]

  return (
    <main className="page">
      <div className="head">
        <div>
          <div className="kicker">Lịch gợi ý · {week ? `Tuần ${isoWeek(week)} · ${ddmm(week)} – ${ddmm(addDays(week, 6))}` : '—'}{store ? ` · Store ${store}` : ''}</div>
          <h1 className="action-title">{notFound ? `Store ${store} chưa có lịch cho tuần này — bấm "Tạo lịch".` : title}</h1>
          {w && <div className="sub">{w.storeName} · mở cửa {w.openingTime}–{w.closingTime} · {w.employeeCount} nhân viên</div>}
        </div>
        <StoreWeekPicker />
      </div>
      {w && (
        <div className="meta-row">
          <Pill>{w.status}</Pill>
          <Pill tone={assessmentTone[w.assessment ?? ''] ?? 'neutral'}>Đánh giá: {w.assessment}</Pill>
          <Pill tone={w.errorCount ? 'bad' : 'good'}>{w.errorCount} lỗi</Pill>
          <Pill tone={w.warningCount ? 'warn' : 'good'}>{w.warningCount} cảnh báo</Pill>
          {w.note && <Pill>{w.note}</Pill>}
          <span className="t">Tạo lúc {w.createdAt} · {w.createdBy}{w.runId ? ` · run #${w.runId}` : ''}</span>
        </div>
      )}
      {ov.isLoading ? (
        <PageLoading />
      ) : (
        <>
      {!!ov.error && !notFound && <Alert type="error" showIcon message="Không tải được dữ liệu" description={String((ov.error as Error).message)} />}
      {notFound && <div className="card empty">Chưa có lịch gợi ý cho store-tuần này. Bấm <b>Tạo lịch</b> để chạy engine (khoảng 5–20 giây).</div>}
      {data && w && w.status !== 'Nháp' && (
        <Alert type="error" showIcon style={{ marginBottom: 14 }} message="Không xếp được lịch"
          description={data.issues.filter((i) => i.severity === 'Lỗi').map((i) => i.message).join(' · ')} />
      )}
      {data && w && w.status === 'Nháp' && selDay && (
        <>
          <KpiTiles ov={data} />
          <section className="row mid">
            <div className="card">
              <div className="card-head"><div><div className="card-title">Ngày thường vs cuối tuần</div><div className="card-sub">Bình quân mỗi ngày</div></div></div>
              <DayTypeSummary ov={data} />
            </div>
            <div className="card">
              <div className="card-head">
                <div><div className="card-title">TC dự báo và giờ công theo ngày</div><div className="card-sub">Giờ công nằm trong vùng xanh thì TCPH đạt target</div></div>
                <div className="legend">
                  <span><i style={{ background: plh.bar }} />TC dự báo</span><span><i style={{ background: plh.green }} />Giờ công (Reg + Train)</span>
                  <span><i style={{ background: plh.tintGreen, border: '1px solid #b9cf8a' }} />Vùng target giờ công</span>
                </div>
              </div>
              <DailyChart days={data.days} />
            </div>
          </section>
          <section className="card" style={{ marginBottom: 14 }}>
            <div className="card-head">
              <div><div className="card-title">Độ phủ theo giờ</div><div className="card-sub">Mỗi ô = số người xếp / số người cần · bấm một ô để xem ai đang làm ngày đó</div></div>
              <div className="legend">{Object.entries(coverageColors).map(([k, c]) => <span key={k}><i style={{ background: c.bg, border: '1px solid #ddd' }} />{k}</span>)}</div>
            </div>
            <CoverageHeatmap days={data.days} hourly={data.hourly} selected={selDay.workDate} onSelect={setDay} />
          </section>
          <section className="card timeline-card" style={{ marginBottom: 14 }}>
            <div className="card-head">
              <div><div className="card-title">Ai làm lúc nào</div><div className="card-sub">{timelineSubtitle(selDay, data.roster)}</div></div>
              <DayTabs days={data.days} selected={selDay.workDate} onSelect={setDay} />
            </div>
            <div className="legend" style={{ marginBottom: 10 }}>
              <span><i style={{ background: plh.green }} />Quản lý</span><span><i style={{ background: plh.tintGreen, border: '1px solid #b9cf8a' }} />Barista Trainer</span>
              <span><i style={{ background: '#fff', borderLeft: `4px solid ${plh.green}`, borderTop: `1px solid ${plh.line}`, borderBottom: `1px solid ${plh.line}` }} />FT</span>
              <span><i style={{ background: '#fff', borderLeft: `4px solid ${plh.ptLine}`, borderTop: `1px solid ${plh.line}`, borderBottom: `1px solid ${plh.line}` }} />PT</span>
              <span><i style={{ background: plh.warm, border: '1px dashed #b9a99a' }} />Training / NSO</span>
              <span><i style={{ background: '#fff', outline: '2px dashed #1F4B63' }} />Mượn từ store khác</span>
              <span><i style={{ background: plh.rust, width: 2 }} />Giờ mở / đóng cửa</span>
            </div>
            <Timeline week={w} day={selDay} roster={data.roster} hourly={data.hourly} />
          </section>
          <BottomCardsRow ov={data} />
        </>
      )}
        </>
      )}
      <div className="foot"><span>{w ? `Dữ liệu tạo lúc ${w.createdAt} · ${w.status}` : ''}</span>
        <span>Nguồn: engine auto scheduling (greedy v0) · forecast tc_p50 · schema sched (DB AutoScheduling)</span></div>
    </main>
  )
}

// Bars = forecast TC per day; line = labor hours (Regular + Training); shaded band = labor hours that keep TCPH in target.
import ReactECharts from 'echarts-for-react'
import type { DaySummary } from '../../api/client'
import { ddmm, fmt } from '../../lib/format'
import { fontFamily, plh } from '../../theme/tokens'

export function DailyChart({ days }: { days: DaySummary[] }) {
  const labels = days.map((d) => `${d.weekday}\n${ddmm(d.workDate)}`)
  const labor = days.map((d) => (d.regularHours ?? 0) + (d.trainingHours ?? 0))
  const option = {
    textStyle: { fontFamily },
    grid: { left: 48, right: 52, top: 24, bottom: 44 },
    tooltip: {
      trigger: 'axis',
      formatter: (ps: { dataIndex: number }[]) => {
        const d = days[ps[0].dataIndex]
        return [
          `<b>${d.weekday} ${ddmm(d.workDate)}</b>`,
          `TC dự báo: ${fmt(d.forecastTc)}`,
          `Giờ công: ${fmt(labor[ps[0].dataIndex], 1)}h (target ${fmt(d.targetHoursMin, 1)}–${fmt(d.targetHoursMax, 1)}h)`,
          `TCPH ${fmt(d.tcph, 2)} ${d.tcphInTarget ? '✓ trong target' : '✗ ngoài target'}`,
        ].join('<br/>')
      },
    },
    xAxis: { type: 'category', data: labels, axisTick: { show: false }, axisLabel: { color: plh.text, fontWeight: 600 } },
    yAxis: [
      { type: 'value', name: 'TC (bill)', nameTextStyle: { color: plh.muted }, splitLine: { lineStyle: { color: plh.warm } } },
      { type: 'value', name: 'Giờ công', nameTextStyle: { color: plh.muted }, splitLine: { show: false } },
    ],
    series: [
      { name: 'TC dự báo', type: 'bar', data: days.map((d) => d.forecastTc), itemStyle: { color: plh.bar, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 46 },
      // band: invisible base at target min + stacked (max - min) shaded area
      { name: 'band-base', type: 'line', yAxisIndex: 1, stack: 'band', data: days.map((d) => d.targetHoursMin), lineStyle: { opacity: 0 },
        symbol: 'none', tooltip: { show: false } },
      { name: 'Vùng target', type: 'line', yAxisIndex: 1, stack: 'band', data: days.map((d) => (d.targetHoursMax ?? 0) - (d.targetHoursMin ?? 0)),
        lineStyle: { opacity: 0 }, symbol: 'none', areaStyle: { color: plh.tintGreen, opacity: 0.95 }, tooltip: { show: false } },
      { name: 'Giờ công', type: 'line', yAxisIndex: 1, data: labor.map((v, i) => ({ value: v,
          itemStyle: { color: days[i].tcphInTarget ? plh.green : plh.rust } })),
        lineStyle: { color: plh.green, width: 2.5 }, symbolSize: 8, z: 5 },
    ],
  }
  return <ReactECharts option={option} style={{ height: 290 }} notMerge lazyUpdate />
}

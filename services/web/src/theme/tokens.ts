// Single source of truth for colours / font (deck template: cream, brand green, dark green, rust for warnings only).
import type { ThemeConfig } from 'antd'

export const plh = {
  cream: '#FDF8E1',
  green: '#035F1D',
  dkgreen: '#1C4220',
  text: '#1C2A1E',
  muted: '#5D6B5F',
  line: '#E4DACE',
  tintGreen: '#EAF1D4',
  tintPink: '#F8E7DF',
  warm: '#F2EBE7',
  rust: '#9A3F22',
  lime: '#D9E69A',
  onDark: '#E9EFD0',
  bar: '#C9DDB0',
  barPeak: '#8DB36A',
  ptLine: '#9DB97A',
  over: '#DDE9F0',
  overText: '#1F4B63',
  amberBg: '#FFF3D6',
  amberText: '#7A5306',
} as const

export const fontFamily = 'Manrope, "Segoe UI", Arial, sans-serif'
export const titleFont = '"Phuc Long Heritage", Manrope, "Segoe UI", Arial, sans-serif'

// hourly coverage status (values come from the DB in Vietnamese)
export const coverageColors: Record<string, { bg: string; fg: string }> = {
  'Đủ người': { bg: plh.tintGreen, fg: plh.green },
  'Dư người': { bg: plh.over, fg: plh.overText },
  'Thiếu người': { bg: plh.tintPink, fg: plh.rust },
  'Thiếu quản lý': { bg: plh.rust, fg: '#fff' },
}

export const assessmentTone: Record<string, 'good' | 'warn' | 'bad'> = { Tốt: 'good', 'Cần chú ý': 'warn', 'Rủi ro cao': 'bad' }
export const severityTone: Record<string, 'bad' | 'warn' | 'good'> = { Lỗi: 'bad', 'Cảnh báo': 'warn', 'Gợi ý': 'good' }

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: plh.green,
    colorText: plh.text,
    colorTextSecondary: plh.muted,
    colorBorder: plh.line,
    colorBorderSecondary: plh.line,
    colorBgLayout: plh.cream,
    colorError: plh.rust,
    colorSuccess: plh.green,
    fontFamily,
    borderRadius: 8,
    fontSize: 13,
  },
  components: {
    Layout: { headerBg: plh.dkgreen, bodyBg: plh.cream, headerHeight: 56, headerPadding: '0 24px' },
    Table: { headerBg: plh.dkgreen, headerColor: plh.cream, headerSortActiveBg: plh.green, headerSortHoverBg: plh.green,
             rowHoverBg: plh.warm, borderColor: plh.line, cellPaddingBlockSM: 6 },
    Card: { headerFontSize: 13 },
    Segmented: { itemSelectedBg: plh.dkgreen, itemSelectedColor: plh.cream },
    Tabs: { itemSelectedColor: plh.green, inkBarColor: plh.green },
    Menu: { darkItemBg: plh.dkgreen, darkItemSelectedBg: plh.green, darkItemColor: plh.onDark, darkItemSelectedColor: plh.cream },
  },
}

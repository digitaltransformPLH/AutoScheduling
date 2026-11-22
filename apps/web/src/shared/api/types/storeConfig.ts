export type StoreConfigListItemDto = {
  storeId: number
  storeCode: string
  storeName: string
  isConfigured: boolean
  tcphTarget: number | null
  tcphCeilingMult: number | null
  openStaff: number | null
  closeStaff: number | null
  minStaffPerSlot: number | null
  updatedAt: string | null
  updatedBy: string | null
}

export type StoreConfigDetailDto = {
  storeId: number
  storeCode: string
  storeName: string
  isConfigured: boolean
  tcphTarget: number
  tcphCeilingMult: number
  openStaff: number
  closeStaff: number
  minStaffPerSlot: number
  updatedAt: string | null
  updatedBy: string | null
}

export type UpsertStoreConfigRequest = {
  tcphTarget: number
  tcphCeilingMult: number
  openStaff: number
  closeStaff: number
  minStaffPerSlot: number
}

export const StoreConfigDefaults = {
  tcphCeilingMult: 1.05,
  openStaff: 2,
  closeStaff: 2,
  minStaffPerSlot: 2,
} as const

export type StoreConfigImportResultDto = {
  created: number
  updated: number
  failed: number
  errors: { row: number; plantCode?: string | null; message: string }[]
}
import type { ReactNode } from 'react'

export function Pill({ tone = 'neutral', children }: { tone?: 'good' | 'warn' | 'bad' | 'neutral'; children: ReactNode }) {
  return <span className={`pill ${tone}`}>{children}</span>
}

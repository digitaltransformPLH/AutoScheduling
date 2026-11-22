type PageLoadingProps = {
  label?: string
  compact?: boolean
}

export function PageLoading({ label = 'Đang tải…', compact = false }: PageLoadingProps) {
  return (
    <div
      className={`page-loading${compact ? ' page-loading--compact' : ''}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <span className="page-loading__spinner" aria-hidden />
      <span className="page-loading__label">{label}</span>
    </div>
  )
}
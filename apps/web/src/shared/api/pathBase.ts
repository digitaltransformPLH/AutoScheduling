/** IIS virtual-directory prefix injected by the API into index.html. Empty at site root. */
export function getPathBase(): string {
  if (typeof window === 'undefined') return ''
  const pb = (window as Window & { __PL_PATH_BASE__?: string }).__PL_PATH_BASE__
  if (!pb || pb === '/') return ''
  const trimmed = pb.replace(/\/$/, '')
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`
}

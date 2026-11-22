import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../../../shared/api/http'
import type {
  Envelope,
  ForecastWeek,
  Meta,
  Overview,
  Run,
  RunRequest,
  ScheduleWeek,
  StoreItem,
} from './client'
import { getJson, sendJson } from './client'

export function useMeta() {
  return useQuery({
    queryKey: ['sched', 'meta'],
    queryFn: () => getJson<Meta>('/meta'),
    staleTime: 30_000,
    refetchInterval: 30_000,
  })
}

const useDataVersion = () => useMeta().data?.dataVersion ?? 0

export function useStores(readyOnly = false) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['sched', 'stores', { readyOnly }, v],
    queryFn: () => getJson<Envelope<StoreItem[]>>('/stores', { ready_only: readyOnly }),
    select: (r) => r.data,
  })
}

export function useForecastWeeks() {
  return useQuery({
    queryKey: ['sched', 'forecast-weeks'],
    queryFn: () => getJson<Envelope<ForecastWeek[]>>('/forecast-weeks'),
    select: (r) => r.data,
  })
}

export function useSchedules(store: string | null) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['sched', 'schedules', { store }, v],
    queryFn: () => getJson<Envelope<ScheduleWeek[]>>('/schedules', { store }),
    select: (r) => r.data,
    placeholderData: keepPreviousData,
  })
}

export function useOverview(store: string | null, week: string | null) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['sched', 'overview', { store, week }, v],
    queryFn: () => getJson<Envelope<Overview>>(`/schedules/${store}/${week}/overview`),
    select: (r) => r.data,
    enabled: !!store && !!week,
    placeholderData: keepPreviousData,
    retry: (n, e: unknown) => !(e instanceof ApiError && e.status === 404) && n < 1,
  })
}

export function useRuns(store: string | null, poll = false) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['sched', 'runs', { store }, v],
    queryFn: () => getJson<Envelope<Run[]>>('/runs', { store, limit: 50 }),
    select: (r) => r.data,
    refetchInterval: poll ? 2_000 : false,
  })
}

export function useStartRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: RunRequest) => sendJson<Envelope<Run>>('/runs', req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sched', 'runs'] }),
  })
}
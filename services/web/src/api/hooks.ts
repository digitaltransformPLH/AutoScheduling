// TanStack Query hooks. Every key carries data_version: when the engine writes a new roster the
// /meta poll returns a higher version and all views refetch.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type {
  AvailabilityItem, EmployeeItem, Envelope, ForecastWeek, InputOptions, LoginRequest, Me, Meta, Overview, Run, RunRequest, ScheduleWeek,
  SecondmentItem, StoreConfig, StoreItem,
} from './client'
import { getJson, sendJson } from './client'

// ---------------------------------------------------------------- auth (accounts of the .NET app)
export function useMe() {
  return useQuery({ queryKey: ['auth', 'me'], queryFn: () => getJson<Me>('/auth/me'), retry: false, staleTime: 5 * 60_000 })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: LoginRequest) => sendJson<Me>('/auth/login', req),
    onSuccess: (me) => { qc.removeQueries({ queryKey: ['sched'] }); qc.setQueryData(['auth', 'me'], me) },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  // Log out locally first (App shows the login screen as soon as 'me' is null), then clear the cookie on the server.
  // Do NOT qc.clear(): it would drop the 'me' query the App is observing, so the screen would not change.
  return useMutation({
    mutationFn: () => sendJson<void>('/auth/logout', {}),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ['sched'] })
      qc.setQueryData(['auth', 'me'], null)
    },
    // drop cached data only after the pages have unmounted (removing earlier makes mounted queries refetch -> 401s)
    onSettled: () => qc.removeQueries({ queryKey: ['sched'] }),
  })
}

/** Any write to the inputs: refresh every platform query afterwards (data_version also moves). */
export function useInputMutation<V, R = unknown>(fn: (vars: V) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ['sched'] }) })
}

export function useMeta() {
  return useQuery({ queryKey: ['sched', 'meta'], queryFn: () => getJson<Meta>('/meta'), staleTime: 30_000, refetchInterval: 30_000 })
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
  return useQuery({ queryKey: ['sched', 'forecast-weeks'], queryFn: () => getJson<Envelope<ForecastWeek[]>>('/forecast-weeks'), select: (r) => r.data })
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
    retry: (n, e: unknown) => (e as { status?: number })?.status !== 404 && n < 1,
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

export function useStoreConfig(allStores = false) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['sched', 'store-config', { allStores }, v],
    queryFn: () => getJson<Envelope<StoreConfig[]>>('/inputs/store-config', { all_stores: allStores }),
    select: (r) => r.data,
  })
}

export function useInputOptions(store: string | null) {
  const v = useDataVersion()
  return useQuery({ queryKey: ['sched', 'input-options', { store }, v], queryFn: () => getJson<InputOptions>('/inputs/options', { store }) })
}

export function useEmployees(store: string | null) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['sched', 'employees', { store }, v],
    queryFn: () => getJson<Envelope<EmployeeItem[]>>('/inputs/employees', { store }),
    select: (r) => r.data, enabled: !!store,
  })
}

export function useAvailability(store: string | null, week: string | null) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['sched', 'availability', { store, week }, v],
    queryFn: () => getJson<Envelope<AvailabilityItem[]>>('/inputs/availability', { store, week }),
    select: (r) => r.data, enabled: !!store && !!week, placeholderData: keepPreviousData,
  })
}

export function useSecondments(store: string | null) {
  const v = useDataVersion()
  return useQuery({
    queryKey: ['sched', 'secondments', { store }, v],
    queryFn: () => getJson<Envelope<SecondmentItem[]>>('/inputs/secondments', { store }),
    select: (r) => r.data,
  })
}

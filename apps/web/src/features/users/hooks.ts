import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as usersApi from './api'
import type { UpsertUserRequest } from '../../shared/api/types'

export function useUsers() {
  return useQuery({ queryKey: ['users'], queryFn: usersApi.listUsers })
}

export function useUserMutations() {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['users'] })

  const save = useMutation({
    mutationFn: async ({
      id,
      body,
    }: {
      id: number | null
      body: UpsertUserRequest
    }) => {
      if (id) return usersApi.updateUser(id, body)
      return usersApi.createUser(body)
    },
    onSuccess: () => void invalidate(),
  })

  const deactivate = useMutation({
    mutationFn: (id: number) => usersApi.deactivateUser(id),
    onSuccess: () => void invalidate(),
  })

  return { save, deactivate }
}

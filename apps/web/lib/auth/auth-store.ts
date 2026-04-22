import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import type { paths } from "@ims/api-types"

type UserPublic = paths["/api/auth/me"]["get"]["responses"]["200"]["content"]["application/json"]

interface AuthState {
  accessToken: string | null
  user: UserPublic | null
  setAuth: (token: string, user: UserPublic) => void
  setAccessToken: (token: string | null) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      setAuth: (accessToken, user) => set({ accessToken, user }),
      setAccessToken: (accessToken) => set({ accessToken }),
      clear: () => set({ accessToken: null, user: null }),
    }),
    {
      name: "ims-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ accessToken: state.accessToken, user: state.user }),
    },
  ),
)

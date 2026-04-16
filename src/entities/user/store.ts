import { create } from "zustand";
import { persist } from "zustand/middleware";

import { SessionState, SessionUser } from "@/shared/types/domain";

type SessionStore = SessionState & {
  hasHydrated: boolean;
  setSession: (payload: {
    accessToken: string;
    refreshToken: string;
    user: SessionUser;
  }) => void;
  clearSession: () => void;
  setHydrated: (hasHydrated: boolean) => void;
};

const initialSessionState: SessionState = {
  accessToken: null,
  refreshToken: null,
  user: null,
};

export const useSessionStore = create<SessionStore>()(
  persist(
    (set) => ({
      ...initialSessionState,
      hasHydrated: false,
      setSession: ({ accessToken, refreshToken, user }) =>
        set({
          accessToken,
          refreshToken,
          user,
        }),
      clearSession: () =>
        set({
          ...initialSessionState,
        }),
      setHydrated: (hasHydrated) => set({ hasHydrated }),
    }),
    {
      name: "quantflow-session",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated(true);
      },
    },
  ),
);

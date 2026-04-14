import { create } from "zustand";

import { mockSession } from "@/shared/mocks/data";
import { SessionState, SessionUser } from "@/shared/types/domain";

type SessionStore = SessionState & {
  setSession: (payload: {
    accessToken: string;
    refreshToken: string;
    user: SessionUser;
  }) => void;
  clearSession: () => void;
};

export const useSessionStore = create<SessionStore>((set) => ({
  ...mockSession,
  setSession: ({ accessToken, refreshToken, user }) =>
    set({
      accessToken,
      refreshToken,
      user,
    }),
  clearSession: () =>
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
    }),
}));

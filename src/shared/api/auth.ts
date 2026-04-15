import axios, { AxiosResponse } from "axios";

import { env } from "@/shared/config/env";
import { useSessionStore } from "@/entities/user/store";
import { ApiEnvelope, SessionState, SessionUser, UserRole } from "@/shared/types/domain";

type AuthApiUser = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
};

type LoginInput = {
  email: string;
  password: string;
};

type AuthTokenPayload = {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  user?: AuthApiUser;
};

type MePayload = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
};

const authHttpClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 10_000,
});

let refreshPromise: Promise<SessionState> | null = null;
let bootstrapPromise: Promise<SessionState | null> | null = null;

function mapUser(apiUser: AuthApiUser | MePayload): SessionUser {
  return {
    id: apiUser.id,
    email: apiUser.email,
    fullName: apiUser.full_name,
    role: apiUser.role,
  };
}

function unwrap<T>(response: AxiosResponse<ApiEnvelope<T>>): T {
  return response.data.data;
}

function persistSession(session: SessionState) {
  useSessionStore.getState().setSession(session);
}

export async function login(input: LoginInput): Promise<SessionState> {
  const response = await authHttpClient.post<ApiEnvelope<AuthTokenPayload>>("/auth/login", input);
  const payload = unwrap(response);

  const session: SessionState = {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token ?? null,
    user: payload.user ? mapUser(payload.user) : null,
  };

  if (!session.user) {
    throw new Error("登录成功，但未返回用户信息。");
  }

  persistSession(session);
  return session;
}

export async function fetchCurrentUser(): Promise<SessionUser> {
  const accessToken = useSessionStore.getState().accessToken;
  const response = await authHttpClient.get<ApiEnvelope<MePayload>>("/auth/me", {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  return mapUser(unwrap(response));
}

export async function refreshSession(): Promise<SessionState> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const currentSession = useSessionStore.getState();
    if (!currentSession.refreshToken) {
      throw new Error("会话已过期，请重新登录。");
    }

    const response = await authHttpClient.post<ApiEnvelope<AuthTokenPayload>>("/auth/refresh", {
      refresh_token: currentSession.refreshToken,
    });
    const payload = unwrap(response);

    const nextSession: SessionState = {
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token ?? currentSession.refreshToken,
      user: payload.user ? mapUser(payload.user) : currentSession.user,
    };

    persistSession(nextSession);
    return nextSession;
  })();

  try {
    return await refreshPromise;
  } catch (error) {
    useSessionStore.getState().clearSession();
    throw error;
  } finally {
    refreshPromise = null;
  }
}

export async function bootstrapSession(): Promise<SessionState | null> {
  if (bootstrapPromise) {
    return bootstrapPromise;
  }

  bootstrapPromise = (async () => {
    const currentSession = useSessionStore.getState();

    if (!currentSession.accessToken && !currentSession.refreshToken) {
      useSessionStore.getState().clearSession();
      return null;
    }

    try {
      const user = await fetchCurrentUser();
      const latestSession = useSessionStore.getState();
      const hydratedSession: SessionState = {
        accessToken: latestSession.accessToken,
        refreshToken: latestSession.refreshToken,
        user,
      };

      persistSession(hydratedSession);
      return hydratedSession;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        try {
          const refreshedSession = await refreshSession();
          const user = await fetchCurrentUser();
          const hydratedSession: SessionState = {
            accessToken: refreshedSession.accessToken,
            refreshToken: refreshedSession.refreshToken,
            user,
          };

          persistSession(hydratedSession);
          return hydratedSession;
        } catch {
          useSessionStore.getState().clearSession();
          return null;
        }
      }

      useSessionStore.getState().clearSession();
      return null;
    }
  })();

  try {
    return await bootstrapPromise;
  } finally {
    bootstrapPromise = null;
  }
}

export async function logout(): Promise<void> {
  const currentSession = useSessionStore.getState();

  try {
    if (currentSession.refreshToken) {
      await authHttpClient.post<ApiEnvelope<null>>(
        "/auth/logout",
        {
          refresh_token: currentSession.refreshToken,
        },
        {
          headers: currentSession.accessToken ? { Authorization: `Bearer ${currentSession.accessToken}` } : undefined,
        },
      );
    }
  } finally {
    useSessionStore.getState().clearSession();
  }
}

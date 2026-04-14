import { httpClient } from "@/shared/api/http";
import { env } from "@/shared/config/env";
import { mockSession } from "@/shared/mocks/data";
import { ApiEnvelope, SessionState, UserRole } from "@/shared/types/domain";

type LoginInput = {
  email: string;
  password: string;
};

type LoginApiData = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    role: UserRole;
  };
};

export async function login(input: LoginInput): Promise<SessionState> {
  if (env.dataSource === "mock") {
    if (input.password !== "quantflow-demo") {
      throw new Error("演示环境密码固定为 quantflow-demo。");
    }
    return mockSession;
  }

  const response = await httpClient.post<ApiEnvelope<LoginApiData>>("/auth/login", input);
  return {
    accessToken: response.data.data.access_token,
    refreshToken: response.data.data.refresh_token,
    user: {
      id: response.data.data.user.id,
      email: response.data.data.user.email,
      fullName: response.data.data.user.full_name,
      role: response.data.data.user.role,
    },
  };
}

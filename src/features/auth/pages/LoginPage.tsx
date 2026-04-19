import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { ArrowRight, Eye, EyeOff, KeyRound, Mail, Radar } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { login } from "@/features/auth/api/login";
import { env } from "@/shared/config/env";
import type { ApiEnvelope } from "@/shared/types/domain";

const loginSchema = z.object({
  email: z.string().email("请输入合法邮箱"),
  password: z.string().min(6, "密码至少 6 位"),
});

type LoginValues = z.infer<typeof loginSchema>;

const demoAccounts: Array<{
  label: string;
  role: string;
  values: LoginValues;
}> = [
  {
    label: "管理员账号",
    role: "ADMIN",
    values: {
      email: "alex@quantflow.local",
      password: "quantflow-demo",
    },
  },
  {
    label: "交易员账号",
    role: "TRADER",
    values: {
      email: "trader@quantflow.local",
      password: "quantflow-demo",
    },
  },
];

const loginPoints = [
  "登录后直接进入交易工作台",
  "当前浏览器会自动恢复最近会话",
  env.dataSource === "api" ? "当前使用后端认证服务" : "当前使用本地演示模式",
];

export function LoginPage() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const {
    register,
    reset,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: demoAccounts[0].values,
  });

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate("/dashboard", { replace: true });
    },
  });

  const emailField = register("email");
  const passwordField = register("password");
  const authModeLabel = env.dataSource === "api" ? "API Mode" : "Mock Mode";
  const loginErrorMessage = mutation.error ? getLoginErrorMessage(mutation.error) : null;

  function resetMutationError() {
    if (mutation.isError) {
      mutation.reset();
    }
  }

  function applyDemoAccount(values: LoginValues) {
    resetMutationError();
    reset(values, {
      keepDirty: false,
      keepTouched: false,
      keepErrors: false,
    });
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.12),transparent_28%),linear-gradient(180deg,#050816,#0b1023)] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center">
        <div className="grid w-full overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950/75 shadow-[0_40px_120px_-70px_rgba(15,23,42,1)] backdrop-blur xl:grid-cols-[0.9fr_1.1fr]">
          <section className="border-b border-white/10 p-8 sm:p-10 xl:border-b-0 xl:border-r">
            <div className="flex h-full flex-col justify-between gap-10">
              <div>
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-[1.2rem] bg-cyan-400/10 text-cyan-200">
                    <Radar className="h-7 w-7" />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/70">QuantFlow Pro</p>
                    <p className="mt-1 text-sm text-slate-400">Trading workspace access</p>
                  </div>
                </div>

                <div className="mt-10">
                  <div className="inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-200">
                    {authModeLabel}
                  </div>
                  <h1 className="mt-5 text-3xl font-semibold leading-tight text-white sm:text-4xl">
                    简单直接地进入 QuantFlow Pro
                  </h1>
                  <p className="mt-4 text-base leading-8 text-slate-300">
                    这是系统登录入口，不再堆叠多余信息。选择演示账号或直接输入账号密码，登录后会进入主工作台。
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                {loginPoints.map((item) => (
                  <div key={item} className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm text-slate-300">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="p-8 sm:p-10">
            <div className="mx-auto max-w-md">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Sign In</p>
                  <h2 className="mt-3 text-3xl font-semibold text-white">登录账号</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    默认演示密码为 <span className="font-mono text-cyan-200">quantflow-demo</span>。
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-slate-400">
                  会话自动恢复
                </div>
              </div>

              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                {demoAccounts.map((account) => (
                  <button
                    key={account.role}
                    type="button"
                    onClick={() => applyDemoAccount(account.values)}
                    disabled={mutation.isPending}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4 text-left transition hover:border-cyan-400/40 hover:bg-cyan-400/[0.06] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{account.role}</p>
                    <p className="mt-2 text-sm font-semibold text-white">{account.label}</p>
                    <p className="mt-2 font-mono text-xs text-cyan-200">{account.values.email}</p>
                  </button>
                ))}
              </div>

              <form noValidate className="mt-8 space-y-5" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
                <div>
                  <label htmlFor="login-email" className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-500">
                    邮箱
                  </label>
                  <div
                    className={[
                      "flex items-center gap-3 rounded-2xl border bg-slate-950/80 px-4 py-3.5 transition",
                      errors.email ? "border-rose-400/60" : "border-slate-800 focus-within:border-cyan-400/80",
                    ].join(" ")}
                  >
                    <Mail className="h-4 w-4 shrink-0 text-slate-500" />
                    <input
                      {...emailField}
                      id="login-email"
                      type="email"
                      inputMode="email"
                      autoComplete="username"
                      disabled={mutation.isPending}
                      placeholder="name@quantflow.local"
                      className="w-full border-none bg-transparent text-sm text-white outline-none placeholder:text-slate-600"
                      onChange={(event) => {
                        resetMutationError();
                        emailField.onChange(event);
                      }}
                    />
                  </div>
                  {errors.email ? <p className="mt-2 text-xs text-rose-300">{errors.email.message}</p> : null}
                </div>

                <div>
                  <label htmlFor="login-password" className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-500">
                    密码
                  </label>
                  <div
                    className={[
                      "flex items-center gap-3 rounded-2xl border bg-slate-950/80 px-4 py-3.5 transition",
                      errors.password ? "border-rose-400/60" : "border-slate-800 focus-within:border-cyan-400/80",
                    ].join(" ")}
                  >
                    <KeyRound className="h-4 w-4 shrink-0 text-slate-500" />
                    <input
                      {...passwordField}
                      id="login-password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      disabled={mutation.isPending}
                      placeholder="请输入登录密码"
                      className="w-full border-none bg-transparent text-sm text-white outline-none placeholder:text-slate-600"
                      onChange={(event) => {
                        resetMutationError();
                        passwordField.onChange(event);
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((current) => !current)}
                      disabled={mutation.isPending}
                      className="rounded-full p-1 text-slate-500 transition hover:text-white disabled:cursor-not-allowed"
                      aria-label={showPassword ? "隐藏密码" : "显示密码"}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.password ? <p className="mt-2 text-xs text-rose-300">{errors.password.message}</p> : null}
                </div>

                {loginErrorMessage ? (
                  <div className="rounded-2xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm leading-6 text-rose-100">
                    {loginErrorMessage}
                  </div>
                ) : null}

                <button
                  type="submit"
                  disabled={mutation.isPending}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-5 py-3.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <span>{mutation.isPending ? "登录中..." : "进入系统"}</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </form>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function getLoginErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const envelope = error.response?.data as ApiEnvelope<unknown> | undefined;
    const errorCode = envelope?.error?.code;
    const errorMessage = envelope?.error?.message;

    if (errorCode === "AUTH_INVALID_CREDENTIALS") {
      return "邮箱或密码不正确，请检查后重试。";
    }

    if (error.response?.status === 401) {
      return errorMessage ?? "当前账号未通过认证，请确认账号状态或密码是否正确。";
    }

    if (error.response && error.response.status >= 500) {
      return "认证服务暂时不可用，请稍后再试。";
    }

    return errorMessage ?? error.message ?? "登录失败，请稍后重试。";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "登录失败，请稍后重试。";
}

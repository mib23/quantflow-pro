import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { useSessionStore } from "@/entities/user/store";
import { login } from "@/features/auth/api/login";

const loginSchema = z.object({
  email: z.string().email("请输入合法邮箱"),
  password: z.string().min(6, "密码至少 6 位"),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useSessionStore((state) => state.setSession);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "alex@quantflow.local",
      password: "quantflow-demo",
    },
  });

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: (session) => {
      if (!session.user || !session.accessToken || !session.refreshToken) {
        return;
      }
      setSession({
        accessToken: session.accessToken,
        refreshToken: session.refreshToken,
        user: session.user,
      });
      navigate("/dashboard");
    },
  });

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.2fr_0.8fr]">
      <section className="hidden bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.24),transparent_30%),linear-gradient(145deg,#060816,#0f172a_55%,#04111b)] px-12 py-16 lg:flex lg:flex-col lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-cyan-300/80">QuantFlow Pro</p>
          <h1 className="mt-6 max-w-2xl text-5xl font-semibold leading-tight text-white">
            为单账户美股交易闭环准备的全栈量化工作台
          </h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-slate-300">
            Phase 0 已完成路由化前端骨架、FastAPI 后端基座、ER 图与契约文档，当前登录页直接对接同仓 mock/API 双通道。
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {[
            ["Broker", "Alpaca Paper"],
            ["Market", "US Equities"],
            ["Infra", "FastAPI + PostgreSQL + Redis"],
          ].map(([label, value]) => (
            <div key={label} className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{label}</p>
              <p className="mt-3 text-lg font-semibold text-white">{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="flex items-center justify-center px-6 py-10 lg:px-10">
        <div className="w-full max-w-md rounded-[2rem] border border-slate-800 bg-slate-950/80 p-8 shadow-[0_30px_120px_-60px_rgba(34,211,238,0.6)]">
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-300/70">Phase 0 Access</p>
          <h2 className="mt-4 text-3xl font-semibold text-white">登录 QuantFlow Pro</h2>
          <p className="mt-3 text-sm leading-6 text-slate-400">默认演示密码：`quantflow-demo`。切换到 `api` 模式后将调用 FastAPI 登录接口。</p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
            <div>
              <label className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-500">Email</label>
              <input
                {...register("email")}
                className="w-full rounded-2xl border border-slate-700 bg-ink-950 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
              />
              {errors.email ? <p className="mt-2 text-xs text-rose-400">{errors.email.message}</p> : null}
            </div>

            <div>
              <label className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-500">Password</label>
              <input
                {...register("password")}
                type="password"
                className="w-full rounded-2xl border border-slate-700 bg-ink-950 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
              />
              {errors.password ? <p className="mt-2 text-xs text-rose-400">{errors.password.message}</p> : null}
            </div>

            <button
              type="submit"
              disabled={mutation.isPending}
              className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span>{mutation.isPending ? "登录中..." : "进入系统"}</span>
              <ArrowRight className="h-4 w-4" />
            </button>

            {mutation.error ? <p className="text-xs text-rose-400">{mutation.error.message}</p> : null}
          </form>
        </div>
      </section>
    </div>
  );
}

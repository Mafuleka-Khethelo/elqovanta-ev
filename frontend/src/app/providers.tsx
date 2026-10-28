import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { BrowserRouter, useNavigate } from "react-router-dom";
import { ApiError, api, ensureCsrf, onAuthFailure } from "../lib/api";
import type { User } from "../lib/types";

type AuthState = {
  user: User | null;
  loading: boolean;
  offline: boolean;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);
const ToastContext = createContext<(message: string) => void>(() => undefined);

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("Auth is only available inside the app providers.");
  return value;
}

export function useToast() {
  return useContext(ToastContext);
}

function AuthBridge({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const me = useQuery({
    queryKey: ["me"],
    retry: false,
    queryFn: async () => {
      try {
        await ensureCsrf();
        return await api<{ user: User }>("/auth/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return { user: null };
        if (error instanceof ApiError && (error.status === 0 || error.code === "api_unavailable")) {
          return { user: null, offline: true };
        }
        throw error;
      }
    },
  });

  useEffect(() => {
    onAuthFailure((code) => {
      queryClient.setQueryData(["me"], { user: null });
      if (code === "session_expired" || code === "session_revoked") navigate("/session-expired");
      else navigate("/sign-in");
    });
  }, [navigate, queryClient]);

  const value = useMemo<AuthState>(
    () => ({
      user: me.data && "user" in me.data ? me.data.user : null,
      loading: me.isLoading,
      offline: Boolean(me.data && "offline" in me.data && me.data.offline) || (me.isError && !me.data),
      refresh: async () => {
        await me.refetch();
      },
    }),
    [me],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { refetchOnWindowFocus: false, retry: 1 },
        },
      }),
  );
  const [toasts, setToasts] = useState<{ id: number; message: string }[]>([]);

  function push(message: string) {
    const id = Date.now();
    setToasts((current) => [...current, { id, message }]);
    window.setTimeout(() => setToasts((current) => current.filter((item) => item.id !== id)), 4000);
  }

  return (
    <QueryClientProvider client={client}>
      <ToastContext.Provider value={push}>
        <BrowserRouter>
          <AuthBridge>{children}</AuthBridge>
          <div className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-80 flex-col gap-2" aria-live="polite">
            {toasts.map((toast) => (
              <p key={toast.id} className="pointer-events-auto rounded-xl bg-navy px-4 py-3 text-sm text-white shadow-lg">
                {toast.message}
              </p>
            ))}
          </div>
        </BrowserRouter>
      </ToastContext.Provider>
    </QueryClientProvider>
  );
}

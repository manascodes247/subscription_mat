import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "@/api/services";
import { TOKEN_KEY } from "@/api/client";
import type { User } from "@/api/types";
import { AuthStateContext } from "./useAuth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(logout)
      .finally(() => setLoading(false));
  }, [logout]);
  useEffect(() => {
    window.addEventListener("brightloop:unauthorized", logout);
    return () => window.removeEventListener("brightloop:unauthorized", logout);
  }, [logout]);
  const login = useCallback(async (email: string, password: string) => {
    const token = await authApi.login(email, password);
    localStorage.setItem(TOKEN_KEY, token.access_token);
    const profile = await authApi.me();
    setUser(profile);
    return profile;
  }, []);
  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout],
  );
  return (
    <AuthStateContext.Provider value={value}>
      {children}
    </AuthStateContext.Provider>
  );
}

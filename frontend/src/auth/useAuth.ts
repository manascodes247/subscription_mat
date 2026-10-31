import { createContext, useContext } from "react";
import type { User } from "@/api/types";

export interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
}

export const AuthStateContext = createContext<AuthState | null>(null);

export function useAuth() {
  const context = useContext(AuthStateContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

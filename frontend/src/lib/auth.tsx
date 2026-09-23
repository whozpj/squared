import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken, type ProfileUpdate, type User } from "./api";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, name: string) => Promise<void>;
  updateProfile: (payload: ProfileUpdate) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, name: string) => {
    const { access_token } = await api.devLogin(email, name);
    setToken(access_token);
    setUser(await api.me());
  };

  const updateProfile = async (payload: ProfileUpdate) => {
    setUser(await api.updateProfile(payload));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return (
    <Ctx.Provider value={{ user, loading, login, updateProfile, logout }}>{children}</Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);

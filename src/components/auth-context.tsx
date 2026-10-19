import React, { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  clearToken,
  fetchCurrentUser,
  getToken,
  loginUser,
  signupUser,
  updateCurrentUserProfile,
  type LoginPayload,
  type SignupPayload,
  type UpdateProfilePayload,
  type UserProfile,
} from "@/lib/api/auth";

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<UserProfile>;
  signup: (payload: SignupPayload) => Promise<UserProfile>;
  updateProfile: (payload: UpdateProfilePayload) => Promise<UserProfile>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await fetchCurrentUser();
      setUser(profile);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshUser();
  }, []);

  const login = async (payload: LoginPayload): Promise<UserProfile> => {
    await loginUser(payload);
    const profile = await fetchCurrentUser();
    setUser(profile);
    return profile;
  };

  const signup = async (payload: SignupPayload): Promise<UserProfile> => {
    await signupUser(payload);
    const profile = await fetchCurrentUser();
    setUser(profile);
    return profile;
  };

  const updateProfile = async (payload: UpdateProfilePayload): Promise<UserProfile> => {
    const updated = await updateCurrentUserProfile(payload);
    setUser(updated);
    return updated;
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        signup,
        updateProfile,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function getUserInitials(user?: UserProfile | null): string {
  if (!user) return "?";
  if (user.full_name && user.full_name.trim().length > 0) {
    const parts = user.full_name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return parts[0].slice(0, 2).toUpperCase();
  }
  if (user.email) {
    return user.email.slice(0, 2).toUpperCase();
  }
  return "?";
}

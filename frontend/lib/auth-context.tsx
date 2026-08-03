"use client"

import { createContext, useCallback, useContext, useEffect, useState } from "react"

export interface AuthUser {
  id: number
  username: string
  display_name?: string | null
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, displayName?: string) => Promise<void>
  logout: () => void
}

const TOKEN_KEY = "auth_token"

const AuthContext = createContext<AuthContextValue | null>(null)

// Read the stored bearer token outside React (used by feedback/chat callers).
export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null
  return window.localStorage.getItem(TOKEN_KEY)
}

function extractError(data: any, fallback: string): string {
  const detail = data?.errors?.[0]?.detail
  return detail || data?.error || fallback
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore session from a stored token on first mount.
  useEffect(() => {
    const stored = getStoredToken()
    if (!stored) {
      setLoading(false)
      return
    }
    setToken(stored)
    fetch("/api/auth/me", { headers: { Authorization: `Bearer ${stored}` } })
      .then(async (res) => {
        if (!res.ok) throw new Error("invalid session")
        const data = await res.json()
        setUser(data.data as AuthUser)
      })
      .catch(() => {
        window.localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const applyAuth = useCallback((accessToken: string, authUser: AuthUser) => {
    window.localStorage.setItem(TOKEN_KEY, accessToken)
    setToken(accessToken)
    setUser(authUser)
  }, [])

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(extractError(data, "Đăng nhập thất bại"))
      applyAuth(data.data.access_token, data.data.user)
    },
    [applyAuth],
  )

  const register = useCallback(
    async (username: string, password: string, displayName?: string) => {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, display_name: displayName || null }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(extractError(data, "Đăng ký thất bại"))
      applyAuth(data.data.access_token, data.data.user)
    },
    [applyAuth],
  )

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider")
  return ctx
}

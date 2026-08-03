// Single source of truth for the FastAPI backend base URL used by all
// app/api/* proxy routes (avoids re-declaring BACKEND_URL in each file).
export const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8001"

// Forward the caller's Authorization header (if any) to the backend so
// authenticated proxy calls carry the bearer token.
export function forwardAuthHeaders(request: Request): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  const auth = request.headers.get("authorization")
  if (auth) headers["Authorization"] = auth
  return headers
}

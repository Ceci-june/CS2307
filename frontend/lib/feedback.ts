// Client helper for recording user interactions (view/save/contact/share/thumbs).
// Attaches the bearer token when logged in; otherwise sends a stable anonymous
// session_id so the signal is still grouped. Fire-and-forget, never throws.
import { getStoredToken } from "./auth-context"

export type InteractionAction =
  | "view"
  | "save"
  | "contact"
  | "share"
  | "thumbs_up"
  | "thumbs_down"

const SESSION_KEY = "feedback_session_id"

function getSessionId(): string {
  if (typeof window === "undefined") return "server"
  let sid = window.localStorage.getItem(SESSION_KEY)
  if (!sid) {
    sid =
      (typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2)) as string
    window.localStorage.setItem(SESSION_KEY, sid)
  }
  return sid
}

export interface InteractionInput {
  listing_id: number | string
  action_type: InteractionAction
  source?: string
  dwell_time_seconds?: number
  raw_query?: string
  conversation_id?: number
}

export async function sendInteraction(input: InteractionInput): Promise<void> {
  try {
    const token = getStoredToken()
    const headers: Record<string, string> = { "Content-Type": "application/json" }
    if (token) headers["Authorization"] = `Bearer ${token}`

    const body: Record<string, unknown> = {
      ...input,
      listing_id: Number(input.listing_id),
    }
    if (!token) body.session_id = getSessionId()

    await fetch("/api/feedback", {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      keepalive: true, // allow the request to complete during page unload
    })
  } catch {
    // Feedback is best-effort; ignore network errors.
  }
}

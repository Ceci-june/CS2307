import { NextRequest, NextResponse } from "next/server"
import { BACKEND_URL, forwardAuthHeaders } from "@/lib/backend"

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/v1/auth/me`, {
      method: "GET",
      headers: forwardAuthHeaders(request),
      cache: "no-store",
    })
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed" },
      { status: 500 },
    )
  }
}

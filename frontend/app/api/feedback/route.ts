import { NextRequest, NextResponse } from "next/server"
import { BACKEND_URL, forwardAuthHeaders } from "@/lib/backend"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const response = await fetch(`${BACKEND_URL}/v1/feedback/interaction`, {
      method: "POST",
      headers: forwardAuthHeaders(request),
      body: JSON.stringify(body),
      cache: "no-store",
    })
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Feedback failed" },
      { status: 500 },
    )
  }
}

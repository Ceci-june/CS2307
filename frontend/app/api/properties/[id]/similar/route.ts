import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8001"

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const limit = request.nextUrl.searchParams.get("limit") || "6"
  try {
    const response = await fetch(
      `${BACKEND_URL}/v1/properties/${encodeURIComponent(id)}/similar?limit=${encodeURIComponent(limit)}`,
      { cache: "no-store" },
    )
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Similar search failed" },
      { status: 500 },
    )
  }
}


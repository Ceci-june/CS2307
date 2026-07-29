import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8001'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const queryString = searchParams.toString()

    console.log('[v0] API Route: Proxying request with query:', queryString)

    // Build the backend URL with all query parameters
    const backendUrl = `${BACKEND_URL}/v1/properties${queryString ? `?${queryString}` : ''}`
    console.log('[v0] API Route: Fetching from backend:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      console.error('[v0] API Route: Backend error:', response.status)
      return NextResponse.json(
        { error: `Backend API error: ${response.status}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    console.log('[v0] API Route: Successfully fetched data')

    return NextResponse.json(data)
  } catch (error) {
    console.error('[v0] API Route error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch properties', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}

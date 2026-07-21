import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    console.log('[v0] AI Search API: Received payload:', body)

    // Build backend URL
    const backendUrl = 'http://34.87.56.13:1605/v1/properties/ai-search'

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      console.error('[v0] AI Search API: Backend error:', response.status)
      return NextResponse.json(
        { error: `Backend API error: ${response.status}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    console.log('[v0] AI Search API: Successfully fetched data')

    return NextResponse.json(data)
  } catch (error) {
    console.error('[v0] AI Search API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to search properties', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}

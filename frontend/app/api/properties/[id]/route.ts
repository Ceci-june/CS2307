const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8001'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params

  if (!id) {
    return Response.json({ error: 'Missing property ID' }, { status: 400 })
  }

  try {
    const response = await fetch(`${BACKEND_URL}/v1/properties/${id}`, {
      headers: {
        'Accept': 'application/json',
      },
      // Disable caching for fresh data
      cache: 'no-store',
    })

    if (!response.ok) {
      if (response.status === 404) {
        return Response.json({ error: 'Property not found' }, { status: 404 })
      }
      return Response.json(
        { error: 'Failed to fetch property' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    console.error('[API] Error fetching property:', error)
    return Response.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

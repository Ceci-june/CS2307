'use client'

import { PropertyCard } from '@/components/property-card'

export function SimilarProperties() {
  // Dummy data for similar properties
  const similarProperties = [
    {
      id: '1',
      title: 'Căn hộ cao cấp tại Phú Nhuận',
      price_range: '4.5',
      area: 85,
      address: 'Phường 1, Quận Phú Nhuận, TP. HCM',
      description: 'Căn hộ 2 phòng ngủ, full nội thất cao cấp',
      images: ['https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&h=600&fit=crop'],
      listing_type: 'VIP Vàng',
      bedrooms: 2,
      bathrooms: 2,
      posted_date: new Date().toISOString(),
    },
    {
      id: '2',
      title: 'Nhà phố 4 tầng Bình Tân',
      price_range: '6.2',
      area: 120,
      address: 'Phường 2, Quận Bình Tân, TP. HCM',
      description: 'Nhà phố đẹp, vị trí đắc địa gần chợ',
      images: ['https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=600&fit=crop'],
      listing_type: 'Tin thường',
      bedrooms: 3,
      bathrooms: 2,
      posted_date: new Date().toISOString(),
    },
    {
      id: '3',
      title: 'Căn hộ penthouse Quận 7',
      price_range: '8.5',
      area: 150,
      address: 'Phường 2, Quận 7, TP. HCM',
      description: 'Penthouse sang trọng với view tuyệt đẹp',
      images: ['https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=800&h=600&fit=crop'],
      listing_type: 'VIP Kim Cương',
      bedrooms: 3,
      bathrooms: 3,
      posted_date: new Date().toISOString(),
    },
  ]

  return (
    <div className="space-y-4 pt-6">
      <h2 className="text-xl font-bold text-foreground">Bất động sản tương tự</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {similarProperties.map((property) => (
          <PropertyCard key={property.id} property={property} />
        ))}
      </div>
    </div>
  )
}

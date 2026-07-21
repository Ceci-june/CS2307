"use client"

import Image from "next/image"
import Link from "next/link"
import { Heart, MapPin, Camera, Bed, Bath } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface PropertyCardProps {
  property: {
    id: string
    title: string
    price_range: string
    area: number | null
    address: string
    description: string
    images: string[]
    listing_type: string
    bedrooms: number | null
    bathrooms: number | null
    posted_date: string
  }
}

const DEFAULT_IMAGE = "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&h=600&fit=crop"

const getBadgeStyle = (listingType: string) => {
  if (listingType === "VIP Kim Cương") {
    return { bg: "bg-[#E03C31]", text: "VIP KIM CƯƠNG" }
  } else if (listingType === "VIP Vàng") {
    return { bg: "bg-orange-500", text: "VIP VÀNG" }
  }
  return null
}

const formatDate = (dateString: string) => {
  try {
    const date = new Date(dateString)
    const day = String(date.getDate()).padStart(2, "0")
    const month = String(date.getMonth() + 1).padStart(2, "0")
    const year = date.getFullYear()
    return `${day}/${month}/${year}`
  } catch {
    return dateString
  }
}

export function PropertyCard({ property }: PropertyCardProps) {
  const imageUrl = property.images?.[0] || DEFAULT_IMAGE
  const badgeStyle = getBadgeStyle(property.listing_type)

  const handleCardClick = () => {
    // Save full property data to sessionStorage
    sessionStorage.setItem('selectedProperty', JSON.stringify(property))
  }

  return (
    <Link href={`/chi-tiet/${property.id}`} onClick={handleCardClick}>
      <div className="bg-card border border-border rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex flex-col md:flex-row">
          {/* Image Section - Left Side */}
          <div className="relative w-full md:w-[280px] lg:w-[320px] h-[200px] md:h-auto md:min-h-[220px] flex-shrink-0">
            <Image
              src={imageUrl}
              alt={property.title}
              fill
              className="object-cover"
              onError={(e) => {
                const img = e.target as HTMLImageElement
                img.src = DEFAULT_IMAGE
              }}
            />
            
            {/* Badge - Only show if not "Tin thường" */}
            {badgeStyle && (
              <div className="absolute top-3 left-3">
                <Badge className={`${badgeStyle.bg} hover:${badgeStyle.bg} text-white text-xs font-medium px-2 py-1`}>
                  {badgeStyle.text}
                </Badge>
              </div>
            )}

            {/* Photo Count */}
            {property.images && property.images.length > 0 && (
              <div className="absolute bottom-3 right-3 bg-black/60 text-white text-xs px-2 py-1 rounded flex items-center gap-1">
                <Camera className="h-3 w-3" />
                <span>{property.images.length}</span>
              </div>
            )}
          </div>

          {/* Content Section - Right Side */}
          <div className="flex-1 p-4 flex flex-col">
            {/* Title & Favorite */}
            <div className="flex items-start justify-between gap-2 mb-2">
              <h3 className="font-semibold text-foreground line-clamp-2 flex-1">
                {property.title}
              </h3>
              <button className="p-1.5 hover:bg-muted rounded-full transition-colors flex-shrink-0" onClick={(e) => e.preventDefault()}>
                <Heart className="h-5 w-5 text-muted-foreground" />
              </button>
            </div>

            {/* Price & Area */}
            <div className="flex items-center gap-3 mb-2">
              <span className="text-lg font-bold text-[#E03C31]">{property.price_range} Tỷ VNĐ</span>
              <span className="text-muted-foreground">|</span>
              <span className="text-muted-foreground">{property.area} m²</span>
            </div>

            {/* Location */}
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3">
              <MapPin className="h-4 w-4 flex-shrink-0" />
              <span className="line-clamp-1">{property.address}</span>
            </div>

            {/* Description */}
            <p className="text-sm text-muted-foreground line-clamp-2 mb-4 flex-1">
              {property.description}
            </p>

            {/* Specs - Bedrooms & Bathrooms */}
            <div className="flex items-center gap-4 mb-3">
              {property.bedrooms !== null && (
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Bed className="h-4 w-4" />
                  <span>{property.bedrooms} phòng</span>
                </div>
              )}
              {property.bathrooms !== null && (
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Bath className="h-4 w-4" />
                  <span>{property.bathrooms} phòng tắm</span>
                </div>
              )}
            </div>

            {/* Footer - Posted Date or View Details Button */}
            <div className="flex items-center justify-between pt-3 border-t border-border">
              <p className="text-xs text-muted-foreground">
                {formatDate(property.posted_date)}
              </p>
              <Button className="bg-[#E03C31] hover:bg-[#c43428] text-white h-9 px-4 text-sm" onClick={(e) => e.preventDefault()}>
                Xem chi tiết
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Link>
  )
}

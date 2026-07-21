'use client'

import { MapPin } from 'lucide-react'

interface LocationSectionProps {
  address: string
}

export function LocationSection({ address }: LocationSectionProps) {
  return (
    <div className="space-y-3 pb-4 border-b border-border">
      <h2 className="text-xl font-bold text-foreground">Vị trí trên bản đồ</h2>
      <div className="relative w-full aspect-video rounded-lg overflow-hidden bg-muted border border-border group">
        {/* Map Placeholder - styled like an iframe */}
        <iframe
          src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3919.2506098937!2d106.7194!3d10.7769!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3175c59140d1be19%3A0xf51ce6427b7918f0!2sHo%20Chi%20Minh%20City%2C%20Vietnam!5e0!3m2!1sen!2sus!4v1234567890"
          width="100%"
          height="100%"
          style={{ border: 0, borderRadius: '8px' }}
          allowFullScreen={true}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          className="w-full h-full"
        />
      </div>

      {/* Address Info */}
      <div className="flex items-start gap-2 p-3 bg-card rounded-lg">
        <MapPin className="h-5 w-5 text-[#E03C31] flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-foreground">Địa chỉ</p>
          <p className="text-sm text-muted-foreground">{address}</p>
        </div>
      </div>
    </div>
  )
}

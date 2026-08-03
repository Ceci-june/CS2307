'use client'

import { useState } from 'react'
import { Heart, Share2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import { sendInteraction } from '@/lib/feedback'

interface ContactFormProps {
  listingId?: number | string
}

export function ContactForm({ listingId }: ContactFormProps) {
  const [formData, setFormData] = useState({ name: '', phone: '' })
  const [saved, setSaved] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (listingId != null) {
      sendInteraction({ listing_id: listingId, action_type: 'contact', source: 'detail' })
    }
  }

  const handleSave = () => {
    setSaved(true)
    if (listingId != null) {
      sendInteraction({ listing_id: listingId, action_type: 'save', source: 'detail' })
    }
  }

  const handleShare = () => {
    if (listingId != null) {
      sendInteraction({ listing_id: listingId, action_type: 'share', source: 'detail' })
    }
    if (typeof navigator !== 'undefined' && navigator.share) {
      navigator.share({ url: window.location.href }).catch(() => {})
    }
  }

  return (
    <div className="space-y-4">
      {/* Booking Form */}
      <Card className="p-4 space-y-4">
        <h3 className="font-semibold text-foreground">Yêu cầu liên hệ lại</h3>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-sm">
              Họ và tên
            </Label>
            <Input
              id="name"
              name="name"
              placeholder="Nhập họ tên"
              value={formData.name}
              onChange={handleChange}
              className="text-sm"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone" className="text-sm">
              Số điện thoại
            </Label>
            <Input
              id="phone"
              name="phone"
              placeholder="Nhập số điện thoại"
              value={formData.phone}
              onChange={handleChange}
              className="text-sm"
            />
          </div>

          <Button type="submit" className="w-full bg-[#E03C31] hover:bg-[#c43428] text-white font-medium text-sm">
            Yêu cầu liên hệ lại
          </Button>
        </form>
      </Card>

      {/* Quick CTAs */}
      <div className="flex gap-2">
        <Button type="button" variant="outline" className="flex-1 text-sm" onClick={handleSave}>
          <Heart className={`h-4 w-4 mr-1.5 ${saved ? 'fill-[#E03C31] text-[#E03C31]' : ''}`} />
          Yêu thích
        </Button>
        <Button type="button" variant="outline" className="flex-1 text-sm" onClick={handleShare}>
          <Share2 className="h-4 w-4 mr-1.5" />
          Chia sẻ
        </Button>
      </div>
    </div>
  )
}

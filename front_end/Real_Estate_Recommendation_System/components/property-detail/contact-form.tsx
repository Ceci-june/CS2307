'use client'

import { useState } from 'react'
import { Heart, Share2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'

export function ContactForm() {
  const [formData, setFormData] = useState({ name: '', phone: '' })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Form submitted:', formData)
    // TODO: Implement API call
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
        <Button variant="outline" className="flex-1 text-sm">
          <Heart className="h-4 w-4 mr-1.5" />
          Yêu thích
        </Button>
        <Button variant="outline" className="flex-1 text-sm">
          <Share2 className="h-4 w-4 mr-1.5" />
          Chia sẻ
        </Button>
      </div>
    </div>
  )
}

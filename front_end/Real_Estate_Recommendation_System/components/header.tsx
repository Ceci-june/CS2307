"use client"

import { Home, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { usePathname } from "next/navigation"

export function Header() {
  const pathname = usePathname()

  const isActive = (href: string) => {
    return pathname === href
  }

  const getLinkClassName = (href: string) => {
    const base = "text-sm font-medium transition-colors rounded-md px-3 py-2"
    if (isActive(href)) {
      return `${base} bg-red-50 text-red-600 font-semibold`
    }
    return `${base} text-foreground hover:text-[#E03C31]`
  }

  return (
    <div className="border-b border-border bg-background">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="p-1.5 bg-[#E03C31] rounded">
            <Home className="h-5 w-5 text-white" />
          </div>
          <span className="font-bold text-lg text-foreground">BATDONGSAN AI</span>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-2">
          <Link href="/" className={getLinkClassName("/")}>
            Tìm kiếm thủ công
          </Link>
          <Link href="/tim-kiem-chuyen-sau" className={getLinkClassName("/tim-kiem-chuyen-sau")}>
            Tìm kiếm chuyên sâu
          </Link>
          <Link href="/tin-tuc" className={getLinkClassName("/tin-tuc")}>
            Tin tức
          </Link>
        </nav>

        {/* Auth Buttons */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" className="text-sm font-medium text-foreground">
            Đăng nhập
          </Button>
          <Button variant="outline" className="text-sm font-medium text-[#E03C31] border-[#E03C31] hover:bg-[#E03C31]/10">
            Đăng ký
          </Button>
          <Button className="bg-[#E03C31] hover:bg-[#c43428] text-white text-sm font-medium">
            <Upload className="h-4 w-4 mr-2" />
            Đăng tin
          </Button>
        </div>
      </div>
    </div>
  )
}

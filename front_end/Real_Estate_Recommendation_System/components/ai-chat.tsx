"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Bot, User, Loader2, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PropertyCard } from "@/components/property-card"

interface ChatMessage {
  role: "user" | "ai"
  content?: string
  properties?: any[]
  timestamp: string
}

interface AISearchPayload {
  question: string
  [key: string]: any
}

interface AIChatProps {
  filters?: any
}

export function AIChat({ filters: propFilters = {} }: AIChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  // Use propFilters directly instead of managing local state
  const currentFilters = propFilters
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialize with welcome message
  useEffect(() => {
    const welcomeMessage: ChatMessage = {
      role: "ai",
      content: "Xin chào! Tôi là trợ lý AI chuyên về bất động sản. Dựa trên các tiêu chí bạn đang nhập, tôi có thể giúp bạn tìm căn hộ hoặc nhà phố phù hợp nhất. Bạn muốn tôi gợi ý Căn hộ/Nhà đất như thế nào?",
      timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
    }
    setMessages([welcomeMessage])
  }, [])

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!inputValue.trim()) return

    // Capture the input before clearing
    const userQuestion = inputValue

    // Add user message
    const userMessage: ChatMessage = {
      role: "user",
      content: userQuestion,
      timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
    }
    setMessages(prev => [...prev, userMessage])
    setInputValue("")

    // Add loading message
    const loadingMessage: ChatMessage = {
      role: "ai",
      content: "Đang tìm kiếm...",
      timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
    }
    setMessages(prev => [...prev, loadingMessage])
    setIsLoading(true)

    try {
      // Create a formatted payload specifically for the AI backend
      // Use strict fallbacks to ensure max_price and max_area are never undefined
      const apiPayload = {
        question: userQuestion,
        min_price: currentFilters.min_price || 0,
        max_price: (currentFilters.max_price === 0 || !currentFilters.max_price) ? 999999 : currentFilters.max_price,
        min_area: currentFilters.min_area || 0,
        max_area: (currentFilters.max_area === 0 || !currentFilters.max_area) ? 999999 : currentFilters.max_area,
        bedrooms: currentFilters.bedrooms || 0,
        bathrooms: currentFilters.bathrooms || 0,
        legal_status: currentFilters.legal_status || "",
        furniture: currentFilters.furniture || "",
        house_direction: currentFilters.house_direction || "",
        balcony_direction: currentFilters.balcony_direction || "",
        district: currentFilters.district || "",
        property_type: currentFilters.property_type || "",
        length_road_entrance: 0,
        // Force all boolean fields to be true/false, NOT 1/0
        pool: !!currentFilters.pool,
        gym: !!currentFilters.gym,
        park: !!currentFilters.park,
        bbq: !!currentFilters.bbq,
        kids_playground: !!currentFilters.kids_playground,
        sports_court: !!currentFilters.sports_court,
        security_24h: !!currentFilters.security_24h,
        reception: !!currentFilters.reception,
        elevator: !!currentFilters.elevator,
        parking: !!currentFilters.parking,
        near_metro: !!currentFilters.near_metro,
        near_bus: !!currentFilters.near_bus,
        near_highway: !!currentFilters.near_highway,
        near_school: !!currentFilters.near_school,
        near_hospital: !!currentFilters.near_hospital,
        near_mall: !!currentFilters.near_mall,
        near_market: !!currentFilters.near_market,
        near_park: !!currentFilters.near_park,
        river_view: !!currentFilters.river_view,
        park_view: !!currentFilters.park_view,
        city_view: !!currentFilters.city_view,
        balcony: !!currentFilters.balcony,
        garden: !!currentFilters.garden,
        garage: !!currentFilters.garage,
        terrace: !!currentFilters.terrace,
      }

      console.log("[v0] AI Search payload:", apiPayload)

      // Use the API proxy route
      const response = await fetch("/api/properties/ai-search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(apiPayload),
      })

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`)
      }

      const data = await response.json()
      console.log("[v0] AI Search response:", data)

      // Parse response
      const properties = data.data || []

      // Update the last message with AI response
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: "ai",
          content: properties.length > 0 
            ? "Dựa trên yêu cầu của bạn, tôi tìm thấy các bất động sản sau:"
            : "Xin lỗi, tôi không tìm thấy bất động sản nào phù hợp với yêu cầu của bạn. Vui lòng thử thay đổi tiêu chí tìm kiếm.",
          properties: properties.length > 0 ? properties : undefined,
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
        }
        return updated
      })
    } catch (error) {
      console.error("[v0] AI Search error:", error)
      
      // Update the last message with error
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: "ai",
          content: "Xin lỗi, đã xảy ra lỗi khi tìm kiếm. Vui lòng thử lại sau.",
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
        }
        return updated
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Chat Header */}
      <div className="shrink-0 flex items-center gap-3 px-4 py-3 bg-background border-b border-border">
        <div className="w-10 h-10 rounded-full bg-[#E03C31]/10 flex items-center justify-center">
          <Bot className="w-5 h-5 text-[#E03C31]" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">AI Real Estate Assistant</h3>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span className="text-xs text-emerald-600">Đang trực tuyến</span>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, idx) => (
          <div key={idx} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            {message.role === "ai" && (
              <div className="w-8 h-8 rounded-full bg-[#E03C31]/10 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-[#E03C31]" />
              </div>
            )}
            
            <div className={`max-w-[75%] ${message.role === "user" ? "order-1" : ""}`}>
              {/* Message Bubble */}
              <div className={`rounded-2xl px-4 py-3 ${
                message.role === "user" 
                  ? "bg-[#E03C31] text-white rounded-tr-sm" 
                  : "bg-muted text-foreground rounded-tl-sm"
              }`}>
                <p className="text-sm leading-relaxed">{message.content}</p>
              </div>

              {/* Properties Grid */}
              {message.properties && message.properties.length > 0 && (
                <div className="mt-3 space-y-3 pr-2">
                  {message.properties.slice(0, 3).map((property) => (
                    <div key={property.id} className="flex flex-col gap-3 mb-6">
                      {/* Property Card */}
                      <PropertyCard property={property} />
                      
                      {/* AI Insights Box */}
                      {(property.explanation || property.comparison) && (
                        <div className="bg-muted/50 rounded-lg p-4 text-sm text-foreground border border-border">
                          <div className="flex items-center gap-2 mb-3">
                            <Sparkles className="w-4 h-4 text-[#E03C31]" />
                            <span className="font-semibold">AI Insights</span>
                          </div>
                          
                          {property.explanation && (
                            <div className="mb-3">
                              <span className="font-semibold">💡 Lý do đề xuất:</span>
                              <p className="mt-1 text-muted-foreground">{property.explanation}</p>
                            </div>
                          )}
                          
                          {property.comparison && (
                            <div>
                              <span className="font-semibold">⚖️ Đánh giá:</span>
                              <p className="mt-1 text-muted-foreground">{property.comparison}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <p className={`text-[10px] mt-1 ${message.role === "user" ? "text-right text-muted-foreground" : "text-muted-foreground"}`}>
                {message.timestamp}
              </p>
            </div>

            {message.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-[#E03C31] flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-white" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="shrink-0 border-t border-border p-4 bg-background">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <Input
            placeholder="Hỏi AI bất cứ điều gì về nhà đất..."
            className="flex-1 h-10"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isLoading}
          />
          <Button 
            type="submit"
            size="icon" 
            className="h-10 w-10 bg-[#E03C31] hover:bg-[#c43428] flex-shrink-0 disabled:opacity-50"
            disabled={isLoading || !inputValue.trim()}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  )
}

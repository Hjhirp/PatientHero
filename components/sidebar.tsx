"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { SettingsDialog } from "@/components/settings-dialog"
import { 
  MessageSquare, 
  Plus, 
  X, 
  Settings,
  ChevronLeft,
  ChevronRight,
  Calendar,
  Bot
} from "lucide-react"
import { cn, formatDate } from "@/lib/utils"

interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  timestamp: Date
}

interface Chat {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}

interface SidebarProps {
  chats: Chat[]
  activeChat: Chat | null
  onChatSelect: (chat: Chat) => void
  onNewChat: () => void
  isOpen: boolean
  onToggle: () => void
}

export function Sidebar({
  chats,
  activeChat,
  onChatSelect,
  onNewChat,
  isOpen,
  onToggle,
}: SidebarProps) {
  const [searchTerm, setSearchTerm] = useState("")

  const filteredChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const groupedChats = filteredChats.reduce(
    (groups: { [key: string]: Chat[] }, chat) => {
      const today = new Date()
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)
      const week = new Date(today)
      week.setDate(week.getDate() - 7)

      let groupKey = "Older"
      if (chat.updatedAt.toDateString() === today.toDateString()) {
        groupKey = "Today"
      } else if (chat.updatedAt.toDateString() === yesterday.toDateString()) {
        groupKey = "Yesterday"
      } else if (chat.updatedAt >= week) {
        groupKey = "Previous 7 days"
      }

      if (!groups[groupKey]) {
        groups[groupKey] = []
      }
      groups[groupKey].push(chat)
      return groups
    },
    {}
  )

  if (!isOpen) {
    return (
      <div className="flex h-full w-12 flex-col items-center border-r bg-muted/10 py-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="mb-4"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={onNewChat}
          className="mb-4"
        >
          <Plus className="h-4 w-4" />
        </Button>
        <div className="flex-1" />
        <SettingsDialog>
          <Button variant="ghost" size="icon">
            <Settings className="h-4 w-4" />
          </Button>
        </SettingsDialog>
      </div>
    )
  }

  return (
    <div className="flex h-full w-80 flex-col border-r bg-muted/10">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Bot className="h-4 w-4" />
          </div>
          <span className="font-semibold">PatientHero</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="hidden md:flex"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </div>

      {/* New Chat Button */}
      <div className="px-4 pb-4">
        <Button
          onClick={onNewChat}
          className="w-full justify-start gap-2"
          variant="outline"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <Separator />

      {/* Chat List */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {Object.entries(groupedChats).map(([groupName, groupChats]) => (
            <div key={groupName} className="mb-4">
              <div className="px-2 py-1">
                <Badge variant="secondary" className="text-xs">
                  {groupName}
                </Badge>
              </div>
              <div className="space-y-1">
                {groupChats.map((chat) => (
                  <Card
                    key={chat.id}
                    className={cn(
                      "cursor-pointer border-0 p-3 transition-colors hover:bg-muted/50",
                      activeChat?.id === chat.id && "bg-muted"
                    )}
                    onClick={() => onChatSelect(chat)}
                  >
                    <div className="flex items-start gap-3">
                      <MessageSquare className="h-4 w-4 mt-0.5 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">
                          {chat.title}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {chat.messages.length > 0
                            ? chat.messages[chat.messages.length - 1].content.slice(0, 50) + "..."
                            : "No messages"}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {formatDate(chat.updatedAt)}
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ))}
          {filteredChats.length === 0 && (
            <div className="text-center py-8">
              <MessageSquare className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">No chats found</p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t">
        <SettingsDialog>
          <Button variant="ghost" className="w-full justify-start gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </Button>
        </SettingsDialog>
      </div>
    </div>
  )
}

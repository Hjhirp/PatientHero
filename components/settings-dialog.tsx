"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Settings, User, Key, Palette, Globe } from "lucide-react"

interface SettingsDialogProps {
  children: React.ReactNode
}

export function SettingsDialog({ children }: SettingsDialogProps) {
  const [apiKey, setApiKey] = useState("")
  const [modelName, setModelName] = useState("gpt-3.5-turbo")
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2048)

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings
          </DialogTitle>
          <DialogDescription>
            Configure your PatientHero chatbot settings
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* API Configuration */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              <h3 className="text-lg font-semibold">API Configuration</h3>
            </div>
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="apiKey">OpenAI API Key</Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="sk-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Your API key is stored locally and never sent to our servers
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Input
                  id="model"
                  placeholder="gpt-3.5-turbo"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Model Parameters */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              <h3 className="text-lg font-semibold">Model Parameters</h3>
            </div>
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="temperature">
                  Temperature: {temperature}
                </Label>
                <input
                  id="temperature"
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  Controls randomness: 0 is focused, 2 is creative
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="maxTokens">Max Tokens: {maxTokens}</Label>
                <input
                  id="maxTokens"
                  type="range"
                  min="256"
                  max="4096"
                  step="256"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  Maximum length of the AI response
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Profile */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <h3 className="text-lg font-semibold">Profile</h3>
            </div>
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="userName">Display Name</Label>
                <Input
                  id="userName"
                  placeholder="Enter your name"
                  defaultValue="Patient"
                />
              </div>
              <div className="space-y-2">
                <Label>Account Type</Label>
                <Badge variant="secondary">Free Plan</Badge>
                <p className="text-xs text-muted-foreground">
                  Upgrade to Pro for unlimited conversations
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Actions */}
          <div className="flex justify-between">
            <Button variant="outline">Reset to Defaults</Button>
            <div className="space-x-2">
              <Button variant="outline">Cancel</Button>
              <Button>Save Changes</Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

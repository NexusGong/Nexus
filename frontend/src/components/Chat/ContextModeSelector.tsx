import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Briefcase, 
  Heart, 
  Users, 
  MessageSquare,
  Check
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ContextModeSelectorProps {
  selectedMode: string
  onModeChange: (mode: string) => void
  className?: string
}

const contextModes = [
  {
    id: 'general',
    name: '通用模式',
    description: '适用于一般社交场景',
    icon: MessageSquare,
    color: 'bg-blue-100 text-blue-600'
  },
  {
    id: 'work',
    name: '职场模式',
    description: '适用于工作场景，注重专业性和效率',
    icon: Briefcase,
    color: 'bg-green-100 text-green-600'
  },
  {
    id: 'intimate',
    name: '亲密关系',
    description: '适用于情侣、家人等亲密关系',
    icon: Heart,
    color: 'bg-pink-100 text-pink-600'
  },
  {
    id: 'social',
    name: '社交模式',
    description: '适用于社交网络和陌生人交流',
    icon: Users,
    color: 'bg-purple-100 text-purple-600'
  }
]

export default function ContextModeSelector({ 
  selectedMode, 
  onModeChange, 
  className 
}: ContextModeSelectorProps) {
  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <CardTitle className="text-lg">情景模式</CardTitle>
        <CardDescription>
          选择适合的对话场景，AI将根据场景提供更精准的分析
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {contextModes.map((mode) => {
            const Icon = mode.icon
            const isSelected = selectedMode === mode.id
            
            return (
              <Button
                key={mode.id}
                variant={isSelected ? "default" : "outline"}
                className={cn(
                  "h-auto p-4 flex flex-col items-start gap-2",
                  isSelected && "ring-2 ring-primary"
                )}
                onClick={() => onModeChange(mode.id)}
              >
                <div className="flex items-center gap-2 w-full">
                  <div className={cn(
                    "p-2 rounded-full",
                    isSelected ? "bg-primary-foreground text-primary" : mode.color
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className="font-medium text-sm">{mode.name}</span>
                  {isSelected && (
                    <Check className="h-4 w-4 ml-auto" />
                  )}
                </div>
                <p className="text-xs text-muted-foreground text-left">
                  {mode.description}
                </p>
              </Button>
            )
          })}
        </div>
        
        {selectedMode && (
          <div className="mt-4 p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="secondary">
                {contextModes.find(m => m.id === selectedMode)?.name}
              </Badge>
              <span className="text-sm text-muted-foreground">已选择</span>
            </div>
            <p className="text-xs text-muted-foreground">
              AI将根据此场景调整分析重点和回复建议
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}


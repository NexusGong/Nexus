import { useState, useEffect } from 'react'
import { Bot, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LoadingMessageProps {
  className?: string
}

export default function LoadingMessage({ className }: LoadingMessageProps) {
  const [currentStep, setCurrentStep] = useState(0)
  
  const loadingSteps = [
    '正在识别内容...',
    '正在解析意图...',
    '正在分析情感...',
    '正在生成建议...',
    '正在整理结果...'
  ]

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % loadingSteps.length)
    }, 1500) // 每1.5秒切换一次

    return () => clearInterval(interval)
  }, [])

  return (
    <div className={cn("flex gap-3 mb-3 justify-start", className)}>
      {/* AI头像 */}
      <div className="flex-shrink-0">
        <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
          <Bot className="h-4 w-4" />
        </div>
      </div>

      {/* 加载消息内容 */}
      <div className="flex flex-col gap-1 max-w-[80%] items-start">
        <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-gray-100 text-gray-900 text-sm leading-relaxed">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
            <span>{loadingSteps[currentStep]}</span>
            <div className="flex gap-1 ml-1">
              <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"></div>
              <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

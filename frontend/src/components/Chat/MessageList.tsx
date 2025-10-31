import { useEffect, useRef } from 'react'
import { Message } from '@/store/chatStore'
import MessageItem from './MessageItem'
import { cn } from '@/lib/utils'

interface MessageListProps {
  messages: Message[]
  onRegenerateAnalysis?: (originalMessage: string) => void
}

export default function MessageList({ messages, onRegenerateAnalysis }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-4xl mx-auto p-4">
        {messages.map((message, index) => (
          <div
            key={message.id}
            className={cn(
              "animate-in slide-in-from-bottom-2 duration-300",
              index === messages.length - 1 && "animate-in fade-in duration-500"
            )}
          >
            <MessageItem 
              message={message} 
              onRegenerateAnalysis={onRegenerateAnalysis}
            />
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

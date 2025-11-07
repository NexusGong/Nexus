import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import ChatInterface from '@/components/Chat/ChatInterface'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { conversationApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'

export default function ChatPage() {
  const { conversationId } = useParams()
  const { isAuthenticated } = useAuthStore()
  const { 
    currentConversation, 
    setCurrentConversation,
    setCurrentMessages,
    setLoading,
    setError 
  } = useChatStore()
  const { toast } = useToast()

  useEffect(() => {
    const loadConversation = async () => {
      // 如果未登录，清空对话数据
      if (!isAuthenticated) {
        setCurrentConversation(null)
        setCurrentMessages([])
        return
      }

      if (conversationId) {
        try {
          setLoading(true)
          const conversation = await conversationApi.getConversation(Number(conversationId))
          setCurrentConversation(conversation)
          
          // 加载消息历史
          const messages = await conversationApi.getMessages(Number(conversationId))
          setCurrentMessages(messages)
        } catch (error) {
          console.error('加载对话失败:', error)
          toast({
            title: "加载失败",
            description: "无法加载对话内容，请重试",
            variant: "destructive"
          })
          setError('加载对话失败')
        } finally {
          setLoading(false)
        }
      } else {
        // 新建对话
        setCurrentConversation(null)
        setCurrentMessages([])
      }
    }

    loadConversation()
  }, [conversationId, isAuthenticated, setCurrentConversation, setCurrentMessages, setLoading, setError, toast])

  return (
    <div className="h-full min-h-0">
      {/* 聊天界面 */}
      <ChatInterface />
    </div>
  )
}

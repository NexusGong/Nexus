import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ChatInterface from '@/components/Chat/ChatInterface'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { conversationApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'

export default function ChatPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
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
        // 如果URL中有conversationId，清除它并导航到/chat
        if (conversationId) {
          navigate('/chat', { replace: true })
        }
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
        } catch (error: any) {
          console.error('加载对话失败:', error)
          
          // 处理token过期的情况
          if ((error as any).isTokenExpired) {
            // Token已过期，响应拦截器已经处理了退出登录
            // 这里只需要清除对话数据并导航
            setCurrentConversation(null)
            setCurrentMessages([])
            navigate('/chat', { replace: true })
            toast({
              title: "登录已过期",
              description: "您的登录已过期，请重新登录",
              variant: "destructive"
            })
            return
          }
          
          // 处理403错误：对话属于已登录用户，但当前未登录
          if (error.response?.status === 403) {
            const errorDetail = error.response?.data?.detail || ''
            if (errorDetail.includes('已登录用户')) {
              // 清除对话数据
              setCurrentConversation(null)
              setCurrentMessages([])
              // 导航到/chat（不带conversationId）
              navigate('/chat', { replace: true })
              toast({
                title: "需要登录",
                description: "该对话属于已登录用户，请先登录后访问",
                variant: "destructive"
              })
              return
            }
          }
          
          // 其他错误
          toast({
            title: "加载失败",
            description: error.response?.data?.detail || "无法加载对话内容，请重试",
            variant: "destructive"
          })
          setError('加载对话失败')
          // 清除无效的对话ID
          if (conversationId) {
            navigate('/chat', { replace: true })
          }
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
  }, [conversationId, isAuthenticated, setCurrentConversation, setCurrentMessages, setLoading, setError, toast, navigate])

  return (
    <div className="h-full min-h-0">
      {/* 聊天界面 */}
      <ChatInterface />
    </div>
  )
}

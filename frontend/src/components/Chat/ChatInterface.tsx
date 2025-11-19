import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { 
  Send, 
  Loader2,
  MessageSquare,
  Image as ImageIcon,
  Sparkles,
  Users
} from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { conversationApi, chatApi, authApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import MessageList from './MessageList'
import FileUploader from './FileUploader'
import MultiImageUploader from './MultiImageUploader'
import LoadingMessage from './LoadingMessage'
import { cn } from '@/lib/utils'

export default function ChatInterface() {
  const [inputValue, setInputValue] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const [pendingContextMode, setPendingContextMode] = useState<'general'|'work'|'intimate'|'social'>('general')
  const [showWelcomeScreen, setShowWelcomeScreen] = useState(true)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const navigate = useNavigate()
  
  const {
    currentConversation,
    currentMessages,
    isAnalyzing,
    setCurrentConversation,
    addMessage,
    setCurrentMessages,
    setCurrentAnalysis,
    setCurrentSuggestions,
    setAnalyzing,
    setError,
    addConversation
  } = useChatStore()
  
  const { isAuthenticated, user, setUsageStats } = useAuthStore()
  const { toast } = useToast()
  
  // 当登录状态变化时，重新获取使用统计
  useEffect(() => {
    const loadUsageStats = async () => {
      try {
        const stats = await authApi.getUsageStats()
        setUsageStats(stats)
      } catch (error) {
        console.error('获取使用统计失败:', error)
      }
    }
    loadUsageStats()
  }, [isAuthenticated, setUsageStats])

  // 当有消息时，隐藏欢迎界面
  useEffect(() => {
    if (currentMessages.length > 0) {
      setShowWelcomeScreen(false)
    } else if (currentMessages.length === 0 && !currentConversation) {
      // 如果没有消息且没有当前对话，显示欢迎界面
      setShowWelcomeScreen(true)
    }
  }, [currentMessages, currentConversation])

  // 自动调整输入框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [inputValue])

  // 重新分析功能
  const handleRegenerateAnalysis = async (originalMessage: string) => {
    if (!currentConversation || isAnalyzing) return

    setAnalyzing(true)
    
    try {
      const response = await chatApi.analyzeChat({
        conversation_id: currentConversation.id,
        message: originalMessage,
        context_mode: currentConversation.context_mode
      })

      // 移除之前的AI分析消息，添加新的分析结果
      setCurrentMessages(prev => {
        const filtered = prev.filter(msg => !(msg.role === 'assistant' && msg.message_type === 'analysis'))
        const aiMessage = {
          ...response.message,
          content: response.message.content,
          analysis_result: response.analysis,
          analysis_metadata: {
            ...response.message.analysis_metadata,
            suggestions: response.suggestions
          }
        }
        return [...filtered, aiMessage]
      })
      
      setCurrentAnalysis(response.analysis)
      setCurrentSuggestions(response.suggestions)

      toast({
        title: "重新分析完成",
        description: "已生成新的分析结果和回复建议",
        duration: 2000
      })
    } catch (error) {
      console.error('重新分析失败:', error)
      toast({
        title: "重新分析失败",
        description: "请重试",
        variant: "destructive",
        duration: 3000
      })
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isAnalyzing) return

    const message = inputValue.trim()
    setInputValue('')

    try {
      let conversation = currentConversation
      
      // 如果没有当前对话，创建新对话
      if (!conversation) {
        try {
          conversation = await conversationApi.createConversation({
            title: message.slice(0, 30) + (message.length > 30 ? '...' : ''),
            context_mode: pendingContextMode || 'general'
          })
          setCurrentConversation(conversation)
          // 不在这里添加到对话列表，只有在消息成功发送后才添加
          // 更新使用统计（创建对话后）
          try {
            const stats = await authApi.getUsageStats()
            setUsageStats(stats)
          } catch (error) {
            console.error('更新使用统计失败:', error)
          }
          // 导航到新对话页面
          navigate(`/chat/${conversation.id}`, { replace: true })
        } catch (error: any) {
          if (error.response?.status === 403) {
            toast({
              title: "会话创建失败",
              description: error.response?.data?.detail || "非登录用户最多只能创建5个会话，请登录后继续使用。",
              variant: "destructive",
              duration: 4000
            })
            return
          }
          throw error
        }
      }

      // 隐藏欢迎界面
      setShowWelcomeScreen(false)
      
      // 添加用户消息到界面
      const userMessage = {
        id: Date.now(),
        role: 'user' as const,
        content: message,
        message_type: 'text',
        source: 'manual',
        is_processed: false,
        is_archived: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      addMessage(userMessage)

      // 检查使用次数限制
      try {
        const stats = await authApi.getUsageStats()
        setUsageStats(stats)
      } catch (error) {
        console.error('获取使用统计失败:', error)
      }

      // 开始分析
      setAnalyzing(true)
      try {
        const response = await chatApi.analyzeChat({
          conversation_id: conversation.id,
          message: message,
          context_mode: conversation.context_mode
        })
        
        // 更新使用统计
        try {
          const stats = await authApi.getUsageStats()
          setUsageStats(stats)
        } catch (error) {
          console.error('更新使用统计失败:', error)
        }

        // 添加AI分析消息
        const aiMessage = {
          ...response.message,
          content: response.message.content,
          analysis_result: response.analysis,
          analysis_metadata: {
            ...response.message.analysis_metadata,
            suggestions: response.suggestions
          }
        }
        
        addMessage(aiMessage)
        
        // 设置分析结果和建议
        setCurrentAnalysis(response.analysis)
        setCurrentSuggestions(response.suggestions)

        // 消息成功发送后，添加到侧边栏的对话列表
        if (conversation) {
          try {
            const convResponse = await conversationApi.getConversations(1, 20)
            const updatedConversation = convResponse.conversations?.find((c: any) => c.id === conversation.id)
            if (updatedConversation) {
              // 检查对话是否已在列表中
              const { conversations } = useChatStore.getState()
              const exists = conversations.some((conv: any) => conv.id === conversation.id)
              
              if (exists) {
                // 如果已存在，更新对话
                updateConversation(conversation.id, updatedConversation)
              } else {
                // 如果不存在，添加到列表顶部
                addConversation(updatedConversation)
              }
            }
          } catch (error) {
            console.error('更新对话列表失败:', error)
          }
        }

        toast({
          title: "分析完成",
          description: "已生成分析结果和回复建议",
          duration: 2000
        })
      } catch (error: any) {
        if (error.response?.status === 403) {
          toast({
            title: "分析失败",
            description: error.response?.data?.detail || "该会话今日分析次数已达上限，请登录后获得更多次数。",
            variant: "destructive",
            duration: 4000
          })
          return
        }
        throw error
      }

    } catch (error) {
      console.error('发送消息失败:', error)
      toast({
        title: "发送失败",
        description: "消息发送失败，请重试",
        variant: "destructive",
        duration: 3000
      })
      setError('发送消息失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }


  const handleNewChat = async () => {
    setCurrentConversation(null)
    setCurrentMessages([])
    setInputValue('')
    // 显示欢迎界面
    setShowWelcomeScreen(true)
    // 如果已登录，导航到 /chat；如果未登录，导航到主页
    if (isAuthenticated && user) {
      navigate('/chat', { replace: true })
    } else {
      navigate('/', { replace: true })
    }
  }


  return (
    <div className="flex flex-col h-full">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto bg-background">
        {currentMessages.length > 0 ? (
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto p-4">
              <MessageList 
                messages={currentMessages} 
                onRegenerateAnalysis={handleRegenerateAnalysis}
              />
              {/* 显示加载状态 */}
              {isAnalyzing && <LoadingMessage />}
            </div>
          </div>
        ) : showWelcomeScreen && isAuthenticated && user ? (
          // 登录后的欢迎界面 - 模式选择界面（无输入框）
          <div className="flex flex-col items-center justify-center h-full bg-background">
            <div className="text-center max-w-5xl mx-auto px-6 py-12 w-full">
              <div className="mb-12">
                <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                  <MessageSquare className="h-12 w-12 text-white" />
                </div>
                <h2 className="text-3xl font-bold mb-3 text-foreground">
                  欢迎回来，{user.username}！
                </h2>
                <p className="text-lg text-muted-foreground mb-2 leading-relaxed">
                  选择你喜欢的方式吧
                </p>
              </div>

              {/* 模式选择卡片 - 大卡片带详细介绍 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
                {/* 卡片模式 */}
                <Card 
                  className="cursor-pointer hover:shadow-xl transition-all duration-300 hover:-translate-y-2 border-2 hover:border-purple-500/50 group relative overflow-hidden"
                  onClick={() => navigate('/card-mode')}
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-bl-full"></div>
                  <div className="relative p-6">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center group-hover:from-purple-500/30 group-hover:to-pink-500/30 transition-colors flex-shrink-0">
                        <Sparkles className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-foreground mb-2">抽张卡吧</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          抽一张卡片式的建议把
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* 自由交谈模式 */}
                <Card 
                  className="cursor-pointer hover:shadow-xl transition-all duration-300 hover:-translate-y-2 border-2 hover:border-blue-500/50 group relative overflow-hidden"
                  onClick={() => navigate('/chat-mode')}
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-bl-full"></div>
                  <div className="relative p-6">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center group-hover:from-blue-500/30 group-hover:to-cyan-500/30 transition-colors flex-shrink-0">
                        <Users className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-foreground mb-2">自由交谈模式</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          不妨听听你喜欢的角色会怎么说
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
              
              {/* 传统分析模式提示 */}
              <div className="mt-8 text-center">
                <p className="text-sm text-muted-foreground">
                  或者继续使用{' '}
                  <button 
                    onClick={() => {
                      setShowWelcomeScreen(false)
                      // 显示传统输入框
                    }} 
                    className="text-primary hover:underline font-medium"
                  >
                    传统分析模式
                  </button>
                </p>
              </div>
            </div>
          </div>
        ) : showWelcomeScreen && !isAuthenticated ? (
          // 未登录的欢迎界面 - 模式选择界面（与登录用户一致）
          <div className="flex flex-col items-center justify-center h-full bg-background">
            <div className="text-center max-w-5xl mx-auto px-6 py-12 w-full">
              <div className="mb-12">
                <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                  <MessageSquare className="h-12 w-12 text-white" />
                </div>
                <h2 className="text-3xl font-bold mb-3 text-foreground">
                  开始你的智能对话分析之旅
                </h2>
                <p className="text-lg text-muted-foreground mb-2 leading-relaxed">
                  选择你喜欢的模式开始使用
                </p>
              </div>

              {/* 模式选择卡片 - 大卡片带详细介绍 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
                {/* 卡片模式 */}
                <Card 
                  className="cursor-pointer hover:shadow-xl transition-all duration-300 hover:-translate-y-2 border-2 hover:border-purple-500/50 group relative overflow-hidden"
                  onClick={() => navigate('/card-mode')}
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-bl-full"></div>
                  <div className="relative p-6">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center group-hover:from-purple-500/30 group-hover:to-pink-500/30 transition-colors flex-shrink-0">
                        <Sparkles className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-foreground mb-2">卡片模式</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          像抽卡游戏一样，输入内容后点击"开始抽卡"，AI会生成一张精美的分析卡片。支持文本输入和图片识别，但不支持对话功能。
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* 自由交谈模式 */}
                <Card 
                  className="cursor-pointer hover:shadow-xl transition-all duration-300 hover:-translate-y-2 border-2 hover:border-blue-500/50 group relative overflow-hidden"
                  onClick={() => navigate('/chat-mode')}
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-bl-full"></div>
                  <div className="relative p-6">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center group-hover:from-blue-500/30 group-hover:to-cyan-500/30 transition-colors flex-shrink-0">
                        <Users className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-foreground mb-2">自由交谈模式</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          与有趣的AI角色进行多轮对话，每个角色都有独特的性格和语气。可以在聊天框旁选择和管理角色，支持生成分析卡片。
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
              
              {/* 传统分析模式提示 */}
              <div className="mt-8 text-center">
                <p className="text-sm text-muted-foreground">
                  或者继续使用{' '}
                  <button 
                    onClick={() => {
                      setShowWelcomeScreen(false)
                      // 显示传统输入框
                    }} 
                    className="text-primary hover:underline font-medium"
                  >
                    传统分析模式
                  </button>
                </p>
              </div>
            </div>
          </div>
        ) : (
          // 传统分析模式输入框（当用户点击"传统分析模式"时显示）
          <div className="flex flex-col items-center justify-center h-full bg-background">
            <div className="text-center max-w-4xl mx-auto px-6 py-12 w-full">
              <div className="mb-8">
                <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                  <MessageSquare className="h-12 w-12 text-white" />
                </div>
                <h2 className="text-3xl font-bold mb-3 text-foreground">
                  开始你的智能对话分析之旅
                </h2>
                <p className="text-lg text-muted-foreground mb-8 leading-relaxed">
                  上传聊天截图或直接输入文字内容，AI将为你进行多维度分析
                </p>
              </div>
              
              {/* 输入框紧跟在欢迎文字下方 */}
              <div className="w-full">
                {/* 豆包输入框 - 欢迎界面时更大更突出，按钮在底部 */}
                <div className="bg-card border border-input rounded-2xl px-6 py-4 shadow-lg focus-within:shadow-xl focus-within:border-ring transition-all min-h-[120px] flex flex-col">
                  {/* 输入框区域 */}
                  <div className="flex-1 mb-3">
                    <Textarea
                      ref={textareaRef}
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={handleKeyDown}
                      onCompositionStart={() => setIsComposing(true)}
                      onCompositionEnd={() => setIsComposing(false)}
                      placeholder="输入消息开始对话..."
                      className="min-h-[60px] max-h-[200px] resize-none border-0 bg-transparent p-0 text-lg placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 w-full"
                      disabled={isAnalyzing}
                    />
                  </div>
                  
                  {/* 底部按钮区域 */}
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    {/* 左侧功能按钮 */}
                    <div className="flex items-center gap-2">
                      <MultiImageUploader
                        onTextExtracted={(text) => setInputValue(text)}
                        disabled={isAnalyzing}
                      />
                      <FileUploader
                        disabled={isAnalyzing}
                      />
                    </div>
                    
                    {/* 右侧操作按钮 */}
                    <div className="flex items-center gap-2">
                      {/* 发送按钮 */}
                      <Button
                        onClick={handleSendMessage}
                        disabled={!inputValue.trim() || isAnalyzing || isComposing}
                        size="icon"
                        className="h-8 w-8 rounded-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:text-gray-500 transition-colors"
                        title="发送消息"
                      >
                        {isAnalyzing ? (
                          <Loader2 className="h-4 w-4 animate-spin text-white" />
                        ) : (
                          <Send className="h-4 w-4 text-white" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>


      {/* 输入区域 - 有消息时显示 */}
      {currentMessages.length > 0 && (
        <div className="p-4 bg-background border-t border">
          <div className="max-w-4xl mx-auto">
            {/* 豆包输入框 - 正常模式 */}
            <div className="flex items-center bg-card border border-input rounded-full px-4 py-3 shadow-sm focus-within:shadow-md focus-within:border-ring transition-all">
              {/* 左侧功能按钮 */}
              <div className="flex items-center gap-3 mr-3">
                <MultiImageUploader
                  onTextExtracted={(text) => setInputValue(text)}
                  disabled={isAnalyzing}
                />
                <FileUploader
                  disabled={isAnalyzing}
                />
              </div>
              
              {/* 输入框 */}
              <div className="flex-1">
                <Textarea
                  ref={textareaRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onCompositionStart={() => setIsComposing(true)}
                  onCompositionEnd={() => setIsComposing(false)}
                  placeholder="输入消息..."
                  className="min-h-[24px] max-h-[120px] resize-none border-0 bg-transparent p-0 text-base placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0"
                  disabled={isAnalyzing}
                />
              </div>
              
              {/* 右侧操作按钮 */}
              <div className="flex items-center gap-2 ml-3">
                {/* 当前模式显示 */}
                {(currentConversation?.context_mode || pendingContextMode) && (
                  <div className="px-2 py-1 bg-blue-50 text-blue-600 text-xs rounded-full border border-blue-200">
                    {(currentConversation?.context_mode || pendingContextMode) === 'work' ? '工作模式' :
                     (currentConversation?.context_mode || pendingContextMode) === 'intimate' ? '亲密模式' :
                     (currentConversation?.context_mode || pendingContextMode) === 'social' ? '社交模式' :
                     (currentConversation?.context_mode || pendingContextMode) === 'general' ? '通用模式' :
                     (currentConversation?.context_mode || pendingContextMode)}
                  </div>
                )}
                
                {/* 发送按钮 */}
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isAnalyzing || isComposing}
                  size="icon"
                  className="h-9 w-9 rounded-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:text-gray-500 transition-colors"
                  title="发送消息"
                >
                  {isAnalyzing ? (
                    <Loader2 className="h-5 w-5 animate-spin text-white" />
                  ) : (
                    <Send className="h-5 w-5 text-white" />
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { 
  Send, 
  Loader2,
  MessageSquare,
  Settings,
  Image as ImageIcon
} from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { conversationApi, chatApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import MessageList from './MessageList'
import ContextModeSelector from './ContextModeSelector'
import FileUploader from './FileUploader'
import MultiImageUploader from './MultiImageUploader'
import LoadingMessage from './LoadingMessage'
import { cn } from '@/lib/utils'

export default function ChatInterface() {
  const [inputValue, setInputValue] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const [showContextMode, setShowContextMode] = useState(false)
  const [pendingContextMode, setPendingContextMode] = useState<'general'|'work'|'intimate'|'social'>('general')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
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
    setError
  } = useChatStore()
  
  const { toast } = useToast()

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
        conversation = await conversationApi.createConversation({
          title: message.slice(0, 30) + (message.length > 30 ? '...' : ''),
          context_mode: 'general'
        })
        setCurrentConversation(conversation)
      }

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

      // 开始分析
      setAnalyzing(true)
      const response = await chatApi.analyzeChat({
        conversation_id: conversation.id,
        message: message,
        context_mode: conversation.context_mode
      })

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

      toast({
        title: "分析完成",
        description: "已生成分析结果和回复建议",
        duration: 2000
      })

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
    setInputValue('')
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
              ) : (
                <div className="flex items-center justify-center h-full bg-background">
                  <div className="text-center max-w-md p-8">
                    <div className="w-20 h-20 mx-auto mb-6 bg-blue-50 rounded-full flex items-center justify-center">
                      <MessageSquare className="h-10 w-10 text-blue-500" />
                    </div>
                    <h3 className="text-2xl font-semibold mb-4 text-foreground">开始新的对话</h3>
                    <p className="text-muted-foreground mb-8 leading-relaxed text-base">
                      上传聊天截图或直接输入文字内容，AI将为你进行多维度分析
                    </p>
                  </div>
                </div>
              )}
            </div>


      {/* 输入区域 - 完全复刻豆包 */}
      <div className="p-4 bg-background border-t border">
        <div className="max-w-4xl mx-auto">
          {/* 分析模式选择器 */}
          {showContextMode && (
            <div className="mb-3 p-4 bg-muted rounded-lg border">
              <div className="mb-3">
                <h4 className="text-sm font-medium text-foreground mb-2">选择分析模式</h4>
                <p className="text-xs text-muted-foreground">不同的模式会影响AI的分析重点和回复建议</p>
              </div>
              <ContextModeSelector
                selectedMode={currentConversation?.context_mode || pendingContextMode}
                onModeChange={(mode) => {
                  if (currentConversation) {
                    setCurrentConversation({ ...currentConversation, context_mode: mode })
                  } else {
                    setPendingContextMode(mode)
                  }
                  setShowContextMode(false)
                  toast({
                    title: "模式已选择",
                    description: `已切换到${mode === 'work' ? '工作' : mode === 'intimate' ? '亲密' : mode === 'social' ? '社交' : '通用'}模式`,
                    duration: 1000
                  })
                }}
              />
            </div>
          )}
          
          {/* 豆包输入框 - 完全复刻 */}
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
              
              {/* 设置按钮 */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowContextMode(!showContextMode)}
                disabled={isAnalyzing}
                className="h-9 w-9 p-0 text-muted-foreground hover:text-foreground hover:bg-accent rounded-full"
                title="选择分析模式"
              >
                <Settings className="h-5 w-5" />
              </Button>
              
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
    </div>
  )
}

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Message, useChatStore } from '@/store/chatStore'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
  User, 
  Bot, 
  Copy, 
  Check,
  Image as ImageIcon,
  Brain,
  RotateCcw,
  MessageSquare,
  Save,
  Loader2
} from 'lucide-react'
import { formatTime, copyToClipboard } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'
import AnalysisResultComponent from './AnalysisResult'
import { cardApi } from '@/services/api'

interface MessageItemProps {
  message: Message
  onRegenerateAnalysis?: (originalMessage: string) => void
}

export default function MessageItem({ message, onRegenerateAnalysis }: MessageItemProps) {
  const [copied, setCopied] = useState(false)
  const [isSavingCard, setIsSavingCard] = useState(false)
  const { toast } = useToast()
  const { currentConversation, currentMessages } = useChatStore()

  const handleCopy = async () => {
    try {
      await copyToClipboard(message.content)
      setCopied(true)
      toast({
        title: "已复制",
        description: "内容已复制到剪贴板",
        duration: 500  // 500毫秒后自动消失
      })
      setTimeout(() => setCopied(false), 500)
    } catch (error) {
      toast({
        title: "复制失败",
        description: "无法复制内容",
        variant: "destructive"
      })
    }
  }

  const handleSaveCard = async () => {
    if (!message.analysis_result || !currentConversation) {
      toast({
        title: "无法保存",
        description: "缺少分析结果或对话信息",
        variant: "destructive",
        duration: 3000
      })
      return
    }

    setIsSavingCard(true)
    
    try {
      // 找到对应的用户消息作为原始内容
      const userMessage = currentMessages.find(msg => 
        msg.role === 'user' && 
        msg.id < message.id
      )
      
      // 生成智能标题
      const intent = message.analysis_result.intent?.primary || '未知意图'
      const sentiment = message.analysis_result.sentiment?.overall || 'neutral'

      const title = `${intent}分析`
      const description = `基于${currentConversation.context_mode || 'general'}模式的AI分析结果`

      // 确保分析数据包含所有必需字段
      const analysisData = {
        intent: message.analysis_result.intent || { primary: '未知', confidence: 0 },
        sentiment: message.analysis_result.sentiment || { overall: 'neutral', intensity: 0 },
        tone: message.analysis_result.tone || { style: '一般', politeness: '一般' },
        relationship: message.analysis_result.relationship || { type: '未知', closeness: 0 },
        subtext: message.analysis_result.subtext || { hidden_meaning: '无', confidence: 0 },
        key_points: message.analysis_result.key_points || [],
        context_analysis: message.analysis_result.context_analysis || { situation: '未知', environment: '未知' }
      }

      // 确保回复建议包含所有必需字段
      const responseSuggestions = (message.analysis_metadata?.suggestions || []).map(suggestion => ({
        type: suggestion.type || 'general',
        title: suggestion.title || '回复建议',
        description: suggestion.description || suggestion.content || '建议回复',
        examples: suggestion.examples || [suggestion.content || '示例回复']
      }))

      await cardApi.createCard({
        title,
        description,
        original_content: userMessage?.content || message.content,
        analysis_data: analysisData,
        response_suggestions: responseSuggestions,
        context_mode: currentConversation.context_mode,
        conversation_id: currentConversation.id
      })

      toast({
        title: "保存成功",
        description: "分析结果已保存到分析卡片",
        duration: 500
      })
    } catch (error) {
      console.error('保存卡片失败:', error)
      toast({
        title: "保存失败",
        description: "无法保存分析结果到卡片",
        variant: "destructive",
        duration: 3000
      })
    } finally {
      setIsSavingCard(false)
    }
  }

  const isUser = message.role === 'user'
  const isAnalysis = message.message_type === 'analysis' || message.role === 'assistant'

  return (
    <div className={cn(
      "flex gap-3 mb-3",
      isUser ? "justify-end" : "justify-start"
    )}>
      {/* 头像 */}
      {!isUser && (
        <div className="flex-shrink-0">
          <div className={cn(
            "w-8 h-8 rounded-full flex items-center justify-center",
            isAnalysis ? "bg-purple-100 text-purple-600" : "bg-blue-100 text-blue-600"
          )}>
            {isAnalysis ? <Brain className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
          </div>
        </div>
      )}

      {/* 消息内容 */}
      <div className={cn(
        "flex flex-col gap-1",
        isUser ? "items-end max-w-[85%]" : "items-start max-w-[90%]"
      )}>
        <div className={cn(
          "px-4 py-3 rounded-2xl text-sm leading-relaxed max-w-full",
          isUser 
            ? "bg-blue-500 text-white rounded-br-sm" 
            : isAnalysis
            ? "bg-muted border text-foreground rounded-bl-sm"
            : "bg-muted text-foreground rounded-bl-sm"
        )}>
          <div className="space-y-2">
            {/* 图片内容 */}
            {message.image_url && (
              <div className="mb-2">
                <img 
                  src={message.image_url} 
                  alt="上传的图片"
                  className="max-w-full h-auto rounded-md"
                />
              </div>
            )}

            {/* OCR识别结果 */}
            {message.image_ocr_result && (
              <div className="mb-2 p-2 bg-muted rounded text-sm">
                <div className="flex items-center gap-1 mb-1">
                  <ImageIcon className="h-3 w-3" />
                  <span className="text-xs font-medium">识别结果：</span>
                </div>
                <p className="text-xs">{message.image_ocr_result}</p>
              </div>
            )}

            {/* 文本内容 */}
            {isAnalysis ? (
              <div className="break-words">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  className="prose prose-sm max-w-none prose-headings:text-foreground prose-p:text-foreground prose-strong:text-foreground prose-em:text-foreground"
                  components={{
                    h1: ({children}) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                    h2: ({children}) => <h2 className="text-base font-semibold mb-1">{children}</h2>,
                    h3: ({children}) => <h3 className="text-sm font-medium mb-1">{children}</h3>,
                    p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                    strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                    em: ({children}) => <em className="italic">{children}</em>,
                    ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                    ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                    li: ({children}) => <li className="text-sm">{children}</li>,
                    code: ({children}) => <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                    pre: ({children}) => <pre className="bg-muted p-2 rounded text-xs overflow-x-auto">{children}</pre>
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="whitespace-pre-wrap break-words">
                {message.content}
              </div>
            )}

            {/* 分析结果 */}
            {message.analysis_result && (
              <div className="mt-3">
                <AnalysisResultComponent
                  analysis={message.analysis_result}
                  suggestions={message.analysis_metadata?.suggestions || []}
                />
              </div>
            )}
          </div>
        </div>

        {/* 消息元信息 */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{formatTime(message.created_at)}</span>
          {message.source && (
            <span className="px-1 py-0.5 bg-muted rounded text-xs">
              {message.source === 'manual' ? '手动输入' : 
               message.source === 'ocr' ? '图片识别' : 
               message.source === 'ai_generated' ? 'AI生成' : message.source}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="h-3 w-3" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </Button>
        </div>

        {/* AI分析消息的操作按钮 */}
        {isAnalysis && (
          <div className="flex items-center gap-2 mt-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-3 text-xs text-foreground"
              onClick={() => {
                if (onRegenerateAnalysis) {
                  // 找到对应的用户消息
                  const userMessage = message.content.includes('分析结果摘要') ? 
                    '请重新分析上述内容' : message.content
                  onRegenerateAnalysis(userMessage)
                } else {
                  toast({
                    title: "功能暂不可用",
                    description: "重新分析功能正在开发中",
                    duration: 2000
                  })
                }
              }}
            >
              <RotateCcw className="h-3 w-3 mr-1 text-foreground" />
              重新分析
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-3 text-xs text-foreground"
              onClick={() => {
                // TODO: 实现继续对话功能
                toast({
                  title: "继续对话",
                  description: "可以继续提问或讨论分析结果",
                  duration: 2000
                })
              }}
            >
              <MessageSquare className="h-3 w-3 mr-1 text-foreground" />
              继续对话
            </Button>
            {message.analysis_result && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 px-3 text-xs text-foreground hover:bg-accent hover:text-accent-foreground"
                onClick={handleSaveCard}
                disabled={isSavingCard}
              >
                {isSavingCard ? (
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                ) : (
                  <Save className="h-3 w-3 mr-1 text-foreground" />
                )}
                保存卡片
              </Button>
            )}
          </div>
        )}
      </div>

      {/* 用户头像 */}
      {isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center">
            <User className="h-4 w-4" />
          </div>
        </div>
      )}
    </div>
  )
}

import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { Sparkles, Loader2 } from 'lucide-react'
import { cardApi, chatApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import MultiImageUploader from '@/components/Chat/MultiImageUploader'
import CardDrawAnimation from '@/components/CardMode/CardDrawAnimation'
import CardPreview from '@/components/Chat/CardPreview'

export default function CardModePage() {
  const [inputValue, setInputValue] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedCard, setGeneratedCard] = useState<any>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressText, setProgressText] = useState('')
  const [showAnimation, setShowAnimation] = useState(false)
  const { toast } = useToast()
  const navigate = useNavigate()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 自动调整输入框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [inputValue])

  const handleGenerateCard = async () => {
    if (isGenerating) return

    // 检查是否有输入内容
    if (!inputValue.trim()) {
      toast({
        title: "请输入内容",
        description: "请先输入文本或上传图片进行识别",
        variant: "destructive",
        duration: 2000
      })
      return
    }

    setIsGenerating(true)
    setProgress(0)
    setProgressText('准备生成卡片...')
    setShowAnimation(true)

    try {
      const chatContent = inputValue.trim()

      setProgress(20)
      setProgressText('AI正在分析内容...')
      
      // 直接分析，不创建对话
      const analysisResponse = await chatApi.analyzeChatCardMode({
        message: chatContent,
        context_mode: 'card_mode'
      })

      setProgress(60)
      setProgressText('正在生成精美卡片...')

      // 不保存到数据库，只在前端生成卡片数据
      const cardData = {
        id: Date.now(), // 临时ID
        title: `${analysisResponse.analysis.intent?.primary || '分析'}卡片`,
        description: '卡片模式生成的分析卡片',
        original_content: chatContent,
        analysis_data: analysisResponse.analysis,
        response_suggestions: analysisResponse.suggestions,
        context_mode: 'card_mode',
        conversation_id: null, // 卡片模式不关联对话
        is_temporary: true // 标记为临时卡片
      }

      setProgress(90)
      setProgressText('卡片生成完成！')

      setProgress(100)
      setProgressText('卡片已就绪！')
      
      // 等待动画完成阶段（给用户看到完成效果）
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // 关闭动画
      setShowAnimation(false)
      
      // 等待动画关闭后再显示卡片
      await new Promise(resolve => setTimeout(resolve, 300))
      
      setGeneratedCard(cardData)
      
      // 不清空输入，允许用户重新生成

      toast({
        title: "卡片生成成功！",
        description: "点击保存卡片按钮保存到卡片库",
        duration: 2000
      })

      // 延迟重置进度
      setTimeout(() => {
        setProgress(0)
        setProgressText('')
      }, 500)
    } catch (error: any) {
      console.error('生成卡片失败:', error)
      setShowAnimation(false)
      toast({
        title: "生成失败",
        description: error.response?.data?.detail || error.message || "无法生成卡片，请重试",
        variant: "destructive",
        duration: 3000
      })
      setProgress(0)
      setProgressText('')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSaveCard = async () => {
    if (!generatedCard) return

    try {
      setIsSaving(true)
      
      // 真正保存卡片到数据库（不关联对话）
      const cardResponse = await cardApi.createCard({
        title: generatedCard.title,
        description: generatedCard.description,
        original_content: generatedCard.original_content,
        analysis_data: generatedCard.analysis_data,
        response_suggestions: generatedCard.response_suggestions,
        context_mode: generatedCard.context_mode,
        conversation_id: null // 卡片模式不关联对话
      })

      toast({
        title: "卡片已保存",
        description: "卡片已保存到你的卡片库",
        duration: 2000
      })
      
      // 跳转到卡片列表
      setTimeout(() => {
        navigate('/cards')
      }, 500)
    } catch (error: any) {
      console.error('保存卡片失败:', error)
      toast({
        title: "保存失败",
        description: error.response?.data?.detail || "无法保存卡片，请重试",
        variant: "destructive"
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleRegenerateCard = async () => {
    if (isRegenerating || isGenerating) return
    
    try {
      setIsRegenerating(true)
      // 保留输入内容和卡片，重新生成时会自动更新
      await handleGenerateCard()
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleNewCard = () => {
    setGeneratedCard(null)
    setInputValue('')
    setProgress(0)
    setProgressText('')
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* 抽卡动画 */}
      <CardDrawAnimation 
        isActive={showAnimation}
        progressText={progressText}
        onComplete={() => {
          // 动画完成后的回调
        }}
      />

      <div className="flex-1 flex flex-col items-center justify-center p-4">
        {!generatedCard ? (
          <div className="w-full max-w-3xl">
            {/* 标题 */}
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold text-foreground mb-2">
                卡片模式
              </h1>
              <p className="text-muted-foreground">
                输入想要的内容，抽一张机会卡吧 ✨
              </p>
            </div>

            {/* 豆包风格输入框 */}
            <div className="bg-card border border-input rounded-2xl px-6 py-4 shadow-lg focus-within:shadow-xl focus-within:border-ring transition-all min-h-[200px] flex flex-col">
              {/* 输入框区域 */}
              <div className="flex-1 mb-3">
                <Textarea
                  ref={textareaRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="输入你想要分析的聊天内容，或粘贴文字..."
                  className="min-h-[120px] max-h-[300px] resize-none border-0 bg-transparent p-0 text-lg placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 w-full"
                  disabled={isGenerating}
                />
              </div>
              
              {/* 底部按钮区域 */}
              <div className="flex items-center justify-between pt-3 border-t border-border/50">
                {/* 左侧功能按钮 */}
                <div className="flex items-center gap-2">
                  <MultiImageUploader
                    onTextExtracted={(text) => {
                      setInputValue(prev => prev ? `${prev}\n\n${text}` : text)
                    }}
                    disabled={isGenerating}
                  />
                </div>
                
                {/* 右侧操作按钮 */}
                <div className="flex items-center gap-2">
                  {/* 进度提示 */}
                  {isGenerating && (
                    <div className="flex items-center gap-2 mr-2 min-w-[200px]">
                      <span className="text-xs text-muted-foreground whitespace-nowrap">{progressText}</span>
                      <Progress value={progress} className="flex-1 h-1.5" />
                      <span className="text-xs text-muted-foreground whitespace-nowrap">{progress}%</span>
                    </div>
                  )}
                  
                  {/* 开始抽卡按钮 */}
                  <Button
                    onClick={handleGenerateCard}
                    disabled={!inputValue.trim() || isGenerating}
                    size="icon"
                    className="h-8 w-8 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:bg-gray-300 disabled:text-gray-500 transition-colors"
                    title="开始抽卡"
                  >
                    {isGenerating ? (
                      <Loader2 className="h-4 w-4 animate-spin text-white" />
                    ) : (
                      <Sparkles className="h-4 w-4 text-white" />
                    )}
                  </Button>
                </div>
              </div>
            </div>

            {/* 提示文字 */}
            <div className="mt-4 text-center">
              <p className="text-sm text-muted-foreground">
                支持文本输入和图片识别，点击 ✨ 按钮开始抽卡
              </p>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-3xl space-y-6">
            {/* 使用CardPreview组件展示卡片 */}
            {generatedCard && (
              <CardPreview
                card={{
                  id: generatedCard.id || 0,
                  title: generatedCard.title,
                  description: generatedCard.description,
                  original_content: generatedCard.original_content,
                  analysis_data: generatedCard.analysis_data,
                  response_suggestions: generatedCard.response_suggestions,
                  context_mode: generatedCard.context_mode,
                  created_at: generatedCard.created_at
                }}
                onSave={handleSaveCard}
                onRegenerate={handleRegenerateCard}
                onContinue={handleNewCard}
                isSaving={isSaving}
                isRegenerating={isRegenerating}
              />
            )}

            {/* 底部操作按钮 - 抽新卡 */}
            <div className="flex gap-3 justify-center">
              <Button
                onClick={handleNewCard}
                variant="outline"
                className="h-12 px-6"
              >
                <Sparkles className="mr-2 h-4 w-4" />
                抽新卡
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

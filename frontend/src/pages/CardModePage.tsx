import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { Sparkles, Loader2, Eye, Save, RefreshCw } from 'lucide-react'
import { cardApi, chatApi, conversationApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import AnalysisResultComponent from '@/components/Chat/AnalysisResult'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import MultiImageUploader from '@/components/Chat/MultiImageUploader'
import CardDrawAnimation from '@/components/CardMode/CardDrawAnimation'
import { cn } from '@/lib/utils'

export default function CardModePage() {
  const [inputValue, setInputValue] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedCard, setGeneratedCard] = useState<any>(null)
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
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
      setIsGenerating(true)
      
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
      setIsGenerating(false)
    }
  }

  const handleRegenerateCard = async () => {
    setGeneratedCard(null)
    // 保留输入内容，重新生成
    handleGenerateCard()
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
            {/* 卡片展示 - 精美设计 */}
            <Card className="border-0 shadow-2xl bg-gradient-to-br from-purple-50/50 via-pink-50/30 to-blue-50/50 dark:from-purple-950/20 dark:via-pink-950/10 dark:to-blue-950/20 overflow-hidden relative">
              {/* 装饰性背景元素 */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-purple-400/10 to-pink-400/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
              <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-blue-400/10 to-cyan-400/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2"></div>
              
              <CardContent className="p-8 relative z-10">
                {/* 标题区域 */}
                <div className="mb-8">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900/30 dark:to-pink-900/30 mb-4">
                    <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-xs font-semibold text-purple-700 dark:text-purple-300">卡片模式</span>
                  </div>
                  <h2 className="text-4xl font-bold text-foreground mb-3 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                    {generatedCard.title}
                  </h2>
                  {generatedCard.description && (
                    <p className="text-muted-foreground text-lg">{generatedCard.description}</p>
                  )}
                </div>

                {/* 分析结果预览 - 精美设计 */}
                {generatedCard.analysis_data && (
                  <div className="mt-6 p-6 rounded-2xl bg-white/60 dark:bg-black/20 backdrop-blur-sm border border-purple-200/50 dark:border-purple-800/50 shadow-lg">
                    <div className="flex items-center gap-2 mb-5">
                      <div className="w-2 h-2 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 animate-pulse"></div>
                      <h4 className="text-lg font-semibold text-foreground">AI分析结果</h4>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl bg-gradient-to-br from-purple-50 to-purple-100/50 dark:from-purple-950/30 dark:to-purple-900/20 border border-purple-200/50 dark:border-purple-800/30 hover:shadow-md transition-shadow">
                        <div className="text-xs font-medium text-purple-600 dark:text-purple-400 mb-2 uppercase tracking-wide">意图</div>
                        <div className="text-lg font-bold text-purple-900 dark:text-purple-100">
                          {generatedCard.analysis_data.intent?.primary || '未知'}
                        </div>
                      </div>
                      <div className={cn(
                        "p-4 rounded-xl border hover:shadow-md transition-shadow",
                        generatedCard.analysis_data.sentiment?.overall === 'positive' 
                          ? "bg-gradient-to-br from-green-50 to-emerald-100/50 dark:from-green-950/30 dark:to-emerald-900/20 border-green-200/50 dark:border-green-800/30"
                          : generatedCard.analysis_data.sentiment?.overall === 'negative'
                          ? "bg-gradient-to-br from-red-50 to-rose-100/50 dark:from-red-950/30 dark:to-rose-900/20 border-red-200/50 dark:border-red-800/30"
                          : "bg-gradient-to-br from-gray-50 to-slate-100/50 dark:from-gray-950/30 dark:to-slate-900/20 border-gray-200/50 dark:border-gray-800/30"
                      )}>
                        <div className={cn(
                          "text-xs font-medium mb-2 uppercase tracking-wide",
                          generatedCard.analysis_data.sentiment?.overall === 'positive'
                            ? "text-green-600 dark:text-green-400"
                            : generatedCard.analysis_data.sentiment?.overall === 'negative'
                            ? "text-red-600 dark:text-red-400"
                            : "text-gray-600 dark:text-gray-400"
                        )}>情感</div>
                        <div className={cn(
                          "text-lg font-bold",
                          generatedCard.analysis_data.sentiment?.overall === 'positive'
                            ? "text-green-900 dark:text-green-100"
                            : generatedCard.analysis_data.sentiment?.overall === 'negative'
                            ? "text-red-900 dark:text-red-100"
                            : "text-gray-900 dark:text-gray-100"
                        )}>
                          {generatedCard.analysis_data.sentiment?.overall === 'positive' ? '积极' : 
                           generatedCard.analysis_data.sentiment?.overall === 'negative' ? '消极' : '中性'}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 操作按钮 */}
                <div className="mt-8 flex gap-3">
                  <Button
                    onClick={() => setViewDialogOpen(true)}
                    variant="outline"
                    className="flex-1 h-12 border-2 hover:bg-purple-50 dark:hover:bg-purple-950/30 hover:border-purple-300 dark:hover:border-purple-700 transition-all"
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    查看详情
                  </Button>
                  <Button
                    onClick={handleSaveCard}
                    className="flex-1 h-12 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg hover:shadow-xl transition-all"
                  >
                    <Save className="mr-2 h-4 w-4" />
                    保存卡片
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* 底部操作按钮 */}
            <div className="flex gap-3 justify-center">
              <Button
                onClick={handleRegenerateCard}
                variant="outline"
                disabled={isGenerating}
                className="h-12 px-6"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                重新生成
              </Button>
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

      {/* 查看详情弹窗 */}
      {generatedCard && (
        <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">
                {generatedCard.title}
              </DialogTitle>
              <DialogDescription>
                分析卡片详细信息
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {generatedCard.analysis_data && (
                <AnalysisResultComponent
                  analysis={generatedCard.analysis_data}
                  suggestions={generatedCard.response_suggestions || []}
                />
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}

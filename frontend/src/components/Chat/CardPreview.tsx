import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Eye, 
  Save, 
  RefreshCw, 
  X,
  Sparkles,
  Loader2,
  Star,
  Zap
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import AnalysisResultComponent from '@/components/Chat/AnalysisResult'

interface CardPreviewProps {
  card: {
    id: number
    title: string
    description?: string
    original_content: string
    analysis_data: any
    response_suggestions?: any[]
    context_mode?: string
    created_at?: string
  }
  onSave: () => void
  onRegenerate: () => void
  onContinue: () => void
  onExport?: () => void
  isSaving?: boolean
  isRegenerating?: boolean
}

// 根据情绪获取卡片颜色配置
function getSentimentConfig(analysisData: any) {
  if (!analysisData) {
    return {
      gradient: 'from-gray-400 via-gray-500 to-gray-600',
      border: 'border-gray-400/50',
      glow: 'shadow-[0_0_15px_rgba(156,163,175,0.3)]',
      label: '中性',
      labelColor: 'text-gray-300',
      bgPattern: 'bg-gradient-to-br from-gray-500/20 via-gray-500/20 to-gray-600/20'
    }
  }
  
  const sentiment = analysisData.sentiment?.overall || 'neutral'
  
  switch (sentiment) {
    case 'positive':
      return {
        gradient: 'from-green-400 via-emerald-500 to-teal-500',
        border: 'border-green-400/50',
        glow: 'shadow-[0_0_30px_rgba(34,197,94,0.6)]',
        label: '积极',
        labelColor: 'text-green-300',
        bgPattern: 'bg-gradient-to-br from-green-500/20 via-emerald-500/20 to-teal-500/20'
      }
    case 'negative':
      return {
        gradient: 'from-red-400 via-rose-500 to-pink-500',
        border: 'border-red-400/50',
        glow: 'shadow-[0_0_30px_rgba(239,68,68,0.6)]',
        label: '消极',
        labelColor: 'text-red-300',
        bgPattern: 'bg-gradient-to-br from-red-500/20 via-rose-500/20 to-pink-500/20'
      }
    default:
      return {
        gradient: 'from-blue-400 via-cyan-500 to-sky-500',
        border: 'border-blue-400/50',
        glow: 'shadow-[0_0_20px_rgba(59,130,246,0.4)]',
        label: '中性',
        labelColor: 'text-blue-300',
        bgPattern: 'bg-gradient-to-br from-blue-500/20 via-cyan-500/20 to-sky-500/20'
      }
  }
}

export default function CardPreview({
  card,
  onSave,
  onRegenerate,
  onContinue,
  onExport,
  isSaving = false,
  isRegenerating = false
}: CardPreviewProps) {
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [isRevealing, setIsRevealing] = useState(true)
  
  const sentimentConfig = getSentimentConfig(card.analysis_data)

  // 卡片揭示动画
  useEffect(() => {
    const timer = setTimeout(() => setIsRevealing(false), 1000)
    return () => clearTimeout(timer)
  }, [])

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'bg-green-500/20 border-green-400/50 text-green-300'
      case 'negative':
        return 'bg-red-500/20 border-red-400/50 text-red-300'
      default:
        return 'bg-gray-500/20 border-gray-400/50 text-gray-300'
    }
  }

  const getSentimentText = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return '积极'
      case 'negative':
        return '消极'
      default:
        return '中性'
    }
  }

  return (
    <>
      {/* 游戏风格卡片 */}
      <div className={cn(
        "mt-6 relative w-full max-w-md mx-auto",
        "transform transition-all duration-1000",
        isRevealing ? "scale-95 opacity-0" : "scale-100 opacity-100 animate-card-reveal"
      )}>
        {/* 卡片主体 - 3D效果 */}
        <div className={cn(
          "relative aspect-[2/3] rounded-2xl overflow-hidden",
          "border-4", sentimentConfig.border,
          sentimentConfig.glow,
          "transform perspective-1000 preserve-3d",
          "hover:scale-105 transition-transform duration-300",
          "bg-gradient-to-br", sentimentConfig.bgPattern
        )}>
          {/* 背景光效 */}
          <div className="absolute inset-0">
            <div className={cn(
              "absolute inset-0 bg-gradient-to-br",
              sentimentConfig.gradient,
              "opacity-30 animate-pulse"
            )} />
            {/* 闪光效果 */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
          </div>

          {/* 顶部装饰 */}
          <div className="absolute top-0 left-0 right-0 h-20 bg-gradient-to-b from-black/40 to-transparent">
            {/* 情绪标签 */}
            <div className={cn(
              "absolute top-3 right-3 px-3 py-1 rounded-full",
              "bg-black/60 backdrop-blur-sm border-2",
              sentimentConfig.border
            )}>
              <span className={cn("text-xs font-bold", sentimentConfig.labelColor)}>
                {sentimentConfig.label}
              </span>
            </div>
            
            {/* 星星装饰 */}
            <div className="absolute top-3 left-3">
              <Star className="w-5 h-5 text-yellow-400/60 animate-pulse" fill="currentColor" />
            </div>
          </div>

          {/* 卡片内容 */}
          <div className="relative z-10 h-full flex flex-col p-6 text-white">
            {/* 标题区域 */}
            <div className="mb-4 mt-12">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-yellow-400" />
                <span className="text-xs font-semibold text-white/80 uppercase tracking-wider">
                  沟通分析卡片
                </span>
              </div>
              <h3 className="text-xl font-bold mb-1 line-clamp-2 drop-shadow-lg">
                {card.title}
              </h3>
              {card.description && (
                <p className="text-xs text-white/70 line-clamp-2">{card.description}</p>
              )}
            </div>

            {/* 分析摘要 - 游戏风格 */}
            {card.analysis_data && (
              <div className="flex-1 space-y-3">
                {/* 意图 */}
                <div className="bg-black/30 backdrop-blur-sm rounded-lg p-3 border border-white/10">
                  <div className="flex items-center gap-2 mb-1">
                    <Zap className="w-3 h-3 text-yellow-400" />
                    <span className="text-xs font-medium text-white/80 uppercase">意图</span>
                  </div>
                  <div className="text-sm font-bold text-white">
                    {card.analysis_data.intent?.primary || '未知'}
                  </div>
                </div>

                {/* 情感 */}
                <div className={cn(
                  "backdrop-blur-sm rounded-lg p-3 border",
                  getSentimentColor(card.analysis_data.sentiment?.overall || 'neutral')
                )}>
                  <div className="flex items-center gap-2 mb-1">
                    <Star className="w-3 h-3" />
                    <span className="text-xs font-medium uppercase">情感</span>
                  </div>
                  <div className="text-sm font-bold">
                    {getSentimentText(card.analysis_data.sentiment?.overall || 'neutral')}
                  </div>
                </div>

                {/* 关键点 */}
                {card.analysis_data.key_points && card.analysis_data.key_points.length > 0 && (
                  <div className="bg-black/30 backdrop-blur-sm rounded-lg p-3 border border-white/10">
                    <div className="text-xs font-medium text-white/80 mb-2 uppercase">关键点</div>
                    <div className="flex flex-wrap gap-1">
                      {card.analysis_data.key_points.slice(0, 3).map((point: string, index: number) => (
                        <Badge 
                          key={index} 
                          variant="outline" 
                          className="text-[10px] px-2 py-0.5 bg-white/10 border-white/20 text-white/90"
                        >
                          {point}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 底部操作按钮 */}
            <div className="mt-4 pt-4 border-t border-white/20 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={() => setViewDialogOpen(true)}
                  variant="outline"
                  size="sm"
                  className="bg-white/10 border-white/20 text-white hover:bg-white/20 text-xs"
                >
                  <Eye className="w-3 h-3 mr-1" />
                  详情
                </Button>
                <Button
                  onClick={onSave}
                  disabled={isSaving}
                  size="sm"
                  className={cn(
                    "bg-gradient-to-r text-white text-xs",
                    sentimentConfig.gradient,
                    "hover:opacity-90"
                  )}
                >
                  {isSaving ? (
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  ) : (
                    <Save className="w-3 h-3 mr-1" />
                  )}
                  保存
                </Button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={onRegenerate}
                  disabled={isRegenerating}
                  variant="outline"
                  size="sm"
                  className="bg-white/10 border-white/20 text-white hover:bg-white/20 text-xs"
                >
                  {isRegenerating ? (
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3 h-3 mr-1" />
                  )}
                  重抽
                </Button>
                <Button
                  onClick={onContinue}
                  variant="outline"
                  size="sm"
                  className="bg-white/10 border-white/20 text-white hover:bg-white/20 text-xs"
                >
                  <X className="w-3 h-3 mr-1" />
                  继续
                </Button>
              </div>
            </div>
          </div>

          {/* 底部光效 */}
          <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-black/40 to-transparent" />
        </div>

        {/* 卡片光晕效果 */}
        <div className={cn(
          "absolute -inset-4 rounded-3xl blur-2xl opacity-50 -z-10",
          "bg-gradient-to-br", sentimentConfig.gradient,
          "animate-pulse"
        )} />
      </div>

      {/* 查看详情弹窗 */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold">
              {card.title}
            </DialogTitle>
            <DialogDescription>
              分析卡片详细信息
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {card.analysis_data && (
              <AnalysisResultComponent
                analysis={card.analysis_data}
                suggestions={card.response_suggestions || []}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

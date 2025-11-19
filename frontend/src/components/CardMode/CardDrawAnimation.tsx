import { useEffect, useState, useRef } from 'react'
import { Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CardDrawAnimationProps {
  isActive: boolean
  progressText?: string
  onComplete?: () => void
}

export default function CardDrawAnimation({ isActive, progressText, onComplete }: CardDrawAnimationProps) {
  const [stage, setStage] = useState<'idle' | 'drawing' | 'revealing' | 'complete'>('idle')
  const [currentTextIndex, setCurrentTextIndex] = useState(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const prevActiveRef = useRef(false)
  const textScrollTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 轮播文字列表
  const scrollTexts = [
    '正在识别内容...',
    '正在理解语义...',
    '正在分析情感...',
    '正在提取关键信息...',
    '正在生成分析结果...',
    '正在制作精美卡片...'
  ]

  // 文字轮播效果
  useEffect(() => {
    if (isActive && (stage === 'drawing' || stage === 'revealing')) {
      // 启动文字轮播
      textScrollTimerRef.current = setInterval(() => {
        setCurrentTextIndex((prev) => (prev + 1) % scrollTexts.length)
      }, 2000) // 每2秒切换一次文字

      return () => {
        if (textScrollTimerRef.current) {
          clearInterval(textScrollTimerRef.current)
          textScrollTimerRef.current = null
        }
      }
    } else {
      // 停止文字轮播
      if (textScrollTimerRef.current) {
        clearInterval(textScrollTimerRef.current)
        textScrollTimerRef.current = null
      }
      setCurrentTextIndex(0)
    }
  }, [isActive, stage, scrollTexts.length])

  useEffect(() => {
    // 清理之前的定时器
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }

    // 如果从非激活状态变为激活状态
    if (isActive && !prevActiveRef.current) {
      // 动画激活时，立即进入drawing阶段
      setStage('drawing')
      setCurrentTextIndex(0)
      // 1秒后进入revealing阶段，并保持在revealing阶段
      timerRef.current = setTimeout(() => {
        setStage('revealing')
      }, 1000)
    }
    // 如果从激活状态变为非激活状态
    else if (!isActive && prevActiveRef.current) {
      // 当isActive变为false时，先进入complete阶段显示完成效果
      if (stage === 'drawing' || stage === 'revealing') {
        setStage('complete')
        // 完成阶段持续一段时间后关闭
        timerRef.current = setTimeout(() => {
          setStage('idle')
          onComplete?.()
        }, 800)
      }
    }

    prevActiveRef.current = isActive

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [isActive, onComplete, stage])

  if (!isActive) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-md px-8">
        {/* 卡片容器 */}
        <div className="relative aspect-[3/4] w-full">
          {/* 背景光效 */}
          <div className={cn(
            "absolute inset-0 rounded-2xl transition-all duration-1000",
            stage === 'drawing' && "bg-gradient-to-br from-purple-500/20 via-pink-500/20 to-blue-500/20 animate-pulse",
            stage === 'revealing' && "bg-gradient-to-br from-purple-500/40 via-pink-500/40 to-blue-500/40",
            stage === 'complete' && "bg-gradient-to-br from-purple-500/60 via-pink-500/60 to-blue-500/60"
          )}>
            {/* 闪光效果 */}
            {stage === 'revealing' && (
              <>
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-400/50 via-pink-400/50 to-blue-400/50 animate-pulse" />
              </>
            )}
          </div>

          {/* 卡片内容 */}
          <div className={cn(
            "absolute inset-0 rounded-2xl border-2 border-white/20 bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900/30 dark:to-pink-900/30 flex flex-col items-center justify-center p-8 transition-all duration-1000",
            stage === 'drawing' && "scale-95 opacity-100",
            stage === 'revealing' && "scale-100 opacity-100",
            stage === 'complete' && "scale-105 opacity-100"
          )}>
            {/* 星星装饰 */}
            <div className="absolute inset-0 overflow-hidden rounded-2xl">
              {[...Array(20)].map((_, i) => {
                const size = 12 + Math.random() * 8
                return (
                  <Sparkles
                    key={i}
                    className={cn(
                      "absolute text-purple-400/30 animate-pulse",
                      (stage === 'revealing' || stage === 'complete') && "text-purple-400/60"
                    )}
                    style={{
                      left: `${Math.random() * 100}%`,
                      top: `${Math.random() * 100}%`,
                      animationDelay: `${Math.random() * 2}s`,
                      animationDuration: `${1 + Math.random() * 2}s`,
                      width: `${size}px`,
                      height: `${size}px`
                    }}
                  />
                )
              })}
            </div>

            {/* 中心图标 */}
            <div className={cn(
              "relative z-10 transition-all duration-1000",
              stage === 'drawing' && "scale-100 opacity-100 animate-pulse",
              stage === 'revealing' && "scale-110 opacity-100 animate-bounce",
              stage === 'complete' && "scale-100"
            )}>
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-2xl">
                <Sparkles className="w-12 h-12 text-white" />
              </div>
            </div>

            {/* 文字提示 */}
            <div className={cn(
              "mt-8 text-center transition-all duration-1000 relative z-10",
              stage === 'drawing' && "opacity-100 translate-y-0",
              stage === 'revealing' && "opacity-100 translate-y-0",
              stage === 'complete' && "opacity-100"
            )}>
              <h3 className="text-2xl font-bold text-white mb-2">
                {stage === 'complete' ? '抽卡成功！' : '正在抽卡...'}
              </h3>
              <div className="text-white/80 text-base min-h-[24px] flex items-center justify-center">
                {stage === 'complete' ? (
                  <p>恭喜获得新卡片！</p>
                ) : (
                  <p className="animate-fade-in">
                    {progressText || scrollTexts[currentTextIndex]}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 进度条 */}
        <div className="mt-8">
          <div className="h-1 bg-white/20 rounded-full overflow-hidden">
            <div className={cn(
              "h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300",
              stage === 'drawing' && "w-1/3",
              stage === 'revealing' && "w-2/3",
              stage === 'complete' && "w-full"
            )} />
          </div>
        </div>
      </div>
    </div>
  )
}


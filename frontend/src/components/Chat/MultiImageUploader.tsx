import { useState, useRef, useCallback, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { 
  Image as ImageIcon, 
  X,
  Loader2,
  Check,
  Eye,
  Download,
  Zap,
  Sparkles,
  Plus
} from 'lucide-react'
import { chatApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

// 动态OCR处理文本组件
function OCRProcessingText() {
  const [currentText, setCurrentText] = useState(0)
  const texts = ["正在识别图片", "正在解析文字", "正在整理结果"]

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentText(prev => (prev + 1) % texts.length)
    }, 1800)
    return () => clearInterval(interval)
  }, [])

  return (
    <span className="inline-block min-h-[2rem]">
      {texts[currentText]}
      <span className="animate-pulse">...</span>
    </span>
  )
}

// 动态OCR处理描述组件
function OCRProcessingDescription() {
  const [currentDesc, setCurrentDesc] = useState(0)
  const descriptions = [
    "请稍候，AI正在处理...",
    "正在努力识别关键信息...",
    "马上就好，别走开~"
  ]

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentDesc(prev => (prev + 1) % descriptions.length)
    }, 2200)
    return () => clearInterval(interval)
  }, [])

  return (
    <span className="inline-block min-h-[1.5rem]">
      {descriptions[currentDesc]}
    </span>
  )
}

// 智能解析聊天对话段落
function parseChatSegments(text: string, imageId: string, imageIndex: number): TextSegment[] {
  if (!text.trim()) return []

  // 清理文本
  let cleanText = text.trim()
  
  // 常见的对话分隔符模式
  const dialoguePatterns = [
    // 时间戳模式: [时间] 或 时间:
    /(\d{1,2}:\d{2}|\d{1,2}月\d{1,2}日|\d{4}-\d{2}-\d{2})/g,
    // 用户名模式: 用户名: 或 用户名：
    /([^:\n]+[：:])/g,
    // 消息气泡模式: 常见的聊天应用格式
    /(.*?)(?=\n\s*(?:\d{1,2}:\d{2}|[^:\n]+[：:]|$))/g,
    // 长文本的自然分段点
    /([.!?。！？])\s*\n/g
  ]

  let segments: string[] = []
  
  // 首先尝试按时间戳分割
  const timeMatches = cleanText.match(/(\d{1,2}:\d{2}[^\n]*)/g)
  if (timeMatches && timeMatches.length > 1) {
    segments = cleanText.split(/(\d{1,2}:\d{2}[^\n]*)/).filter(s => s.trim().length > 0)
  } else {
    // 尝试按用户名分割
    const userMatches = cleanText.match(/[^:\n]+[：:]/g)
    if (userMatches && userMatches.length > 1) {
      segments = cleanText.split(/([^:\n]+[：:])/).filter(s => s.trim().length > 0)
    } else {
      // 按换行分割，但合并过短的段落
      const lines = cleanText.split('\n').filter(line => line.trim().length > 0)
      segments = []
      let currentSegment = ''
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim()
        
        // 如果当前行很短（少于10个字符），且下一行也很短，则合并
        if (line.length < 10 && i < lines.length - 1 && lines[i + 1].trim().length < 10) {
          currentSegment += (currentSegment ? ' ' : '') + line
        } else {
          currentSegment += (currentSegment ? ' ' : '') + line
          if (currentSegment.length > 5) { // 只保留有意义的段落
            segments.push(currentSegment)
            currentSegment = ''
          }
        }
      }
      
      if (currentSegment.trim().length > 5) {
        segments.push(currentSegment)
      }
    }
  }

  // 进一步优化段落
  const optimizedSegments = segments
    .map(segment => segment.trim())
    .filter(segment => segment.length > 3) // 过滤掉太短的段落
    .map((segment, index) => {
      // 检测是否是用户名开头
      const isUserStart = /^[^:\n]+[：:]/.test(segment)
      const displayText = isUserStart ? segment : segment
      
      return {
        id: `${imageId}-${index}`,
        text: displayText,
        selected: true,
        source: `图片 ${imageIndex}`
      }
    })

  return optimizedSegments
}

interface ImageFile {
  id: string
  file: File
  preview: string
  ocrResult?: {
    text: string
    confidence: number
    language: string
  }
  isProcessing?: boolean
  error?: string
}

interface TextSegment {
  id: string
  text: string
  selected: boolean
  source: string
  speakerSide?: 'left' | 'right'
  speakerName?: string
}

interface MultiImageUploaderProps {
  onTextExtracted?: (text: string) => void
  disabled?: boolean
}

export default function MultiImageUploader({ onTextExtracted, disabled }: MultiImageUploaderProps) {
  const [images, setImages] = useState<ImageFile[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [showTextSelection, setShowTextSelection] = useState(false)
  const [textSegments, setTextSegments] = useState<TextSegment[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const [ocrMode, setOcrMode] = useState<'fast' | 'quality'>('fast')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()

  // 轻量压缩：>1.5MB 时压到 webp，最长边 1400，质量 0.82
  const compressImage = useCallback(async (file: File): Promise<File> => {
    const SHOULD_COMPRESS_BYTES = 1.5 * 1024 * 1024
    if (!file.type.startsWith('image/') || file.size <= SHOULD_COMPRESS_BYTES) return file

    return new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        const maxSize = 1400
        let { width, height } = img
        let targetW = width
        let targetH = height
        if (width > height && width > maxSize) {
          targetW = maxSize
          targetH = Math.round((height / width) * maxSize)
        } else if (height >= width && height > maxSize) {
          targetH = maxSize
          targetW = Math.round((width / height) * maxSize)
        }
        const canvas = document.createElement('canvas')
        canvas.width = targetW
        canvas.height = targetH
        const ctx = canvas.getContext('2d')!
        ctx.drawImage(img, 0, 0, targetW, targetH)
        canvas.toBlob((blob) => {
          if (blob) {
            resolve(new File([blob], file.name.replace(/\.[^.]+$/, '.webp'), { type: 'image/webp' }))
          } else {
            resolve(file)
          }
        }, 'image/webp', 0.82)
      }
      img.onerror = () => resolve(file)
      const reader = new FileReader()
      reader.onload = (e) => { img.src = String(e.target?.result) }
      reader.readAsDataURL(file)
    })
  }, [])

  // 处理文件选择（含并行压缩）
  const handleFileSelect = useCallback(async (files: FileList) => {
    const candidates = Array.from(files).filter((f) => f.type.startsWith('image/') && f.size <= 20 * 1024 * 1024)
    if (candidates.length === 0) {
      toast({
        title: '选择失败',
        description: '请选择有效的图片文件（支持JPG、PNG、GIF、WebP，大小不超过20MB）',
        variant: 'destructive',
        duration: 3000,
      })
      return
    }

    const prepared = await Promise.all(
      candidates.map(async (file) => {
        const id = Math.random().toString(36).substr(2, 9)
        const optimized = await compressImage(file)
        const preview = URL.createObjectURL(optimized)
        return { id, file: optimized, preview, isProcessing: false } as ImageFile
      })
    )

    setImages((prev) => [...prev, ...prepared])
  }, [compressImage, toast])

  // 处理文件输入变化
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelect(files)
    }
    e.target.value = ''
  }, [handleFileSelect])

  // 移除图片
  const removeImage = useCallback((id: string) => {
    setImages(prev => {
      const image = prev.find(img => img.id === id)
      if (image) {
        URL.revokeObjectURL(image.preview)
      }
      return prev.filter(img => img.id !== id)
    })
  }, [])

  // 前端可视进度
  const [overallProgressPct, setOverallProgressPct] = useState(0)
  const [overallProgressCount, setOverallProgressCount] = useState(0)
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 开始OCR识别（批量处理）
  const startOCRProcessing = useCallback(async () => {
    if (images.length === 0) return

    setIsProcessing(true)
    setIsUploading(true)
    // 创建可取消控制器
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    try {
      const processingImages = images.map(img => ({ ...img, isProcessing: true }))
      setImages(processingImages)

      // 初始化进度（前端可视进度，后端完成时再拉满100%）
      setOverallProgressPct(0)
      setOverallProgressCount(0)
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
      const total = images.length || 1
      const step = Math.max(0.5, 90 / (total * 30))
      progressTimerRef.current = setInterval(() => {
        setOverallProgressPct(prev => {
          const next = Math.min(90, prev + step)
          const count = Math.min(total - 1, Math.floor((next / 100) * total))
          setOverallProgressCount(count)
          return next
        })
      }, 200)

      // 逐张识别，实时更新进度与计数
      const aggregatedStructured: any[] = []
      const aggregatedTexts: string[] = []
      // 单张识别封装（优先单张接口；失败回退到批量接口的单张）
      const doSingleOCR = async (file: File) => {
        // 每张最多2次客户端重试（与服务端重试叠加，尽量保证成功）
        const maxClientRetries = 2
        let lastErr: any = null
        for (let r = 0; r <= maxClientRetries; r++) {
          try {
            // 优先走单张接口
            const res1 = await chatApi.extractTextFromImage(file)
            return res1
          } catch (e1: any) {
            lastErr = e1
            try {
              // 回退到批量接口的单张（保留取消 signal）
              const res2 = await chatApi.extractTextFromImages([file], ocrMode, abortRef.current.signal)
              return res2
            } catch (e2: any) {
              lastErr = e2
              // 轻微退避再重试
              await new Promise(res => setTimeout(res, 200 + r * 150))
            }
          }
        }
        throw lastErr
      }

      for (let i = 0; i < total; i++) {
        const file = images[i].file
        const singleResult = await doSingleOCR(file)
        // 更新该图片的处理状态与结果
        setImages(prev => prev.map((img, idx) => idx === i ? ({ ...img, ocrResult: singleResult, isProcessing: false }) : img))
        // 汇总结构化或文本
        const structuredOnce = (singleResult as any)?.metadata?.structured_messages as Array<any> | undefined
        if (structuredOnce && Array.isArray(structuredOnce) && structuredOnce.length > 0) {
          structuredOnce.forEach(m => aggregatedStructured.push(m))
        } else if (singleResult?.text) {
          aggregatedTexts.push(singleResult.text)
        }
        // 实时更新进度
        if (progressTimerRef.current) {
          clearInterval(progressTimerRef.current)
          progressTimerRef.current = null
        }
        const done = i + 1
        setOverallProgressCount(done)
        setOverallProgressPct(Math.round((done / total) * 100))

        // 为避免命中服务端限流，两个请求之间加入轻微延时
        if (i < total - 1) {
          await new Promise(res => setTimeout(res, 120))
        }
      }

      // 识别完成，拉满进度（双保险）
      setOverallProgressPct(100)
      setOverallProgressCount(total)

      // 汇总段落
      let allSegments: TextSegment[] = []
      if (aggregatedStructured.length > 0) {
        const hasRight = aggregatedStructured.some(m => (m.speaker_side === 'right') || (m.speaker_name === '我'))
        allSegments = aggregatedStructured.map((m: any, idx: number) => ({
          id: `batch-${idx}`,
          text: String(m.text || '').trim(),
          selected: true,
          source: hasRight ? (m.speaker_side === 'right' ? '己方' : '对方') : '对方',
          speakerSide: hasRight ? (m.speaker_side === 'right' ? 'right' : 'left') : 'left',
          speakerName: hasRight ? (m.speaker_name || (m.speaker_side === 'right' ? '己方' : '对方')) : (m.speaker_name || '对方')
        })).filter(s => s.text.length > 0)
      } else if (aggregatedTexts.length > 0) {
        allSegments = aggregatedTexts.flatMap((t, idx) => parseChatSegments(t, 'batch', idx + 1))
      }

      setTextSegments(allSegments)
      setShowTextSelection(true)

      // 成功后不弹出提示框，由后续界面引导

    } catch (error: any) {
      console.error('批量OCR处理失败:', error)
      if (error?.name === 'CanceledError' || error?.code === 'ERR_CANCELED') {
        toast({ title: '已取消识别', duration: 1500 })
      } else {
      toast({
        title: "批量识别失败",
        description: "服务繁忙或网络波动，请稍后重试",
        variant: "destructive",
        duration: 3000
      })
      }
      
      // 更新所有图片状态为失败
      setImages(prev => prev.map(img => ({ 
        ...img, 
        error: '识别失败', 
        isProcessing: false 
      })))
    } finally {
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current)
        progressTimerRef.current = null
      }
      setIsProcessing(false)
      setIsUploading(false)
    }
  }, [images, ocrMode, toast])

  // 确认选择的文本
  const confirmTextSelection = useCallback(() => {
    const selectedTexts = textSegments
      .filter(segment => segment.selected)
      .map(segment => segment.text)
      .join('\n\n')

    if (selectedTexts.trim()) {
      onTextExtracted?.(selectedTexts)
      setShowTextSelection(false)
      setImages([])
      setTextSegments([])
      
      toast({
        title: "文本已添加",
        description: `已添加 ${textSegments.filter(s => s.selected).length} 个段落到输入框`,
        duration: 2000
      })
    }
  }, [textSegments, onTextExtracted, toast])

  // 取消选择
  const cancelSelection = useCallback(() => {
    setShowTextSelection(false)
    setTextSegments([])
  }, [])

  // 切换段落选择状态
  const toggleSegmentSelection = useCallback((id: string) => {
    setTextSegments(prev => prev.map(segment => 
      segment.id === id 
        ? { ...segment, selected: !segment.selected }
        : segment
    ))
  }, [])

  // 全选/取消全选
  const toggleAllSelection = useCallback(() => {
    const allSelected = textSegments.every(segment => segment.selected)
    setTextSegments(prev => prev.map(segment => ({ ...segment, selected: !allSelected })))
  }, [textSegments])

  return (
    <>
      {/* 顶部全局识别进度条（已移除，根据需求仅保留卡片内进度与取消） */}
      {/* 上传按钮 */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled || isUploading}
        className="h-9 w-9 p-0 text-muted-foreground hover:text-foreground hover:bg-accent rounded-full"
        title="上传图片"
      >
        {isUploading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <ImageIcon className="h-5 w-5" />
        )}
      </Button>

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* 图片预览和操作 - 居中显示 */}
      {images.length > 0 && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <Card className="p-6 bg-card shadow-2xl border max-w-lg w-full mx-4 rounded-2xl backdrop-blur-sm">
            <div className="space-y-6">
              {/* 标题栏 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <ImageIcon className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-foreground">
                      图片预览
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      已选择 {images.length} 张图片，点击开始识别
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setImages([])}
                    className="h-8 w-8 p-0 hover:bg-accent rounded-full"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              {/* 图片缩略图网格 */}
              <div className="grid grid-cols-2 gap-4 max-h-64 overflow-y-auto">
                {images.map((image) => (
                  <div key={image.id} className="relative group">
                    <div className="aspect-square rounded-xl overflow-hidden border-2 border group-hover:border-blue-300 transition-colors">
                      <img
                        src={image.preview}
                        alt="预览"
                        className="w-full h-full object-cover"
                      />
                      <Button
                        variant="destructive"
                        size="icon"
                        className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => removeImage(image.id)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                      {image.isProcessing && (
                        <div className="absolute inset-0 bg-black bg-opacity-60 flex items-center justify-center">
                          <div className="flex flex-col items-center gap-1">
                            <Loader2 className="h-5 w-5 animate-spin text-white" />
                            <span className="text-xs text-white font-medium">识别中</span>
                          </div>
                        </div>
                      )}
                      {image.error && (
                        <div className="absolute top-2 left-2 flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/90 border border-red-300 shadow-sm">
                          <X className="h-3.5 w-3.5 text-red-600" />
                          <span className="text-[11px] leading-none text-red-600 font-medium">识别失败</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {/* 添加图片卡片：紧跟在最新一张图片后，尺寸与缩略图一致 */}
                <button
                  type="button"
                  onClick={() => {
                    if (fileInputRef.current) {
                      fileInputRef.current.click()
                    }
                  }}
                  className="relative group aspect-square rounded-xl overflow-hidden border-2 border-dashed border-muted-foreground/40 hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-colors flex items-center justify-center"
                >
                  <div className="flex flex-col items-center justify-center text-muted-foreground group-hover:text-blue-600">
                    <Plus className="h-8 w-8" />
                    <span className="mt-1 text-xs font-medium">添加图片</span>
                  </div>
                </button>
              </div>
              
              {/* 识别模式选择 */}
              <div className="space-y-3 border-t border-b py-4">
                <div className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                  选择识别模式
                </div>
              <div className="grid grid-cols-2 gap-3">
                  {/* 极速模式 */}
                  <button
                    onClick={() => setOcrMode('fast')}
                    className={cn(
                      "relative p-4 rounded-2xl border transition-all duration-300 text-left group overflow-hidden",
                      ocrMode === 'fast'
                        ? "border-blue-500 bg-blue-50 dark:bg-blue-950/80 shadow-md ring-2 ring-blue-500/30"
                        : "border-border bg-card hover:border-blue-300 hover:bg-accent"
                    )}
                  >
                    {/* 选中指示器 */}
                    {ocrMode === 'fast' && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center shadow-md">
                        <Check className="h-4 w-4 text-white" />
                      </div>
                    )}
                    <div className="flex items-start gap-3 relative">
                      <div className={cn(
                        "w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-300",
                        ocrMode === 'fast'
                          ? "bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-md"
                          : "bg-muted text-muted-foreground group-hover:bg-blue-100 group-hover:text-blue-600 dark:group-hover:bg-blue-950 dark:group-hover:text-blue-400"
                      )}>
                        <Zap className="h-5 w-5" />
                      </div>
                      <div className="flex-1 min-w-0 pt-0.5">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={cn(
                            "font-semibold text-sm transition-colors duration-200",
                            ocrMode === 'fast'
                              ? "text-blue-700 dark:text-blue-300"
                              : "text-foreground"
                          )}>
                            极速模式
                          </span>
                        </div>
                        <p className={cn(
                          "text-xs leading-relaxed transition-colors duration-200",
                          ocrMode === 'fast'
                            ? "text-blue-600 dark:text-blue-400"
                            : "text-muted-foreground"
                        )}>
                          简单识别文本,识别速度快,适合快速预览
                        </p>
                      </div>
                    </div>
                  </button>
                  
                  {/* 性能模式 */}
                  <button
                    onClick={() => setOcrMode('quality')}
                    className={cn(
                      "relative p-4 rounded-2xl border transition-all duration-300 text-left group overflow-hidden",
                      ocrMode === 'quality'
                        ? "border-purple-500 bg-purple-50 dark:bg-purple-950/80 shadow-md ring-2 ring-purple-500/30"
                        : "border-border bg-card hover:border-purple-300 hover:bg-accent"
                    )}
                  >
                    {/* 选中指示器 */}
                    {ocrMode === 'quality' && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center shadow-md">
                        <Check className="h-4 w-4 text-white" />
                      </div>
                    )}
                    <div className="flex items-start gap-3 relative">
                      <div className={cn(
                        "w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-300",
                        ocrMode === 'quality'
                          ? "bg-gradient-to-br from-purple-500 to-purple-600 text-white shadow-md"
                          : "bg-muted text-muted-foreground group-hover:bg-purple-100 group-hover:text-purple-600 dark:group-hover:bg-purple-950 dark:group-hover:text-purple-400"
                      )}>
                        <Sparkles className="h-5 w-5" />
                      </div>
                      <div className="flex-1 min-w-0 pt-0.5">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={cn(
                            "font-semibold text-sm transition-colors duration-200",
                            ocrMode === 'quality'
                              ? "text-purple-700 dark:text-purple-300"
                              : "text-foreground"
                          )}>
                            性能模式
                          </span>
                        </div>
                        <p className={cn(
                          "text-xs leading-relaxed transition-colors duration-200",
                          ocrMode === 'quality'
                            ? "text-purple-600 dark:text-purple-400"
                            : "text-muted-foreground"
                        )}>
                          AI图片多维度理解，识别效果好，等待时间长
                        </p>
                      </div>
                    </div>
                  </button>
                  
                  
                </div>
              </div>
              
              {/* 操作按钮 */}
              <div className="flex gap-3">
                {isUploading ? (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => {
                        abortRef.current?.abort()
                        setIsUploading(false)
                        setIsProcessing(false)
                        setImages(prev => prev.map(img => ({ ...img, isProcessing: false })))
                        toast({ title: '已取消识别', duration: 1500 })
                      }}
                      className="flex-1 border-red-300 text-red-600 hover:bg-red-50 hover:border-red-400 dark:text-red-400 dark:hover:bg-red-950/20"
                    >
                      <X className="h-4 w-4 mr-2" />
                      取消识别
                    </Button>
                    <Button
                      disabled
                      className={cn(
                        "flex-1 text-white shadow-lg cursor-not-allowed",
                        ocrMode === 'fast'
                          ? "bg-gradient-to-r from-blue-500 to-blue-600"
                          : ocrMode === 'quality'
                          ? "bg-gradient-to-r from-purple-500 to-purple-600"
                          : "bg-gradient-to-r from-orange-500 to-orange-600"
                      )}
                    >
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      正在识别...
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => setImages([])}
                      className="flex-1"
                    >
                      重新选择
                    </Button>
                    <Button
                      onClick={startOCRProcessing}
                      disabled={isProcessing}
                      className={cn(
                        "flex-1 text-white shadow-lg hover:shadow-xl transition-all duration-200",
                        ocrMode === 'fast'
                          ? "bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700"
                          : ocrMode === 'quality'
                          ? "bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700"
                          : "bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700"
                      )}
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      开始识别
                    </Button>
                  </>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* OCR处理中的全屏提示 */}
      {isProcessing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-2xl p-8 w-96 shadow-2xl">
            <div className="text-center space-y-6">
              {/* 动画图标 */}
              <div className="relative">
                <div className="w-24 h-24 mx-auto bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                  <Eye className="h-12 w-12 text-white animate-pulse" />
                </div>
                <div className="absolute inset-0 w-24 h-24 mx-auto bg-gradient-to-r from-blue-500 to-purple-600 rounded-full animate-ping opacity-20"></div>
                <div className="absolute inset-0 w-24 h-24 mx-auto bg-gradient-to-r from-blue-500 to-purple-600 rounded-full animate-pulse opacity-10"></div>
              </div>
              
              {/* 动态标题和描述 - 固定宽度 */}
              <div className="space-y-3 w-full">
                <h3 className="text-2xl font-bold text-foreground w-full">
                  <span className="block w-full text-center">
                    <OCRProcessingText />
                  </span>
                </h3>
                <p className="text-muted-foreground text-lg w-full">
                  <span className="block w-full text-center">
                    <OCRProcessingDescription />
                  </span>
                </p>
              </div>
              
              {/* 进度指示器 */}
              <div className="space-y-4 w-full">
                <div className="flex justify-center space-x-2">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="w-3 h-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    ></div>
                  ))}
                </div>
                <div className="bg-muted rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-500 ease-out"
                    style={{ 
                      width: `${overallProgressPct}%` 
                    }}
                  ></div>
                </div>
                <p className="text-sm text-muted-foreground font-medium flex items-center justify-between bg-muted/50 rounded-md px-3 py-2">
                  <span className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-blue-500 to-purple-600" />
                    <span>
                      识别进度: {overallProgressCount} / {images.length}
                    </span>
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      abortRef.current?.abort()
                      setIsUploading(false)
                      setIsProcessing(false)
                      setImages(prev => prev.map(img => ({ ...img, isProcessing: false })))
                      toast({ title: '已取消识别', duration: 1500 })
                    }}
                    className="h-7 px-3 rounded-full border-red-300 text-red-600 hover:bg-red-50 hover:border-red-400 dark:text-red-400 dark:hover:bg-red-950/20"
                  >
                    <X className="h-3.5 w-3.5 mr-1.5" />
                    取消识别
                  </Button>
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 文本选择对话框 */}
      <Dialog open={showTextSelection} onOpenChange={setShowTextSelection}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden">
          <DialogHeader className="pb-4">
            <DialogTitle className="text-xl font-semibold text-foreground">
              选择要保留的文本段落
            </DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground mt-1">
              请选择您想要保留的文本段落，选中的内容将自动填入输入框
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* 操作栏 */}
            <div className="flex items-center justify-between bg-muted p-4 rounded-lg">
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={toggleAllSelection}
                  className="hover:bg-blue-50 hover:border-blue-300"
                >
                  {textSegments.every(s => s.selected) ? '取消全选' : '全选'}
                </Button>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span>
                    已选择 <span className="font-semibold text-blue-600">
                      {textSegments.filter(s => s.selected).length}
                    </span> / {textSegments.length} 个段落
                  </span>
                </div>
              </div>
            </div>

            {/* 文本段落列表（按角色着色） */}
            <div className="max-h-96 overflow-y-auto space-y-3 pr-2">
              {textSegments.map((segment) => {
                const isRight = segment.speakerSide === 'right'
                const roleColor = isRight 
                  ? 'border-green-500 bg-gradient-to-r from-green-50 to-emerald-50'
                  : 'border-blue-500 bg-gradient-to-r from-blue-50 to-indigo-50'
                const rolePillClasses = isRight 
                  ? 'bg-green-100 text-green-700'
                  : 'bg-blue-100 text-blue-700'
                return (
                  <div key={segment.id} className={cn('flex', isRight ? 'justify-end' : 'justify-start')}>
                    <div
                      className={cn(
                        'max-w-[80%] p-4 border-2 rounded-2xl cursor-pointer transition-all duration-200 hover:shadow-md',
                        isRight ? 'rounded-tr-sm' : 'rounded-tl-sm',
                        segment.selected ? roleColor + ' shadow-sm' : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                      )}
                      onClick={() => toggleSegmentSelection(segment.id)}
                    >
                      <div className={cn('flex items-start gap-3', isRight ? 'flex-row-reverse' : 'flex-row')}>
                        {/* 选择对勾：镜像到对应侧 */}
                        <div className="flex-shrink-0 mt-1">
                          {segment.selected ? (
                            <div className="w-5 h-5 bg-primary rounded-full flex items-center justify-center">
                              <Check className="h-3 w-3 text-white" />
                            </div>
                          ) : (
                            <div className="w-5 h-5 border-2 border rounded-full" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          {/* 顶部徽章：镜像对齐 */}
                          <div className={cn('flex items-center gap-2 mb-2', isRight ? 'justify-end flex-row-reverse' : 'justify-start')}>
                            {segment.selected && (
                              <div className="px-2 py-1 bg-muted text-muted-foreground text-xs rounded-full">
                                已选择
                              </div>
                            )}
                            <div className={cn('px-2 py-1 text-xs rounded-full', rolePillClasses)}>
                              {segment.speakerName || segment.source}
                            </div>
                          </div>
                          <div className={cn('text-sm text-foreground whitespace-pre-wrap leading-relaxed', isRight ? 'text-right' : 'text-left')}>
                            {segment.text}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* 底部操作按钮 */}
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 pt-4 pb-4 px-4 -mx-6 border-t border-border">
              <div className="text-sm text-muted-foreground order-2 sm:order-1">
                选择完成后，文本将自动填入输入框
              </div>
              <div className="flex gap-3 justify-end order-1 sm:order-2">
                <Button 
                  variant="outline" 
                  onClick={() => {
                    // 若正在上传，先取消网络请求
                    if (isUploading) {
                      abortRef.current?.abort()
                    }
                    cancelSelection()
                  }}
                  className="px-6"
                >
                  取消
                </Button>
                <Button 
                  onClick={confirmTextSelection}
                  disabled={!textSegments.some(s => s.selected)}
                  className="px-6 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white shadow-md hover:shadow-lg transition-all duration-200"
                >
                  确认选择 ({textSegments.filter(s => s.selected).length})
                </Button>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

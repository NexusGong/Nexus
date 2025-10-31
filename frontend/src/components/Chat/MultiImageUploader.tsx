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
  Download
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

  // 开始OCR识别（批量处理）
  const startOCRProcessing = useCallback(async () => {
    if (images.length === 0) return

    setIsProcessing(true)
    setIsUploading(true)

    try {
      const processingImages = images.map(img => ({ ...img, isProcessing: true }))
      setImages(processingImages)

      // 使用批量识别API
      const files = images.map(img => img.file)
      const ocrResult = await chatApi.extractTextFromImages(files)
      
      // 更新所有图片状态
      setImages(prev => prev.map(img => ({ 
        ...img, 
        ocrResult, 
        isProcessing: false 
      })))

      // 若后端提供结构化消息，优先使用
      let allSegments: TextSegment[] = []
      const structured = (ocrResult as any)?.metadata?.structured_messages as Array<any> | undefined
      if (structured && Array.isArray(structured) && structured.length > 0) {
        allSegments = structured.map((m, idx) => ({
          id: `batch-${idx}`,
          text: String(m.text || '').trim(),
          selected: true,
          source: m.speaker_side === 'right' ? '己方' : '对方',
          speakerSide: m.speaker_side === 'right' ? 'right' : 'left',
          speakerName: m.speaker_name || (m.speaker_side === 'right' ? '己方' : '对方')
        })).filter(s => s.text.length > 0)
      } else {
        // 退化为本地解析
        allSegments = parseChatSegments(ocrResult.text, 'batch', 1)
      }

      setTextSegments(allSegments)
      setShowTextSelection(true)

      // 成功后不弹出提示框，由后续界面引导

    } catch (error: any) {
      console.error('批量OCR处理失败:', error)
      toast({
        title: "批量识别失败",
        description: "服务繁忙或网络波动，请稍后重试",
        variant: "destructive",
        duration: 3000
      })
      
      // 更新所有图片状态为失败
      setImages(prev => prev.map(img => ({ 
        ...img, 
        error: '识别失败', 
        isProcessing: false 
      })))
    } finally {
      setIsProcessing(false)
      setIsUploading(false)
    }
  }, [images, toast])

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
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setImages([])}
                  className="h-8 w-8 p-0 hover:bg-accent rounded-full"
                >
                  <X className="h-4 w-4" />
                </Button>
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
                        <div className="absolute inset-0 bg-red-500 bg-opacity-60 flex items-center justify-center">
                          <div className="flex flex-col items-center gap-1">
                            <X className="h-5 w-5 text-white" />
                            <span className="text-xs text-white font-medium">失败</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* 操作按钮 */}
              <div className="flex gap-3">
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
                  className="flex-1 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white shadow-lg hover:shadow-xl transition-all duration-200"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      正在识别...
                    </>
                  ) : (
                    <>
                      <Eye className="h-4 w-4 mr-2" />
                      开始识别
                    </>
                  )}
                </Button>
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
                      width: `${((images.length - images.filter(img => img.isProcessing).length) / images.length) * 100}%` 
                    }}
                  ></div>
                </div>
                <p className="text-sm text-muted-foreground font-medium">
                  识别进度: {images.length - images.filter(img => img.isProcessing).length} / {images.length}
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
                          <div className={cn('flex items-center gap-2 mb-2', isRight ? 'justify-end' : 'justify-start')}>
                            <div className={cn('px-2 py-1 text-xs rounded-full', rolePillClasses)}>
                              {segment.speakerName || segment.source}
                            </div>
                            {segment.selected && (
                              <div className="px-2 py-1 bg-muted text-muted-foreground text-xs rounded-full">
                                已选择
                              </div>
                            )}
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
            <div className="flex justify-between items-center pt-4 border-t border">
              <div className="text-sm text-muted-foreground">
                选择完成后，文本将自动填入输入框
              </div>
              <div className="flex gap-3">
                <Button 
                  variant="outline" 
                  onClick={cancelSelection}
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

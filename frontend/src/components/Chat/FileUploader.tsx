import { useState, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { 
  Paperclip, 
  FileText, 
  Loader2
} from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { useToast } from '@/hooks/use-toast'

interface FileUploaderProps {
  disabled?: boolean
}

export default function FileUploader({ disabled }: FileUploaderProps) {
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { setUploading } = useChatStore()
  const { toast } = useToast()

  const handleFileUpload = useCallback(async (file: File) => {
    if (!file) return

    // 检查文件大小 (10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: "文件过大",
        description: "文件大小不能超过10MB",
        variant: "destructive",
        duration: 2000
      })
      return
    }

    setIsUploading(true)
    setUploading(true)

    try {
      // 文件上传处理（成功不提示）
    } catch (error) {
      console.error('文件上传失败:', error)
      toast({
        title: "上传失败",
        description: "无法上传文件，请重试",
        variant: "destructive",
        duration: 2000
      })
    } finally {
      setIsUploading(false)
      setUploading(false)
    }
  }, [setUploading, toast])

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileUpload(files[0])
    }
    e.target.value = ''
  }, [handleFileUpload])

  return (
    <div className="flex items-center gap-2">
      {/* 文件上传按钮 */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled || isUploading}
        className="h-9 w-9 p-0 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full"
        title="上传文件"
      >
        {isUploading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Paperclip className="h-5 w-5" />
        )}
      </Button>

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileInputChange}
        className="hidden"
      />
    </div>
  )
}

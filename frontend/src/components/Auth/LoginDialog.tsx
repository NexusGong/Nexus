import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { authApi } from '@/services/api'
import { useAuthStore } from '@/store/authStore'
import { useToast } from '@/hooks/use-toast'
import { Loader2 } from 'lucide-react'

interface LoginDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSwitchToRegister?: () => void
}

export default function LoginDialog({ open, onOpenChange, onSwitchToRegister }: LoginDialogProps) {
  const [contact, setContact] = useState('')
  const [code, setCode] = useState('')
  const [isSendingCode, setIsSendingCode] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  
  const { login } = useAuthStore()
  const { toast } = useToast()
  const navigate = useNavigate()

  const handleSendCode = async () => {
    if (!contact.trim()) {
      toast({
        title: "请输入联系方式",
        description: "请输入邮箱或手机号",
        variant: "destructive"
      })
      return
    }

    setIsSendingCode(true)
    try {
      await authApi.sendCode({
        contact: contact.trim(),
        code_type: 'login'
      })
      toast({
        title: "验证码已发送",
        description: "请查收验证码",
        duration: 500
      })
      setCountdown(60)
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } catch (error: any) {
      toast({
        title: "发送失败",
        description: error.response?.data?.detail || "验证码发送失败，请重试",
        variant: "destructive",
        duration: 500
      })
    } finally {
      setIsSendingCode(false)
    }
  }

  const handleLogin = async () => {
    if (!contact.trim() || !code.trim()) {
      toast({
        title: "请填写完整信息",
        description: "请输入联系方式和验证码",
        variant: "destructive"
      })
      return
    }

    setIsLoggingIn(true)
    try {
      const response = await authApi.login({
        contact: contact.trim(),
        code: code.trim()
      })
      
      login(response.access_token, response.user)
      
      // 登录成功后立即获取使用统计信息
      try {
        const stats = await authApi.getUsageStats()
        useAuthStore.getState().setUsageStats(stats)
      } catch (error) {
        console.error('获取使用统计失败:', error)
      }
      
      onOpenChange(false)
      setContact('')
      setCode('')
      
      // 登录成功后导航到聊天页面，这样会触发 Sidebar 和 CardsPage 的数据加载
      navigate('/chat', { replace: true })
    } catch (error: any) {
      toast({
        title: "登录失败",
        description: error.response?.data?.detail || "登录失败，请检查验证码",
        variant: "destructive",
        duration: 500
      })
    } finally {
      setIsLoggingIn(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>登录</DialogTitle>
          <DialogDescription>
            使用邮箱或手机号登录，验证码将发送到您的联系方式
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">联系方式</label>
            <Input
              placeholder="邮箱或手机号"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              disabled={isLoggingIn || isSendingCode}
            />
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">验证码</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSendCode}
                disabled={isSendingCode || countdown > 0 || !contact.trim()}
                className="h-8 text-xs"
              >
                {isSendingCode ? (
                  <>
                    <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                    发送中
                  </>
                ) : countdown > 0 ? (
                  `${countdown}秒后重发`
                ) : (
                  '发送验证码'
                )}
              </Button>
            </div>
            <Input
              placeholder="请输入验证码"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={isLoggingIn}
              maxLength={6}
            />
          </div>
          
          <Button
            onClick={handleLogin}
            disabled={isLoggingIn || !contact.trim() || !code.trim()}
            className="w-full"
          >
            {isLoggingIn ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                登录中...
              </>
            ) : (
              '登录'
            )}
          </Button>
          
          {onSwitchToRegister && (
            <div className="text-center text-sm text-muted-foreground">
              还没有账号？{' '}
              <button
                onClick={onSwitchToRegister}
                className="text-primary hover:underline"
              >
                立即注册
              </button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}


import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Loader2, Lock, Sparkles, CheckCircle2, CreditCard, Shield, Zap } from 'lucide-react'
import { paymentApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

interface AICharacter {
  id: number
  name: string
  avatar_url?: string
  description?: string
  rarity: string
}

interface UnlockDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  character: AICharacter | null
  onUnlockSuccess?: () => void
}

type PaymentStep = 'idle' | 'validating' | 'processing' | 'confirming' | 'success' | 'failed'

export default function UnlockDialog({ open, onOpenChange, character, onUnlockSuccess }: UnlockDialogProps) {
  const { toast } = useToast()
  const [price, setPrice] = useState<number | null>(null)
  const [isLoadingPrice, setIsLoadingPrice] = useState(false)
  const [isPurchasing, setIsPurchasing] = useState(false)
  const [paymentStep, setPaymentStep] = useState<PaymentStep>('idle')

  // 获取角色价格
  useEffect(() => {
    if (open && character) {
      loadPrice()
      setPaymentStep('idle')
    } else {
      setPrice(null)
      setPaymentStep('idle')
    }
  }, [open, character])

  const loadPrice = async () => {
    if (!character) return
    
    try {
      setIsLoadingPrice(true)
      const response = await paymentApi.getCharacterPrice(character.id)
      setPrice(response.price)
    } catch (error: any) {
      console.error('获取角色价格失败:', error)
      toast({
        title: "获取价格失败",
        description: error.response?.data?.detail || "无法获取角色价格",
        variant: "destructive"
      })
    } finally {
      setIsLoadingPrice(false)
    }
  }

  const handlePurchase = async () => {
    if (!character) return

    try {
      setIsPurchasing(true)
      setPaymentStep('validating')
      
      // 模拟支付流程步骤1：验证支付信息
      await new Promise(resolve => setTimeout(resolve, 800))
      setPaymentStep('processing')
      
      // 模拟支付流程步骤2：处理支付
      await new Promise(resolve => setTimeout(resolve, 1200))
      setPaymentStep('confirming')
      
      // 模拟支付流程步骤3：确认支付
      await new Promise(resolve => setTimeout(resolve, 600))
      
      // 调用后端API完成支付
      const response = await paymentApi.purchaseCharacter(character.id)
      
      if (response.payment_success) {
        setPaymentStep('success')
        
        // 延迟一下显示成功状态
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        toast({
          title: "解锁成功",
          description: `已成功解锁角色 ${character.name}`,
          duration: 500
        })
        onOpenChange(false)
        if (onUnlockSuccess) {
          onUnlockSuccess()
        }
      } else {
        setPaymentStep('failed')
        toast({
          title: "解锁失败",
          description: response.message || "解锁角色失败",
          variant: "destructive"
        })
        // 3秒后重置状态
        setTimeout(() => {
          setPaymentStep('idle')
        }, 3000)
      }
    } catch (error: any) {
      console.error('购买角色失败:', error)
      setPaymentStep('failed')
      toast({
        title: "解锁失败",
        description: error.response?.data?.detail || "解锁角色失败，请重试",
        variant: "destructive"
      })
      // 3秒后重置状态
      setTimeout(() => {
        setPaymentStep('idle')
      }, 3000)
    } finally {
      setIsPurchasing(false)
    }
  }

  const getRarityColor = (rarity: string) => {
    switch (rarity) {
      case 'legendary':
        return 'from-yellow-500 to-orange-500'
      case 'epic':
        return 'from-purple-500 to-pink-500'
      case 'rare':
        return 'from-blue-500 to-cyan-500'
      default:
        return 'from-gray-500 to-gray-600'
    }
  }

  const getRarityLabel = (rarity: string) => {
    switch (rarity) {
      case 'legendary':
        return 'SSR'
      case 'epic':
        return 'SR'
      case 'rare':
        return 'R'
      default:
        return 'N'
    }
  }

  if (!character) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5 text-primary" />
            解锁角色
          </DialogTitle>
          <DialogDescription>
            解锁后即可使用该角色进行对话
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* 角色信息 */}
          <div className="flex items-start gap-4 p-4 rounded-lg border bg-card">
            {/* 角色头像 */}
            <div className="relative flex-shrink-0">
              {character.avatar_url ? (
                <img
                  src={character.avatar_url}
                  alt={character.name}
                  className="w-16 h-16 rounded-full object-cover border-2 border-primary/20"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/20 to-primary/40 flex items-center justify-center border-2 border-primary/20">
                  <span className="text-2xl font-bold text-primary">
                    {character.name.charAt(0)}
                  </span>
                </div>
              )}
              {/* 稀有度标签 */}
              <div className={cn(
                "absolute -top-1 -right-1 w-6 h-6 rounded-full bg-gradient-to-r",
                getRarityColor(character.rarity),
                "flex items-center justify-center border-2 border-background shadow-sm"
              )}>
                <span className="text-xs font-bold text-white">
                  {getRarityLabel(character.rarity)}
                </span>
              </div>
            </div>

            {/* 角色详情 */}
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-lg mb-1">{character.name}</h3>
              {character.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {character.description}
                </p>
              )}
            </div>
          </div>

          {/* 价格信息 */}
          <div className="p-4 rounded-lg border bg-muted/50">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">解锁价格</span>
              {isLoadingPrice ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-muted-foreground">加载中...</span>
                </div>
              ) : price !== null ? (
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span className="text-2xl font-bold text-primary">
                    ¥{price.toFixed(2)}
                  </span>
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">获取失败</span>
              )}
            </div>
            {price === 0 && (
              <p className="text-xs text-muted-foreground mt-2">
                该角色为免费角色
              </p>
            )}
          </div>

          {/* 支付流程展示 */}
          {isPurchasing && paymentStep !== 'idle' && (
            <div className="p-4 rounded-lg border bg-primary/5 border-primary/20">
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-3">
                  <CreditCard className="h-4 w-4 text-primary" />
                  支付处理中...
                </div>
                
                {/* 支付步骤 */}
                <div className="space-y-2">
                  {/* 步骤1：验证支付信息 */}
                  <div className={cn(
                    "flex items-center gap-2 text-sm transition-colors",
                    paymentStep === 'validating' ? "text-primary" : 
                    ['processing', 'confirming', 'success'].includes(paymentStep) ? "text-green-600" : 
                    "text-muted-foreground"
                  )}>
                    {paymentStep === 'validating' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : ['processing', 'confirming', 'success'].includes(paymentStep) ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-muted-foreground" />
                    )}
                    <span>验证支付信息</span>
                  </div>

                  {/* 步骤2：处理支付 */}
                  <div className={cn(
                    "flex items-center gap-2 text-sm transition-colors",
                    paymentStep === 'processing' ? "text-primary" : 
                    ['confirming', 'success'].includes(paymentStep) ? "text-green-600" : 
                    "text-muted-foreground"
                  )}>
                    {paymentStep === 'processing' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : ['confirming', 'success'].includes(paymentStep) ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-muted-foreground" />
                    )}
                    <span>处理支付请求</span>
                  </div>

                  {/* 步骤3：确认支付 */}
                  <div className={cn(
                    "flex items-center gap-2 text-sm transition-colors",
                    paymentStep === 'confirming' ? "text-primary" : 
                    paymentStep === 'success' ? "text-green-600" : 
                    "text-muted-foreground"
                  )}>
                    {paymentStep === 'confirming' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : paymentStep === 'success' ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-muted-foreground" />
                    )}
                    <span>确认支付完成</span>
                  </div>
                </div>

                {/* 支付成功提示 */}
                {paymentStep === 'success' && (
                  <div className="flex items-center gap-2 text-sm text-green-600 mt-3 pt-3 border-t border-green-200">
                    <Shield className="h-4 w-4" />
                    <span>支付成功，正在解锁角色...</span>
                  </div>
                )}

                {/* 支付失败提示 */}
                {paymentStep === 'failed' && (
                  <div className="flex items-center gap-2 text-sm text-destructive mt-3 pt-3 border-t border-destructive/20">
                    <Zap className="h-4 w-4" />
                    <span>支付失败，请重试</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => {
              if (!isPurchasing) {
                onOpenChange(false)
              }
            }}
            disabled={isPurchasing}
          >
            取消
          </Button>
          <Button
            onClick={handlePurchase}
            disabled={isPurchasing || isLoadingPrice || price === null || paymentStep === 'success'}
            className="min-w-24"
          >
            {isPurchasing ? (
              <>
                {paymentStep === 'success' ? (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    解锁成功
                  </>
                ) : (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {paymentStep === 'validating' ? '验证中...' :
                     paymentStep === 'processing' ? '支付中...' :
                     paymentStep === 'confirming' ? '确认中...' :
                     '处理中...'}
                  </>
                )}
              </>
            ) : (
              <>
                <Lock className="mr-2 h-4 w-4" />
                确认解锁
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}


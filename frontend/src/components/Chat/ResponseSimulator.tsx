import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { 
  Brain, 
  MessageSquare, 
  Send,
  Loader2,
  Lightbulb,
  AlertCircle
} from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { chatApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

interface ResponseSimulatorProps {
  className?: string
}

export default function ResponseSimulator({ className }: ResponseSimulatorProps) {
  const [selectedResponse, setSelectedResponse] = useState('')
  const [simulatedReaction, setSimulatedReaction] = useState('')
  const [isSimulating, setIsSimulating] = useState(false)
  const { currentSuggestions, currentConversation } = useChatStore()
  const { toast } = useToast()

  const handleSimulate = async () => {
    if (!selectedResponse.trim() || !currentConversation) {
      toast({
        title: "请先选择回复",
        description: "请选择一个回复建议后再进行模拟",
        variant: "destructive"
      })
      return
    }

    try {
      setIsSimulating(true)
      
      // 模拟对方可能的反应
      const response = await chatApi.analyzeChat({
        conversation_id: currentConversation.id,
        message: `如果对方回复："${selectedResponse}"，请预测对方可能的反应和感受`,
        context_mode: currentConversation.context_mode
      })

      setSimulatedReaction(response.analysis.sentiment?.description || '分析完成')
      
      toast({
        title: "模拟完成",
        description: "已生成对方可能的反应预测"
      })

    } catch (error) {
      console.error('模拟失败:', error)
      toast({
        title: "模拟失败",
        description: "无法生成反应预测，请重试",
        variant: "destructive"
      })
    } finally {
      setIsSimulating(false)
    }
  }

  if (!currentSuggestions || currentSuggestions.length === 0) {
    return (
      <Card className={cn("", className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            回复模拟器
          </CardTitle>
          <CardDescription>
            预测对方对你回复的可能反应
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              请先进行聊天分析，获取回复建议后再使用模拟器
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5" />
          回复模拟器
        </CardTitle>
        <CardDescription>
          选择回复建议，AI将预测对方可能的反应
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 回复建议选择 */}
        <div>
          <h4 className="font-medium mb-3">选择要模拟的回复：</h4>
          <div className="space-y-2">
            {currentSuggestions.map((suggestion, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{suggestion.type}</Badge>
                  <span className="text-sm font-medium">{suggestion.title}</span>
                </div>
                {suggestion.examples.map((example, exampleIndex) => (
                  <Button
                    key={exampleIndex}
                    variant={selectedResponse === example ? "default" : "outline"}
                    size="sm"
                    className="w-full justify-start text-left h-auto p-3"
                    onClick={() => setSelectedResponse(example)}
                  >
                    <MessageSquare className="h-4 w-4 mr-2 flex-shrink-0" />
                    <span className="text-sm">{example}</span>
                  </Button>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* 模拟按钮 */}
        <Button
          onClick={handleSimulate}
          disabled={!selectedResponse || isSimulating}
          className="w-full"
        >
          {isSimulating ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              正在模拟...
            </>
          ) : (
            <>
              <Brain className="h-4 w-4 mr-2" />
              开始模拟
            </>
          )}
        </Button>

        {/* 模拟结果 */}
        {simulatedReaction && (
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-yellow-600" />
              <span className="font-medium text-sm">预测反应：</span>
            </div>
            <p className="text-sm text-muted-foreground">
              {simulatedReaction}
            </p>
          </div>
        )}

        {/* 使用提示 */}
        <div className="p-3 bg-blue-50 rounded-lg">
          <p className="text-xs text-blue-700">
            💡 提示：模拟器会基于对话上下文和选择的回复，预测对方可能的反应和感受，帮助你更好地准备后续对话。
          </p>
        </div>
      </CardContent>
    </Card>
  )
}


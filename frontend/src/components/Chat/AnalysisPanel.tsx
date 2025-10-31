import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Brain, 
  Heart, 
  MessageSquare, 
  Users, 
  Eye, 
  Key,
  Lightbulb,
  Download,
  FileText,
  Plus,
  Settings
} from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { cardApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import ContextModeSelector from './ContextModeSelector'
import ResponseSimulator from './ResponseSimulator'
import { cn } from '@/lib/utils'

export default function AnalysisPanel() {
  const [isCreatingCard, setIsCreatingCard] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const { 
    currentAnalysis, 
    currentSuggestions, 
    currentConversation,
    currentMessages,
    setCurrentConversation
  } = useChatStore()
  const { toast } = useToast()

  const handleCreateCard = async () => {
    if (!currentAnalysis || !currentConversation) return

    try {
      setIsCreatingCard(true)
      
      // 获取最新的用户消息作为原始内容
      const lastUserMessage = currentMessages
        .filter(msg => msg.role === 'user')
        .pop()

      if (!lastUserMessage) {
        throw new Error('没有找到用户消息')
      }

      // 生成更智能的标题
      const intent = currentAnalysis.intent?.primary || '未知意图'
      const sentiment = currentAnalysis.sentiment?.overall || 'neutral'
      
      const title = `${intent}分析`
      const description = `基于${currentConversation.context_mode || 'general'}模式的AI分析结果`

      await cardApi.createCard({
        title,
        description,
        original_content: lastUserMessage.content,
        analysis_data: currentAnalysis,
        response_suggestions: currentSuggestions,
        context_mode: currentConversation.context_mode,
        conversation_id: currentConversation.id
      })

      toast({
        title: "卡片创建成功",
        description: "分析结果已保存为卡片",
        duration: 500
      })

    } catch (error) {
      console.error('创建卡片失败:', error)
      toast({
        title: "创建失败",
        description: "无法创建分析卡片，请重试",
        variant: "destructive"
      })
    } finally {
      setIsCreatingCard(false)
    }
  }

  const handleContextModeChange = (mode: string) => {
    if (currentConversation) {
      setCurrentConversation({
        ...currentConversation,
        context_mode: mode
      })
    }
  }

  if (!currentAnalysis) {
    return (
      <div className="p-4 h-full flex items-center justify-center">
        <Card className="text-center">
          <CardHeader>
            <Brain className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <CardTitle>等待分析</CardTitle>
            <CardDescription>
              发送消息后，AI将在这里显示详细的分析结果
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center gap-2"
            >
              <Settings className="h-4 w-4" />
              设置分析模式
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* 设置面板 */}
      {showSettings && (
        <ContextModeSelector
          selectedMode={currentConversation?.context_mode || 'general'}
          onModeChange={handleContextModeChange}
        />
      )}

      {/* 设置按钮 */}
      <div className="flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowSettings(!showSettings)}
          className="flex items-center gap-2"
        >
          <Settings className="h-4 w-4" />
          {showSettings ? '隐藏设置' : '分析设置'}
        </Button>
      </div>
      {/* 分析概览 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            分析概览
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">意图</span>
            <Badge variant="secondary">
              {currentAnalysis.intent.primary}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">情感</span>
            <Badge 
              variant={currentAnalysis.sentiment.overall === 'positive' ? 'default' : 
                      currentAnalysis.sentiment.overall === 'negative' ? 'destructive' : 'secondary'}
            >
              {currentAnalysis.sentiment.overall}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">语气</span>
            <Badge variant="outline">
              {currentAnalysis.tone.style}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">关系</span>
            <Badge variant="outline">
              {currentAnalysis.relationship.closeness}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* 详细分析 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            详细分析
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 意图分析 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="h-4 w-4" />
              <span className="font-medium">意图分析</span>
            </div>
            <p className="text-sm text-muted-foreground">
              {currentAnalysis.intent.description}
            </p>
            {currentAnalysis.intent.secondary.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {currentAnalysis.intent.secondary.map((intent, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {intent}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* 情感分析 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Heart className="h-4 w-4" />
              <span className="font-medium">情感分析</span>
            </div>
            <p className="text-sm text-muted-foreground">
              {currentAnalysis.sentiment.description}
            </p>
            <div className="mt-2 flex items-center gap-2">
              <span className="text-xs">强度:</span>
              <div className="flex-1 bg-muted rounded-full h-2">
                <div 
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${currentAnalysis.sentiment.intensity * 100}%` }}
                />
              </div>
              <span className="text-xs">{Math.round(currentAnalysis.sentiment.intensity * 100)}%</span>
            </div>
            {currentAnalysis.sentiment.emotions.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {currentAnalysis.sentiment.emotions.map((emotion, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {emotion}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* 关系分析 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4" />
              <span className="font-medium">关系分析</span>
            </div>
            <p className="text-sm text-muted-foreground">
              {currentAnalysis.relationship.description}
            </p>
          </div>

          {/* 潜台词分析 */}
          {currentAnalysis.subtext.hidden_meanings.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Eye className="h-4 w-4" />
                <span className="font-medium">潜台词</span>
              </div>
              <ul className="text-sm text-muted-foreground space-y-1">
                {currentAnalysis.subtext.hidden_meanings.map((meaning, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-primary">•</span>
                    <span>{meaning}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 关键信息 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Key className="h-4 w-4" />
              <span className="font-medium">关键信息</span>
            </div>
            <ul className="text-sm text-muted-foreground space-y-1">
              {currentAnalysis.key_points.map((point, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* 回复建议 */}
      {currentSuggestions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5" />
              回复建议
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {currentSuggestions.map((suggestion, index) => (
              <div key={index} className="border rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline">{suggestion.type}</Badge>
                  <span className="font-medium text-sm">{suggestion.title}</span>
                </div>
                <p className="text-sm text-muted-foreground mb-2">
                  {suggestion.description}
                </p>
                {suggestion.examples.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-xs font-medium">示例回复:</span>
                    {suggestion.examples.map((example, exampleIndex) => (
                      <div key={exampleIndex} className="text-xs bg-muted p-2 rounded">
                        {example}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 回复模拟器 */}
      <ResponseSimulator />

      {/* 操作按钮 */}
      <div className="space-y-2">
        <Button 
          onClick={handleCreateCard}
          disabled={isCreatingCard}
          className="w-full"
        >
          {isCreatingCard ? (
            <>
              <FileText className="h-4 w-4 mr-2 animate-spin" />
              创建中...
            </>
          ) : (
            <>
              <Plus className="h-4 w-4 mr-2" />
              创建分析卡片
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

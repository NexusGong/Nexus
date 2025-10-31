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
  Copy,
  Check
} from 'lucide-react'
import { AnalysisResult, ResponseSuggestion } from '@/store/chatStore'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

interface AnalysisResultProps {
  analysis: AnalysisResult
  suggestions: ResponseSuggestion[]
}

export default function AnalysisResultComponent({ analysis, suggestions }: AnalysisResultProps) {
  const [copiedSuggestion, setCopiedSuggestion] = useState<number | null>(null)
  const { toast } = useToast()

  const copySuggestion = async (suggestion: ResponseSuggestion, index: number) => {
    try {
      const text = suggestion.examples?.[0] || suggestion.description
      await navigator.clipboard.writeText(text)
      setCopiedSuggestion(index)
      toast({
        title: "已复制",
        description: "内容已复制到剪贴板",
        duration: 500  // 500毫秒后自动消失
      })
      setTimeout(() => setCopiedSuggestion(null), 500)
    } catch (error) {
      toast({
        title: "复制失败",
        description: "无法复制内容",
        variant: "destructive"
      })
    }
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'bg-green-100 text-green-800 border-green-200'
      case 'negative': return 'bg-red-100 text-red-800 border-red-200'
      case 'neutral': return 'bg-gray-100 text-gray-800 border-gray-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getIntentColor = (intent: string) => {
    const colors = {
      '信息询问': 'bg-blue-100 text-blue-800 border-blue-200',
      '情感表达': 'bg-pink-100 text-pink-800 border-pink-200',
      '请求帮助': 'bg-yellow-100 text-yellow-800 border-yellow-200',
      '社交互动': 'bg-purple-100 text-purple-800 border-purple-200',
      '工作相关': 'bg-indigo-100 text-indigo-800 border-indigo-200',
      '默认': 'bg-gray-100 text-gray-800 border-gray-200'
    }
    return colors[intent as keyof typeof colors] || colors['默认']
  }

  return (
    <div className="space-y-4">
      {/* 分析结果 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4" />
            AI分析结果
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 意图分析 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Key className="h-4 w-4" />
              <span className="font-medium">意图分析</span>
              <Badge className={cn("text-xs", getIntentColor(analysis.intent?.primary || ''))}>
                {analysis.intent?.primary}
              </Badge>
            </div>
            <div className="mt-2 p-3 bg-muted/30 rounded-md">
              <p className="text-sm text-muted-foreground mb-2">
                {analysis.intent?.description}
              </p>
              <div className="flex flex-wrap gap-1">
                {analysis.intent?.secondary?.map((intent, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {intent}
                  </Badge>
                ))}
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                置信度: {Math.round((analysis.intent?.confidence || 0) * 100)}%
              </div>
            </div>
          </div>

          {/* 情感分析 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Heart className="h-4 w-4" />
              <span className="font-medium">情感分析</span>
              <Badge className={cn("text-xs", getSentimentColor(analysis.sentiment?.overall || ''))}>
                {analysis.sentiment?.overall}
              </Badge>
            </div>
            <div className="mt-2 p-3 bg-muted/30 rounded-md">
              <p className="text-sm text-muted-foreground mb-2">
                {analysis.sentiment?.description}
              </p>
              <div className="flex flex-wrap gap-1">
                {analysis.sentiment?.emotions?.map((emotion, index) => (
                  <Badge key={index} variant="secondary" className="text-xs">
                    {emotion}
                  </Badge>
                ))}
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                强度: {Math.round((analysis.sentiment?.intensity || 0) * 100)}%
              </div>
            </div>
          </div>

          {/* 语气分析 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="h-4 w-4" />
              <span className="font-medium">语气分析</span>
              <Badge variant="outline" className="text-xs">
                {analysis.tone?.style}
              </Badge>
            </div>
            <div className="mt-2 p-3 bg-muted/30 rounded-md">
              <p className="text-sm text-muted-foreground mb-2">
                {analysis.tone?.description}
              </p>
              <div className="flex gap-2">
                <Badge variant="outline" className="text-xs">
                  礼貌程度: {analysis.tone?.politeness}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  置信度: {Math.round((analysis.tone?.confidence || 0) * 100)}%
                </Badge>
              </div>
            </div>
          </div>

          {/* 关系分析 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4" />
              <span className="font-medium">关系分析</span>
              <Badge variant="outline" className="text-xs">
                {analysis.relationship?.closeness}
              </Badge>
            </div>
            <div className="mt-2 p-3 bg-muted/30 rounded-md">
              <p className="text-sm text-muted-foreground mb-2">
                {analysis.relationship?.description}
              </p>
              <div className="flex gap-2">
                <Badge variant="outline" className="text-xs">
                  权力关系: {analysis.relationship?.power_dynamic}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  信任度: {analysis.relationship?.trust_level}
                </Badge>
              </div>
            </div>
          </div>

          {/* 潜台词分析 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Eye className="h-4 w-4" />
              <span className="font-medium">潜台词分析</span>
            </div>
            <div className="mt-2 p-3 bg-muted/30 rounded-md">
              <p className="text-sm text-muted-foreground mb-2">
                {analysis.subtext?.description}
              </p>
              <div className="space-y-2">
                <div>
                  <span className="text-xs font-medium">隐含含义:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {analysis.subtext?.hidden_meanings?.map((meaning, index) => (
                      <Badge key={index} variant="secondary" className="text-xs">
                        {meaning}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-xs font-medium">潜在影响:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {analysis.subtext?.implications?.map((implication, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {implication}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 回复建议 */}
      {suggestions && suggestions.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Lightbulb className="h-4 w-4" />
              智能回复建议
            </CardTitle>
            <CardDescription className="text-xs">
              基于分析结果生成的回复建议，点击复制使用
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {suggestions.map((suggestion, index) => (
                <div key={index} className="p-3 border rounded-md hover:bg-muted/30 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <Badge variant="outline" className="text-xs mb-1">
                        {suggestion.type}
                      </Badge>
                      <h4 className="text-sm font-medium">{suggestion.title}</h4>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => copySuggestion(suggestion, index)}
                    >
                      {copiedSuggestion === index ? (
                        <Check className="h-3 w-3" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">
                    {suggestion.description}
                  </p>
                  {suggestion.examples && suggestion.examples.length > 0 && (
                    <div className="space-y-1">
                      {suggestion.examples.map((example, exampleIndex) => (
                        <div key={exampleIndex} className="text-xs bg-muted/50 p-2 rounded">
                          "{example}"
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}


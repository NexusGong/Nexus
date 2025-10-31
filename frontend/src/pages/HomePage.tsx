import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  MessageSquare, 
  FileText, 
  Image, 
  Brain, 
  Lightbulb
} from 'lucide-react'

export default function HomePage() {
  const features = [
    {
      icon: Image,
      title: '图片识别',
      description: '上传聊天截图，AI自动识别文字内容'
    },
    {
      icon: Brain,
      title: '智能分析',
      description: '多维度分析聊天内容，洞察真实意图'
    },
    {
      icon: Lightbulb,
      title: '回复建议',
      description: '提供多种回复思路和示例，助你完美回应'
    },
    {
      icon: FileText,
      title: '分析卡片',
      description: '生成精美的分析结果卡片，支持导出分享'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* 欢迎区域 */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary/10 mb-6">
            <Brain className="w-10 h-10 text-primary" />
          </div>
          <h1 className="text-5xl font-bold text-foreground mb-6 bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
            聊天内容智能分析平台
          </h1>
          <p className="text-xl text-muted-foreground mb-10 max-w-3xl mx-auto leading-relaxed">
            基于AI的聊天内容多维度分析，帮你理解对话深层含义，提供智能回复建议，让沟通更加高效
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="text-lg px-8 py-6">
              <Link to="/chat">
                <MessageSquare className="mr-2 h-5 w-5" />
                开始分析
              </Link>
            </Button>
            <Button variant="outline" size="lg" className="text-lg px-8 py-6" asChild>
              <Link to="/cards">
                <FileText className="mr-2 h-5 w-5" />
                查看卡片
              </Link>
            </Button>
          </div>
        </div>

        {/* 功能特性 */}
        <div className="mb-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground mb-4">核心功能</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              强大的AI分析能力，为你提供全方位的聊天内容洞察
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <Card key={index} className="text-center hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-0 shadow-md">
                  <CardHeader className="pb-4">
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-xl bg-gradient-to-br from-primary/10 to-primary/5">
                      <Icon className="h-8 w-8 text-primary" />
                    </div>
                    <CardTitle className="text-xl font-semibold">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <CardDescription className="text-base leading-relaxed">{feature.description}</CardDescription>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>


      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Eye, 
  Heart,
  Calendar,
  FileText,
  Image as ImageIcon,
  Loader2,
  MoreVertical,
  Edit2,
  Trash2,
  Save
} from 'lucide-react'
import { cardApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import { formatDate, downloadFile } from '@/lib/utils'
import DeleteConfirmDialog from '@/components/DeleteConfirmDialog'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import AnalysisResultComponent from '@/components/Chat/AnalysisResult'

interface AnalysisCard {
  id: number
  title: string
  description?: string
  original_content: string
  analysis_data: any
  response_suggestions?: any[]
  context_mode?: string
  is_favorite: boolean
  is_public: boolean
  tags?: string[]
  export_count: number
  conversation_time?: string
  created_at: string
  updated_at: string
}

export default function CardsPage() {
  const [cards, setCards] = useState<AnalysisCard[]>([])
  const [loading, setLoading] = useState(true)
  const [exportingCard, setExportingCard] = useState<number | null>(null)
  const [editingCard, setEditingCard] = useState<number | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const [showMoreOptions, setShowMoreOptions] = useState<number | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [cardToDelete, setCardToDelete] = useState<number | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [viewingCard, setViewingCard] = useState<AnalysisCard | null>(null)
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    loadCards()
  }, [])

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = () => {
      setShowMoreOptions(null)
    }
    
    if (showMoreOptions) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [showMoreOptions])

  const loadCards = async () => {
    try {
      setLoading(true)
      const response = await cardApi.getCards({
        page: 1,
        size: 50
      })
      setCards(response.cards)
    } catch (error) {
      console.error('加载卡片失败:', error)
      toast({
        title: "加载失败",
        description: "无法加载分析卡片，请重试",
        variant: "destructive",
        duration: 500
      })
    } finally {
      setLoading(false)
    }
  }

  const handleExportImage = async (cardId: number) => {
    try {
      setExportingCard(cardId)
      // 使用后端高质量导出（Playwright 渲染）
      const blob = await cardApi.exportCardAsImage(cardId)
      downloadFile(blob, `analysis_card_${cardId}.png`)
      toast({
        title: "导出成功",
        description: "分析卡片已导出为图片",
        duration: 500
      })
    } catch (error) {
      console.error('导出图片失败:', error)
      toast({
        title: "导出失败",
        description: "无法导出图片，请重试",
        variant: "destructive",
        duration: 500
      })
    } finally {
      setExportingCard(null)
    }
  }

  // PDF导出功能已下线

  const handleEditCard = (card: AnalysisCard) => {
    setEditingCard(card.id)
    setEditingTitle(card.title)
    setShowMoreOptions(null)
  }

  const handleSaveEdit = async (cardId: number) => {
    if (!editingTitle.trim()) return

    try {
      await cardApi.updateCard(cardId, {
        title: editingTitle.trim()
      })
      
      setCards(prev => prev.map(card => 
        card.id === cardId ? { ...card, title: editingTitle.trim() } : card
      ))
      
      setEditingCard(null)
      setEditingTitle('')
      
      toast({
        title: "重命名成功",
        description: "卡片标题已更新",
        duration: 500
      })
    } catch (error) {
      console.error('重命名失败:', error)
      toast({
        title: "重命名失败",
        description: "无法更新卡片标题，请重试",
        variant: "destructive",
        duration: 500
      })
    }
  }

  const handleDeleteCard = (cardId: number) => {
    setCardToDelete(cardId)
    setDeleteDialogOpen(true)
    setShowMoreOptions(null)
  }

  const handleViewCard = (card: AnalysisCard) => {
    setViewingCard(card)
    setViewDialogOpen(true)
  }

  const confirmDeleteCard = async () => {
    if (!cardToDelete) return
    
    setIsDeleting(true)
    try {
      await cardApi.deleteCard(cardToDelete)
      setCards(prev => prev.filter(card => card.id !== cardToDelete))
      
      // 删除成功后关闭对话框
      setDeleteDialogOpen(false)
      
      // 删除成功后不显示Toast提示，与删除对话保持一致
    } catch (error) {
      console.error('删除卡片失败:', error)
      toast({
        title: "删除失败",
        description: "无法删除卡片，请重试",
        variant: "destructive",
        duration: 500
      })
    } finally {
      setIsDeleting(false)
      setCardToDelete(null)
    }
  }

  const filteredCards = cards

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 页面头部 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">分析卡片</h1>
        <p className="text-muted-foreground">
          查看和管理你的聊天分析结果卡片
        </p>
      </div>


      {/* 卡片列表 */}
      {filteredCards.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">暂无分析卡片</h3>
            <p className="text-muted-foreground mb-4">
              开始分析聊天内容来创建你的第一张卡片
            </p>
            <Button asChild>
              <a href="/chat">开始分析</a>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCards.map((card) => (
            <Card key={card.id} className="group hover:shadow-xl transition-all duration-300 border shadow-md bg-card">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-500"></div>
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        {card.context_mode || 'general'}
                      </span>
                    </div>
                    {editingCard === card.id ? (
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleSaveEdit(card.id)
                          } else if (e.key === 'Escape') {
                            setEditingCard(null)
                            setEditingTitle('')
                          }
                        }}
                        onBlur={() => handleSaveEdit(card.id)}
                    className="w-full text-lg font-semibold bg-transparent border-b border-blue-300 focus:outline-none focus:border-blue-500 text-foreground"
                        autoFocus
                      />
                    ) : (
                      <CardTitle className="text-lg line-clamp-2 text-foreground group-hover:text-blue-600 transition-colors">
                        {card.title}
                      </CardTitle>
                    )}
                    {card.description && (
                      <CardDescription className="mt-2 line-clamp-2 text-muted-foreground">
                        {card.description}
                      </CardDescription>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {card.is_favorite && (
                      <Heart className="h-5 w-5 text-red-500 fill-current animate-pulse" />
                    )}
                    <div className="relative">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => {
                          e.stopPropagation()
                          setShowMoreOptions(showMoreOptions === card.id ? null : card.id)
                        }}
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                      
                      {/* 更多选项菜单 */}
                      {showMoreOptions === card.id && (
                        <div className="absolute right-0 top-8 z-10 bg-background border rounded-md shadow-lg min-w-32">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleEditCard(card)
                            }}
                            className="w-full px-3 py-2 text-left text-sm hover:bg-accent flex items-center gap-2"
                          >
                            <Edit2 className="h-3 w-3" />
                            重命名
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDeleteCard(card.id)
                            }}
                            className="w-full px-3 py-2 text-left text-sm hover:bg-accent text-destructive flex items-center gap-2"
                          >
                            <Trash2 className="h-3 w-3" />
                            删除
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* 分析结果预览 */}
                {card.analysis_data && (
                  <div className="p-3 rounded-lg border bg-primary/5 border-primary/20">
                    <h4 className="text-sm font-semibold mb-2 text-foreground flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
                      AI分析结果
                    </h4>
                    <div className="grid grid-cols-1 gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">意图</span>
                        <Badge variant="outline" className="text-xs bg-white border-blue-200 text-blue-700 px-2 py-0.5">
                          {card.analysis_data.intent?.primary}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">情感</span>
                        <Badge 
                          variant={card.analysis_data.sentiment?.overall === 'positive' ? 'default' : 
                                  card.analysis_data.sentiment?.overall === 'negative' ? 'destructive' : 'secondary'}
                          className="text-xs px-2 py-0.5"
                        >
                          {card.analysis_data.sentiment?.overall === 'positive' ? '积极' : 
                           card.analysis_data.sentiment?.overall === 'negative' ? '消极' : '中性'}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">语气</span>
                        <Badge variant="outline" className="text-xs bg-card border text-foreground px-2 py-0.5">
                          {card.analysis_data.tone?.style}
                        </Badge>
                      </div>
                    </div>
                  </div>
                )}

                {/* 标签 */}
                {card.tags && card.tags.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-1.5 text-foreground">标签</h4>
                    <div className="flex flex-wrap gap-1">
                      {card.tags.map((tag, index) => (
                        <Badge key={index} variant="secondary" className="text-xs bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors px-2 py-0.5">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* 元信息 */}
                <div className="space-y-1 text-xs text-muted-foreground pt-2 border-t border">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="h-3 w-3" />
                      <span>对话: {card.conversation_time ? formatDate(card.conversation_time) : '未知'}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <FileText className="h-3 w-3" />
                      <span>{card.export_count || 0}次导出</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Save className="h-3 w-3" />
                    <span>保存: {formatDate(card.created_at)}</span>
                  </div>
                </div>

                {/* 查看详情按钮 */}
                <div className="pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full hover:bg-purple-50 hover:border-purple-200 hover:text-purple-600 transition-all"
                    onClick={() => handleViewCard(card)}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    查看详情
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 删除确认弹窗 */}
      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={confirmDeleteCard}
        isLoading={isDeleting}
        title="删除分析卡片"
        description="此操作将永久删除此分析卡片，无法撤销。"
      />

      {/* 查看详情弹窗 */}
      {viewingCard && (
        <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold flex items-center gap-2">
                <FileText className="h-5 w-5" />
                {viewingCard.title}
              </DialogTitle>
              <DialogDescription>
                分析卡片详细信息
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* 卡片基本信息 */}
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  <span>创建时间: {formatDate(viewingCard.created_at)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <FileText className="h-4 w-4" />
                  <span>导出次数: {viewingCard.export_count || 0}</span>
                </div>
                {viewingCard.context_mode && (
                  <Badge variant="outline" className="text-xs">
                    {viewingCard.context_mode}
                  </Badge>
                )}
              </div>

              {/* 分析结果 */}
              {viewingCard.analysis_data && (
                <AnalysisResultComponent
                  analysis={viewingCard.analysis_data}
                  suggestions={viewingCard.response_suggestions || []}
                />
              )}
            </div>

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setViewDialogOpen(false)}>
                关闭
              </Button>
              <Button 
                onClick={() => handleExportImage(viewingCard.id)}
                disabled={exportingCard === viewingCard.id}
              >
                {exportingCard === viewingCard.id ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <ImageIcon className="h-4 w-4 mr-2" />
                )}
                导出图片
              </Button>
              
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}


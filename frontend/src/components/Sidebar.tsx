import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { 
  MessageSquare, 
  FileText, 
  Plus, 
  Menu,
  X,
  Edit2,
  Trash2,
  MoreVertical
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useChatStore } from '@/store/chatStore'
import { conversationApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import DeleteConfirmDialog from '@/components/DeleteConfirmDialog'
import { cn } from '@/lib/utils'

export default function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [editingConversation, setEditingConversation] = useState<number | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const [showMoreOptions, setShowMoreOptions] = useState<number | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [conversationToDelete, setConversationToDelete] = useState<number | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  
  const { 
    conversations, 
    setCurrentConversation, 
    clearCurrentChat,
    setConversations,
    updateConversation,
    removeConversation
  } = useChatStore()
  const location = useLocation()
  const navigate = useNavigate()
  const { toast } = useToast()

  // 加载对话列表
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const response = await conversationApi.getConversations(1, 20)
        setConversations(response.conversations)
      } catch (error) {
        console.error('加载对话列表失败:', error)
      }
    }
    loadConversations()
  }, [setConversations])

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

  const handleNewChat = () => {
    clearCurrentChat()
    navigate('/chat')
  }

  const handleConversationClick = (conversation: any) => {
    setCurrentConversation(conversation)
    navigate(`/chat/${conversation.id}`)
  }

  const handleEditConversation = (conversation: any) => {
    setEditingConversation(conversation.id)
    setEditingTitle(conversation.title)
    setShowMoreOptions(null)
  }

  const handleSaveEdit = async (conversationId: number) => {
    if (!editingTitle.trim()) return
    
    try {
      const updatedConversation = await conversationApi.updateConversation(conversationId, {
        title: editingTitle.trim()
      })
      updateConversation(conversationId, updatedConversation)
      setEditingConversation(null)
      setEditingTitle('')
      toast({
        title: "更新成功",
        description: "对话标题已更新",
        duration: 500
      })
    } catch (error) {
      console.error('更新对话失败:', error)
      toast({
        title: "更新失败",
        description: "无法更新对话标题，请重试",
        variant: "destructive"
      })
    }
  }

  const handleDeleteConversation = (conversationId: number) => {
    setConversationToDelete(conversationId)
    setDeleteDialogOpen(true)
    setShowMoreOptions(null)
  }

  const confirmDeleteConversation = async () => {
    if (!conversationToDelete) return
    
    setIsDeleting(true)
    try {
      await conversationApi.deleteConversation(conversationToDelete)
      removeConversation(conversationToDelete)
      
      // 如果删除的是当前对话，跳转到新建对话
      if (location.pathname === `/chat/${conversationToDelete}`) {
        navigate('/chat')
        clearCurrentChat()
      }
    } catch (error) {
      console.error('删除对话失败:', error)
      toast({
        title: "删除失败",
        description: "无法删除对话，请重试",
        variant: "destructive"
      })
    } finally {
      setIsDeleting(false)
      setConversationToDelete(null)
      setDeleteDialogOpen(false)
    }
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)
    
    if (diffInHours < 1) {
      return '刚刚'
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)}小时前`
    } else if (diffInHours < 24 * 7) {
      return `${Math.floor(diffInHours / 24)}天前`
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
    }
  }


  const navigation = [
    {
      name: '新建对话',
      href: '/chat',
      icon: Plus,
      onClick: handleNewChat
    },
    {
      name: '分析卡片',
      href: '/cards',
      icon: FileText
    },
    {
      name: '最近对话',
      href: '/chat',
      icon: MessageSquare
    }
  ]

  return (
    <div className={cn(
      "flex flex-col bg-card border-r transition-all duration-300",
      isCollapsed ? "w-16" : "w-72"
    )}>
      {/* 头部 */}
      <div className="p-3 border-b">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <h1 className="text-lg font-semibold text-foreground">
              聊天分析
            </h1>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="h-8 w-8"
          >
            {isCollapsed ? <Menu className="h-4 w-4" /> : <X className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* 导航菜单 */}
      <nav className="flex-1 p-3 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.href
          
          if (item.name === '最近对话') {
            // 特殊处理最近对话项
            return (
              <div key={item.name} className="space-y-2">
                <div className={cn(
                  "flex items-center gap-3 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  "text-muted-foreground",
                  isCollapsed && "justify-center"
                )}>
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  {!isCollapsed && <span>{item.name}</span>}
                </div>
                
                {/* 对话列表 */}
                {!isCollapsed && (
                  <div className="ml-7 space-y-0.5 max-h-[calc(100vh-60px)] overflow-y-auto">
                    {(Array.isArray(conversations) ? conversations : []).slice(0, 20).map((conversation) => {
                      const isActive = location.pathname === `/chat/${conversation.id}`
                      const isEditing = editingConversation === conversation.id
                      
                      return (
                        <div
                          key={conversation.id}
                          className={cn(
                            "group relative rounded-md transition-colors",
                            isActive ? "bg-primary/10" : "hover:bg-accent/50"
                          )}
                        >
                          {isEditing ? (
                            <div className="p-1.5">
                              <input
                                type="text"
                                value={editingTitle}
                                onChange={(e) => setEditingTitle(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    handleSaveEdit(conversation.id)
                                  } else if (e.key === 'Escape') {
                                    setEditingConversation(null)
                                    setEditingTitle('')
                                  }
                                }}
                                onBlur={() => handleSaveEdit(conversation.id)}
                                className="w-full px-2 py-1 text-sm bg-background border rounded focus:outline-none focus:ring-2 focus:ring-primary"
                                autoFocus
                              />
                            </div>
                          ) : (
                            <div className="w-full p-1.5 text-sm">
                              <div className="flex items-center justify-between">
                                <button
                                  onClick={() => handleConversationClick(conversation)}
                                  className="flex-1 min-w-0 text-left"
                                >
                                  <div className="font-medium truncate text-foreground text-sm">
                                    {conversation.title}
                                  </div>
                                  <div className="flex items-center gap-1.5 mt-0.5">
                                    <span className="text-xs text-muted-foreground">
                                      {conversation.message_count}条
                                    </span>
                                    <span className="text-xs text-muted-foreground">•</span>
                                    <span className="text-xs text-muted-foreground">
                                      {formatTime(conversation.updated_at)}
                                    </span>
                                  </div>
                                </button>
                                
                                {/* 更多选项按钮 */}
                                <div className="opacity-0 group-hover:opacity-100 transition-opacity ml-1">
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-5 w-5"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setShowMoreOptions(
                                        showMoreOptions === conversation.id ? null : conversation.id
                                      )
                                    }}
                                  >
                                    <MoreVertical className="h-3 w-3" />
                                  </Button>
                                </div>
                              </div>
                            </div>
                          )}
                          
                          {/* 更多选项菜单 */}
                          {showMoreOptions === conversation.id && (
                            <div className="absolute right-0 top-6 z-10 bg-background border rounded-md shadow-lg min-w-28">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleEditConversation(conversation)
                                }}
                                className="w-full px-2 py-1.5 text-left text-xs hover:bg-accent flex items-center gap-1.5"
                              >
                                <Edit2 className="h-3 w-3" />
                                重命名
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDeleteConversation(conversation.id)
                                }}
                                className="w-full px-2 py-1.5 text-left text-xs hover:bg-accent text-destructive flex items-center gap-1.5"
                              >
                                <Trash2 className="h-3 w-3" />
                                删除
                              </button>
                            </div>
                          )}
                        </div>
                      )
                    })}
                    {(!Array.isArray(conversations) || conversations.length === 0) && (
                      <p className="text-xs text-muted-foreground px-2 py-4 text-center">
                        暂无对话记录
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          }
          
          return (
            <Link
              key={item.name}
              to={item.href}
              onClick={item.onClick}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive 
                  ? "bg-primary text-primary-foreground" 
                  : "text-muted-foreground hover:text-foreground hover:bg-accent",
                isCollapsed && "justify-center"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {!isCollapsed && <span>{item.name}</span>}
            </Link>
          )
        })}
      </nav>

      {/* 删除确认弹窗 */}
      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={confirmDeleteConversation}
        isLoading={isDeleting}
      />
    </div>
  )
}

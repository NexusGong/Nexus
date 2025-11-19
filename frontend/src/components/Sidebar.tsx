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
  MoreVertical,
  Sparkles,
  Users
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { conversationApi, characterChatApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import DeleteConfirmDialog from '@/components/DeleteConfirmDialog'
import { cn, formatRelativeTime } from '@/lib/utils'

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

  // 加载对话列表（仅登录用户）
  const { isAuthenticated } = useAuthStore()
  
  useEffect(() => {
    const loadConversations = async () => {
      // 只有登录用户才能看到对话列表
      if (!isAuthenticated) {
        setConversations([])
        return
      }
      
      try {
        // 同时获取普通对话和角色对话（静默处理错误，不显示toast）
        const [normalResponse, characterResponse] = await Promise.all([
          conversationApi.getConversations(1, 20).catch((error) => {
            // 静默处理，不显示toast，特别是当没有历史记录时
            console.log('加载普通对话失败（可能是没有记录）:', error)
            return { conversations: [], total: 0 }
          }),
          characterChatApi.getConversations({ page: 1, size: 20 }).catch((error) => {
            // 静默处理，不显示toast，特别是当没有历史记录时
            console.log('加载角色对话失败（可能是没有记录）:', error)
            return { conversations: [], total: 0 }
          })
        ])
        
        // 合并后端返回的对话和本地存储的对话
        const currentConversations = useChatStore.getState().conversations || []
        const backendNormalConversations = normalResponse.conversations || []
        const backendCharacterConversations = characterResponse.conversations || []
        
        // 将角色对话转换为侧边栏格式
        const formattedCharacterConversations = backendCharacterConversations.map((conv: any) => ({
          id: conv.id,
          title: conv.title || (conv.character ? `与${conv.character.name}的对话` : '角色对话'),
          description: conv.character ? `与${conv.character.name}的对话` : '角色对话',
          context_mode: 'character_chat',
          is_active: 'active',
          message_count: conv.message_count || 0,
          analysis_count: 0,
          created_at: conv.created_at,
          updated_at: conv.updated_at,
          character: conv.character
        }))
        
        // 合并所有对话
        const allBackendConversations = [...backendNormalConversations, ...formattedCharacterConversations]
        
        // 创建一个 Map 来去重（以对话 ID 为键）
        const conversationMap = new Map<number, any>()
        
        // 先添加本地存储的对话（保留历史记录）
        currentConversations.forEach((conv: any) => {
          if (conv && conv.id) {
            conversationMap.set(conv.id, conv)
          }
        })
        
        // 然后添加后端返回的对话（更新最新数据）
        allBackendConversations.forEach((conv: any) => {
          if (conv && conv.id) {
            conversationMap.set(conv.id, conv)
          }
        })
        
        // 转换为数组并按更新时间排序
        const mergedConversations = Array.from(conversationMap.values())
          .sort((a, b) => {
            const timeA = new Date(a.updated_at || a.created_at || 0).getTime()
            const timeB = new Date(b.updated_at || b.created_at || 0).getTime()
            return timeB - timeA
          })
        
        setConversations(mergedConversations)
      } catch (error) {
        console.error('加载对话列表失败:', error)
      }
    }
    loadConversations()
  }, [setConversations, isAuthenticated])

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
    // 如果未登录，导航到主页；如果已登录，导航到聊天页面
    if (isAuthenticated) {
      navigate('/chat')
    } else {
      navigate('/')
    }
  }

  const handleConversationClick = (conversation: any) => {
    setCurrentConversation(conversation)
    // 判断是角色对话还是普通对话
    if (conversation.context_mode === 'character_chat') {
      navigate(`/chat-mode/${conversation.id}`)
    } else {
      navigate(`/chat/${conversation.id}`)
    }
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
      // 根据对话类型选择不同的删除API
      const conversation = conversations.find((c: any) => c.id === conversationToDelete)
      const isCharacterChat = conversation?.context_mode === 'character_chat'
      
      if (isCharacterChat) {
        // 删除角色对话
        await characterChatApi.deleteConversation(conversationToDelete)
      } else {
        // 删除普通对话
        await conversationApi.deleteConversation(conversationToDelete)
      }
      
      removeConversation(conversationToDelete)
      
      // 删除成功后，如果删除的是当前对话，跳转到新建对话页面
      const currentPath = location.pathname
      if (currentPath === `/chat/${conversationToDelete}` || currentPath === `/chat-mode/${conversationToDelete}`) {
        clearCurrentChat()
        if (isCharacterChat) {
          navigate('/chat-mode', { replace: true })
        } else {
          navigate('/chat', { replace: true })
        }
      } else {
        // 即使删除的不是当前对话，也确保清除当前对话状态（如果匹配）
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



  const navigation = [
    {
      name: '新建对话',
      href: '/chat',
      icon: Plus,
      onClick: handleNewChat
    },
    {
      name: '卡片模式',
      href: '/card-mode',
      icon: Sparkles
    },
    {
      name: '自由交谈',
      href: '/chat-mode',
      icon: Users
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
    <div 
      className={cn(
        "flex flex-col bg-card border-r transition-[width] duration-300 ease-in-out will-change-[width]",
        isCollapsed ? "w-16" : "w-72"
      )}
      style={{
        backfaceVisibility: 'hidden',
        transform: 'translateZ(0)',
      }}
    >
      {/* 头部 */}
      <div className="p-3 border-b">
        <div className="flex items-center justify-between">
          <h1 className={cn(
            "text-lg font-semibold text-foreground transition-all duration-300 ease-in-out overflow-hidden whitespace-nowrap",
            isCollapsed ? "w-0 opacity-0" : "w-auto opacity-100"
          )}>
            Replay
          </h1>
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
                  <span className={cn(
                    "transition-all duration-300 ease-in-out overflow-hidden whitespace-nowrap",
                    isCollapsed ? "w-0 opacity-0" : "w-auto opacity-100"
                  )}>
                    {item.name}
                  </span>
                </div>
                
                {/* 对话列表 */}
                <div className={cn(
                  "ml-7 space-y-0.5 transition-all duration-300 ease-in-out",
                  isCollapsed 
                    ? "w-0 opacity-0 overflow-hidden pointer-events-none" 
                    : "w-auto opacity-100",
                  // 当只有一条对话时，给更多上下空间，避免出现滚动条
                  conversations.length === 1 
                    ? "py-4" 
                    : "max-h-[calc(100vh-60px)] overflow-y-auto"
                )}>
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
                                      {formatRelativeTime(conversation.updated_at)}
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
              <span className={cn(
                "transition-all duration-300 ease-in-out overflow-hidden whitespace-nowrap",
                isCollapsed ? "w-0 opacity-0" : "w-auto opacity-100"
              )}>
                {item.name}
              </span>
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

import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { 
  Users, 
  Loader2, 
  Send, 
  MessageSquare,
  ChevronDown,
  Check,
  User,
  ArrowLeft,
  Settings,
  Lock
} from 'lucide-react'
import { characterApi, characterChatApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'
import MultiImageUploader from '@/components/Chat/MultiImageUploader'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import UnlockDialog from '@/components/Character/UnlockDialog'
import LoginDialog from '@/components/Auth/LoginDialog'
import RegisterDialog from '@/components/Auth/RegisterDialog'

interface AICharacter {
  id: number
  name: string
  avatar_url?: string
  description?: string
  personality: string
  speaking_style: string
  background?: string
  category: string
  rarity: string
  is_usable?: boolean
  is_locked?: boolean
}

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export default function ChatModePage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { addConversation, updateConversation } = useChatStore()
  const { user, isAuthenticated } = useAuthStore()
  
  const [characters, setCharacters] = useState<AICharacter[]>([])
  const [selectedCharacter, setSelectedCharacter] = useState<AICharacter | null>(null)
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [hasGreeted, setHasGreeted] = useState(false)
  const [isCharacterDialogOpen, setIsCharacterDialogOpen] = useState(false)
  const [unlockDialogOpen, setUnlockDialogOpen] = useState(false)
  const [characterToUnlock, setCharacterToUnlock] = useState<AICharacter | null>(null)
  const [loginDialogOpen, setLoginDialogOpen] = useState(false)
  const [registerDialogOpen, setRegisterDialogOpen] = useState(false)

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 加载角色列表
  useEffect(() => {
    loadCharacters()
  }, [toast, isAuthenticated])

  // 如果有conversationId，加载对话；如果没有，保留角色选择状态
  useEffect(() => {
    if (conversationId) {
      const id = Number(conversationId)
      // 如果当前已经有相同的conversationId且正在显示消息，不重新加载
      if (currentConversationId === id && messages.length > 0) {
        // 已经在显示对话，不重新加载
        return
      }
      loadConversation(id)
    } else {
      // 当没有conversationId时，清除对话相关状态，但保留角色选择
      // 只有在确实没有选择角色时才清除
      if (!selectedCharacter) {
        setCurrentConversationId(null)
        setMessages([])
        setHasGreeted(false)
        setInputValue('')
      }
      // 注意：不清除selectedCharacter，因为用户可能已经选择了角色但还没有发送消息
    }
  }, [conversationId, currentConversationId, messages.length, selectedCharacter])
  
  // 如果没有conversationId且没有选择角色，保持在选择角色页面（/chat-mode）
  // 不需要导航，因为已经在正确的页面了

  // 不再需要加载欢迎语，因为欢迎语会在发送第一条消息时自动创建

  const loadConversation = async (id: number) => {
    try {
      setIsLoading(true)
      const [convResponse, messagesResponse] = await Promise.all([
        characterChatApi.getConversations({ page: 1, size: 100 }),
        characterChatApi.getMessages(id)
      ])
      
      const conversation = convResponse.conversations?.find((c: any) => c.id === id)
      if (conversation) {
        setCurrentConversationId(id)
        setSelectedCharacter(conversation.character)
        setMessages(messagesResponse || [])
        setHasGreeted(messagesResponse && messagesResponse.length > 0)
        
        // 不在这里添加到对话列表，只有在用户成功发送消息后才添加
      } else {
        // 静默处理，不显示toast
        console.log('对话不存在，返回选择角色页面')
        navigate('/chat-mode', { replace: true })
      }
    } catch (error: any) {
      console.error('加载对话失败:', error)
      // 只有当是真正的错误（非404）时才显示toast
      if (error.response?.status !== 404) {
        toast({
          title: "加载失败",
          description: "无法加载对话内容",
          variant: "destructive"
        })
      }
      navigate('/chat-mode', { replace: true })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectCharacter = async (character: AICharacter) => {
    // 检查角色是否可用
    if (character.is_locked) {
      // 如果角色被锁定，触发解锁流程
      // 先保存要解锁的角色信息
      setCharacterToUnlock(character)
      
      if (!isAuthenticated) {
        // 未登录用户：弹出登录对话框
        setLoginDialogOpen(true)
      } else {
        // 登录用户：弹出付费解锁对话框
        setUnlockDialogOpen(true)
      }
      return
    }

    // 选择角色后立即创建对话并显示greetings
    setSelectedCharacter(character)
    setMessages([])
    setHasGreeted(false)
    setIsLoading(true)
    
    // 导航到聊天页面（不带conversationId）
    navigate('/chat-mode', { replace: true })
    
    try {
      // 创建临时greeting消息占位符
      const tempGreetingId = Date.now()
      const tempGreeting: Message = {
        id: tempGreetingId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString()
      }
      setMessages([tempGreeting])
      
      // 创建对话并流式显示greetings
      await characterChatApi.createConversationStream(
        {
          character_id: character.id,
          title: `与${character.name}的对话`
        },
        // onChunk: 接收流式greetings
        (greeting: string, conversationId: number, done: boolean) => {
          setCurrentConversationId(conversationId)
          setMessages(prev => prev.map(msg => 
            msg.id === tempGreetingId 
              ? { ...msg, content: greeting }
              : msg
          ))
          if (done) {
            setHasGreeted(true)
            setIsLoading(false)
            // 更新URL但不触发重新加载（使用replace: true避免触发useEffect）
            // 使用window.history.replaceState来避免触发useEffect
            window.history.replaceState(null, '', `/chat-mode/${conversationId}`)
          }
        },
        // onError: 错误处理
        (error: string) => {
          console.error('创建对话失败:', error)
          toast({
            title: "创建失败",
            description: error || "无法创建对话，请重试",
            variant: "destructive"
          })
          setMessages([])
          setIsLoading(false)
        }
      )
    } catch (error: any) {
      console.error('创建对话失败:', error)
      toast({
        title: "创建失败",
        description: error.message || "无法创建对话，请重试",
        variant: "destructive"
      })
      setMessages([])
      setIsLoading(false)
    }
  }

  const handleUnlockSuccess = () => {
    // 解锁成功后刷新角色列表
    loadCharacters()
    setCharacterToUnlock(null)
    hasHandledLoginUnlock.current = false
  }

  // 监听登录状态变化，登录成功后如果有要解锁的角色，弹出解锁对话框
  // 使用 ref 来跟踪是否已经处理过登录后的解锁流程，避免重复弹出
  const hasHandledLoginUnlock = useRef(false)
  
  useEffect(() => {
    if (isAuthenticated && characterToUnlock && !unlockDialogOpen && !hasHandledLoginUnlock.current) {
      // 用户已登录，且有要解锁的角色，且解锁对话框未打开，且还未处理过
      // 延迟一下，确保角色列表已刷新
      hasHandledLoginUnlock.current = true
      setTimeout(() => {
        setUnlockDialogOpen(true)
      }, 300)
    }
    
    // 如果用户未登录，重置标志
    if (!isAuthenticated) {
      hasHandledLoginUnlock.current = false
    }
  }, [isAuthenticated, characterToUnlock, unlockDialogOpen])

  const loadCharacters = async () => {
    try {
      setIsLoading(true)
      const response = await characterApi.getCharacters()
      const charactersList = response.characters || []
      console.log('加载到的角色数量:', charactersList.length)
      console.log('角色列表:', charactersList.map((c: any) => c.name))
      setCharacters(charactersList)
    } catch (error) {
      console.error('加载角色失败:', error)
      toast({
        title: "加载失败",
        description: "无法加载AI角色列表",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSwitchCharacter = async (character: AICharacter) => {
    // 切换角色时，创建新对话
    await handleSelectCharacter(character)
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isSending) return
    
    // 如果没有选择角色，不能发送消息
    if (!selectedCharacter) {
      toast({
        title: "请先选择角色",
        description: "请先选择一个AI角色",
        variant: "destructive"
      })
      return
    }

    const userMessage = inputValue.trim()
    setInputValue('')

    // 添加用户消息到界面
    const tempUserMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, tempUserMessage])

    // 如果是第一条消息，先显示欢迎语占位符
    if (!currentConversationId && messages.length === 0) {
      const tempGreetingId = Date.now() + 0.5
      const tempGreeting: Message = {
        id: tempGreetingId,
        role: 'assistant',
        content: '...',
        created_at: new Date().toISOString()
      }
      setMessages(prev => [...prev, tempGreeting])
    }

    // 创建AI消息占位符
    const tempAiMessageId = Date.now() + 1
    const tempAiMessage: Message = {
      id: tempAiMessageId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, tempAiMessage])

    try {
      setIsSending(true)
      
      let fullContent = ''
      let greetingReceived = false
      
      await characterChatApi.sendMessageStream(
        {
          conversation_id: currentConversationId || undefined,
          character_id: !currentConversationId ? selectedCharacter.id : undefined,
          message: userMessage
        },
        // onChunk: 接收流式内容
        (content: string, isGreeting?: boolean) => {
          if (isGreeting && !currentConversationId) {
            // 第一条消息时，先接收欢迎语
            if (!greetingReceived) {
              greetingReceived = true
              setMessages(prev => prev.map(msg => {
                // 更新欢迎语占位符
                if (msg.id === Date.now() + 0.5) {
                  return { ...msg, content: content }
                }
                return msg
              }))
            }
          } else {
            fullContent += content
            // 更新AI消息内容
            setMessages(prev => prev.map(msg => 
              msg.id === tempAiMessageId 
                ? { ...msg, content: fullContent }
                : msg
            ))
          }
        },
        // onDone: 流式完成（只有消息成功发送后才添加到最近对话）
        async (messageId: number, conversationId?: number) => {
          // 如果是新创建的对话，更新对话ID并导航
          if (conversationId && !currentConversationId) {
            setCurrentConversationId(conversationId)
            navigate(`/chat-mode/${conversationId}`, { replace: true })
            setHasGreeted(true)
          }
          
          // 更新消息ID为服务器返回的真实ID
          setMessages(prev => prev.map(msg => 
            msg.id === tempAiMessageId 
              ? { ...msg, id: messageId, content: fullContent }
              : msg
          ))
          
          // 消息成功发送后，添加到侧边栏的对话列表
          const finalConversationId = conversationId || currentConversationId
          if (finalConversationId && selectedCharacter) {
            try {
              const convResponse = await characterChatApi.getConversations({ page: 1, size: 100 })
              const conversation = convResponse.conversations?.find((c: any) => c.id === finalConversationId)
              if (conversation) {
                const conversationForSidebar = {
                  id: conversation.id,
                  title: conversation.title || `与${selectedCharacter.name}的对话`,
                  description: `与${selectedCharacter.name}的对话`,
                  context_mode: 'character_chat',
                  is_active: 'active',
                  message_count: conversation.message_count || 0,
                  analysis_count: 0,
                  created_at: conversation.created_at,
                  updated_at: conversation.updated_at,
                  character: selectedCharacter
                }
                
                // 检查对话是否已在列表中
                const { conversations } = useChatStore.getState()
                const exists = conversations.some((conv: any) => conv.id === conversation.id)
                
                if (exists) {
                  // 如果已存在，更新对话
                  updateConversation(conversation.id, conversationForSidebar as any)
                } else {
                  // 如果不存在，添加到列表顶部（与经典模式一致）
                  addConversation(conversationForSidebar as any)
                }
              }
            } catch (error) {
              console.error('更新对话列表失败:', error)
            }
          }
          
          setIsSending(false)
        },
        // onError: 错误处理
        (error: string) => {
          console.error('发送消息失败:', error)
          toast({
            title: "发送失败",
            description: error || "消息发送失败，请重试",
            variant: "destructive"
          })
          // 移除临时消息（包括欢迎语占位符）
          setMessages(prev => prev.filter(m => 
            m.id !== tempUserMessage.id && 
            m.id !== tempAiMessageId &&
            m.id !== Date.now() + 0.5
          ))
          setIsSending(false)
        }
      )
    } catch (error: any) {
      console.error('发送消息失败:', error)
      toast({
        title: "发送失败",
        description: error.message || "消息发送失败，请重试",
        variant: "destructive"
      })
      // 移除临时消息
      setMessages(prev => prev.filter(m => 
        m.id !== tempUserMessage.id && m.id !== tempAiMessageId
      ))
      setIsSending(false)
    }
  }

  const handleGenerateCardFromMessage = async () => {
    if (!currentConversationId) return

    try {
      setIsLoading(true)
      await characterChatApi.generateCard({
        conversation_id: currentConversationId
      })
      
      toast({
        title: "卡片生成成功",
        description: "分析卡片已保存",
        duration: 2000
      })
      
      navigate('/cards')
    } catch (error) {
      console.error('生成卡片失败:', error)
      toast({
        title: "生成失败",
        description: "无法生成卡片",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
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

  const getRarityOrder = (rarity: string) => {
    switch (rarity) {
      case 'legendary':
        return 4
      case 'epic':
        return 3
      case 'rare':
        return 2
      default:
        return 1
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

  const getCategoryName = (category: string) => {
    switch (category) {
      case 'original':
        return '原创'
      case 'classic':
        return '经典'
      case 'anime':
        return '动漫'
      case 'tv_series':
        return '影视剧'
      default:
        return category
    }
  }

  const filteredCharacters = (activeCategory === 'all' 
    ? characters 
    : characters.filter(c => c.category === activeCategory)
  ).sort((a, b) => {
    // 第一优先级：可用状态（可用的在前）
    const aUsable = a.is_usable ?? false
    const bUsable = b.is_usable ?? false
    if (aUsable !== bUsable) {
      return aUsable ? -1 : 1
    }
    // 第二优先级：稀有度（从高到低）
    const rarityDiff = getRarityOrder(b.rarity) - getRarityOrder(a.rarity)
    if (rarityDiff !== 0) return rarityDiff
    // 第三优先级：名称（中文排序）
    return a.name.localeCompare(b.name, 'zh-CN')
  })

  const categories = ['all', 'original', 'classic', 'anime', 'tv_series']

  // 如果没有选择角色，显示角色选择界面
  if (!selectedCharacter && !conversationId) {
    return (
      <div className="h-full flex flex-col bg-background">
        {/* 角色选择界面 */}
        <div className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-4 py-8 max-w-6xl">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 mb-4">
                <Users className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <h2 className="text-3xl font-bold text-foreground mb-2">选择你的倾听者</h2>
              <p className="text-muted-foreground">听听ta的建议吧</p>
            </div>

            {/* 分类筛选 */}
            <div className="flex gap-2 justify-center mb-6 flex-wrap">
              {categories.map(cat => (
                <Button
                  key={cat}
                  variant={activeCategory === cat ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveCategory(cat)}
                >
                  {cat === 'all' ? '全部' : getCategoryName(cat)}
                </Button>
              ))}
            </div>

            {/* 角色列表 */}
            {isLoading && characters.length === 0 ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {filteredCharacters.map((character) => {
                  const isLocked = character.is_locked ?? false
                  return (
                    <Card
                      key={character.id}
                      className={cn(
                        "relative cursor-pointer hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 border group overflow-hidden",
                        isLocked 
                          ? "border-muted/50 opacity-90" 
                          : "hover:border-primary/50"
                      )}
                      onClick={() => handleSelectCharacter(character)}
                    >
                      <CardContent className="p-3">
                        <div className="flex flex-col h-full">
                          {/* 头像区域 */}
                          <div className="relative mx-auto mb-2">
                            {character.avatar_url ? (
                              <img
                                src={character.avatar_url}
                                alt={character.name}
                                className={cn(
                                  "w-16 h-16 rounded-full object-cover border-2 transition-colors relative z-10",
                                  isLocked
                                    ? "border-primary/30 opacity-85"
                                    : "border-primary/20 group-hover:border-primary/50"
                                )}
                              />
                            ) : (
                              <div className={cn(
                                "w-16 h-16 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center border-2 transition-colors relative z-10",
                                isLocked
                                  ? "border-primary/30 opacity-85"
                                  : "border-primary/20 group-hover:border-primary/50"
                              )}>
                                <Users className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                              </div>
                            )}
                            {/* 稀有度角标 */}
                            <div className={`absolute -top-1 -right-1 w-6 h-6 rounded-full bg-gradient-to-r ${getRarityColor(character.rarity)} flex items-center justify-center border-2 border-background shadow-sm z-10`}>
                              <span className="text-[10px] font-bold text-white leading-none">
                                {getRarityLabel(character.rarity)}
                              </span>
                            </div>
                          </div>
                          
                          {/* 名称 */}
                          <h3 className={cn(
                            "font-semibold text-sm text-center mb-2 line-clamp-1 relative z-10",
                            isLocked ? "text-foreground/90" : "text-foreground"
                          )}>
                            {character.name}
                          </h3>
                          
                          {/* 标签 */}
                          <div className="flex items-center justify-center gap-1 mb-2 flex-wrap relative z-10">
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0.5">
                              {getCategoryName(character.category)}
                            </Badge>
                          </div>
                          
                          {/* 描述 */}
                          {character.description && (
                            <p className={cn(
                              "text-xs line-clamp-2 leading-relaxed text-center flex-1 relative z-10",
                              isLocked ? "text-foreground/85" : "text-muted-foreground"
                            )}>
                              {character.description}
                            </p>
                          )}
                        </div>

                        {/* 锁定遮罩 - 使用更透明的遮罩，确保信息可见 */}
                        {isLocked && (
                          <div className="absolute inset-0 bg-background/30 backdrop-blur-[1px] flex flex-col items-center justify-end pb-2 gap-1.5 z-20 pointer-events-none">
                            <div className="w-8 h-8 rounded-full bg-primary/90 flex items-center justify-center border-2 border-background shadow-lg">
                              <Lock className="h-4 w-4 text-background" />
                            </div>
                            <span className="text-xs font-semibold text-primary bg-background/95 backdrop-blur-sm px-2.5 py-1 rounded-md border border-primary/20 shadow-sm">
                              {!isAuthenticated ? '登录解锁' : '点击解锁'}
                            </span>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
                
                {/* 管理角色卡片 */}
                <Card
                  className="cursor-pointer hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 border-2 border-dashed border-primary/50 hover:border-primary group overflow-hidden"
                  onClick={() => navigate('/character-management')}
                >
                  <CardContent className="p-3">
                    <div className="flex flex-col h-full items-center justify-center min-h-[180px]">
                      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center border-2 border-primary/20 group-hover:border-primary/50 transition-colors mb-3">
                        <Settings className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                      </div>
                      <h3 className="font-semibold text-sm text-foreground text-center mb-2">
                        管理角色
                      </h3>
                      <p className="text-xs text-muted-foreground text-center">
                        解锁和管理角色
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>

        {/* 解锁对话框 */}
        <UnlockDialog
          open={unlockDialogOpen}
          onOpenChange={(open) => {
            setUnlockDialogOpen(open)
            // 如果关闭对话框（无论是取消还是成功），清除要解锁的角色
            if (!open) {
              setCharacterToUnlock(null)
              hasHandledLoginUnlock.current = false
            }
          }}
          character={characterToUnlock}
          onUnlockSuccess={handleUnlockSuccess}
        />

        {/* 登录对话框 */}
        <LoginDialog
          open={loginDialogOpen}
          onOpenChange={(open) => {
            setLoginDialogOpen(open)
            // 如果关闭登录对话框且用户已登录，刷新角色列表
            if (!open && isAuthenticated) {
              loadCharacters()
            }
          }}
          onSwitchToRegister={() => {
            setLoginDialogOpen(false)
            setRegisterDialogOpen(true)
          }}
        />

        {/* 注册对话框 */}
        <RegisterDialog
          open={registerDialogOpen}
          onOpenChange={(open) => {
            setRegisterDialogOpen(open)
            // 如果关闭注册对话框且用户已登录，刷新角色列表
            if (!open && isAuthenticated) {
              loadCharacters()
            }
          }}
          onSwitchToLogin={() => {
            setRegisterDialogOpen(false)
            setLoginDialogOpen(true)
          }}
        />
      </div>
    )
  }

  // 正常聊天界面 - 豆包风格
  return (
    <div className="h-full flex flex-col bg-background">
      {/* 返回按钮 - 只在未进行对话时显示 */}
      {messages.length === 0 && selectedCharacter && (
        <div className="p-4 border-b border-border/50">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSelectedCharacter(null)
              setCurrentConversationId(null)
              setMessages([])
              setHasGreeted(false)
              setInputValue('')
              navigate('/chat-mode')
            }}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            返回角色选择
          </Button>
        </div>
      )}
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto bg-background">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">开始与 {selectedCharacter?.name} 对话</h3>
              <p className="text-muted-foreground mb-2">
                {selectedCharacter?.description || '开始你的对话吧！'}
              </p>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto p-4">
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex items-start gap-3",
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {/* AI消息显示头像（在左侧） */}
                  {message.role === 'assistant' && selectedCharacter && (
                    <div className="flex-shrink-0">
                      {selectedCharacter.avatar_url ? (
                        <img
                          src={selectedCharacter.avatar_url}
                          alt={selectedCharacter.name}
                          className="w-10 h-10 rounded-full object-cover border-2 border-primary/20"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center border-2 border-primary/20">
                          <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div
                    className={cn(
                      "max-w-[80%] rounded-lg p-4",
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-foreground'
                    )}
                  >
                    {message.role === 'assistant' ? (
                      <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-foreground prose-strong:text-foreground prose-em:text-foreground prose-code:text-foreground">
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({children}) => <h1 className="text-lg font-bold mb-2 text-foreground">{children}</h1>,
                            h2: ({children}) => <h2 className="text-base font-semibold mb-1 text-foreground">{children}</h2>,
                            h3: ({children}) => <h3 className="text-sm font-medium mb-1 text-foreground">{children}</h3>,
                            p: ({children}) => <p className="mb-2 last:mb-0 text-foreground">{children}</p>,
                            strong: ({children}) => <strong className="font-semibold text-foreground">{children}</strong>,
                            em: ({children}) => <em className="italic text-foreground">{children}</em>,
                            ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1 text-foreground">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1 text-foreground">{children}</ol>,
                            li: ({children}) => <li className="text-sm text-foreground">{children}</li>,
                            code: ({node, inline, className, children, ...props}: any) => {
                              return inline ? (
                                <code className="bg-muted/50 px-1 py-0.5 rounded text-xs font-mono text-foreground" {...props}>
                                  {children}
                                </code>
                              ) : (
                                <code className="block bg-muted/50 p-2 rounded text-xs font-mono text-foreground overflow-x-auto" {...props}>
                                  {children}
                                </code>
                              )
                            },
                            pre: ({children}) => <pre className="bg-muted/50 p-2 rounded text-xs overflow-x-auto text-foreground">{children}</pre>,
                            blockquote: ({children}) => <blockquote className="border-l-4 border-primary/50 pl-4 italic text-foreground">{children}</blockquote>,
                            a: ({children, href}) => <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    )}
                  </div>

                  {/* 用户消息显示头像（在右侧） */}
                  {message.role === 'user' && (
                    <div className="flex-shrink-0">
                      {user?.avatar_url ? (
                        <img
                          src={user.avatar_url}
                          alt={user.username}
                          className="w-10 h-10 rounded-full object-cover border-2 border-primary/20"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center border-2 border-primary/20">
                          <MessageSquare className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* 输入区域 - 豆包风格 */}
      <div className="p-4 bg-background border-t">
        <div className="max-w-4xl mx-auto">
          {/* 豆包输入框 */}
          <div className="bg-card border border-input rounded-2xl px-6 py-4 shadow-lg focus-within:shadow-xl focus-within:border-ring transition-all min-h-[120px] flex flex-col">
            {/* 输入框区域 */}
            <div className="flex-1 mb-3">
              <Textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage()
                  }
                }}
                placeholder={`输入消息与${selectedCharacter?.name || '角色'}对话...`}
                disabled={isSending}
                className="min-h-[60px] max-h-[200px] resize-none border-0 bg-transparent p-0 text-lg placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 w-full"
              />
            </div>
            
            {/* 底部按钮区域 */}
            <div className="flex items-center justify-between pt-2 border-t border-border/50">
              {/* 左侧功能按钮 */}
              <div className="flex items-center gap-2">
                {/* 角色选择器 */}
                {selectedCharacter && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-3 flex items-center gap-2"
                      onClick={() => setIsCharacterDialogOpen(true)}
                    >
                      {selectedCharacter.avatar_url ? (
                        <img
                          src={selectedCharacter.avatar_url}
                          alt={selectedCharacter.name}
                          className="w-6 h-6 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
                          <Users className="h-3 w-3 text-blue-600 dark:text-blue-400" />
                        </div>
                      )}
                      <span className="text-sm">{selectedCharacter.name}</span>
                      <ChevronDown className="h-3 w-3" />
                    </Button>
                    
                    {/* 角色选择对话框 */}
                    <Dialog open={isCharacterDialogOpen} onOpenChange={setIsCharacterDialogOpen}>
                      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                        <DialogHeader>
                          <DialogTitle>切换角色</DialogTitle>
                          <DialogDescription>
                            选择一个角色开始对话
                          </DialogDescription>
                        </DialogHeader>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                          {characters
                            .filter((character) => character.is_usable && !character.is_locked)
                            .sort((a, b) => {
                              const rarityDiff = getRarityOrder(b.rarity) - getRarityOrder(a.rarity)
                              if (rarityDiff !== 0) return rarityDiff
                              return a.name.localeCompare(b.name, 'zh-CN')
                            })
                            .map((character) => (
                            <Card
                              key={character.id}
                              className={cn(
                                "cursor-pointer hover:shadow-md transition-all duration-200 border-2",
                                selectedCharacter?.id === character.id 
                                  ? "border-primary bg-primary/5" 
                                  : "hover:border-primary/50"
                              )}
                              onClick={() => {
                                handleSwitchCharacter(character)
                                setIsCharacterDialogOpen(false)
                              }}
                            >
                              <CardContent className="p-3">
                                <div className="flex items-start gap-3">
                                  {character.avatar_url ? (
                                    <img
                                      src={character.avatar_url}
                                      alt={character.name}
                                      className="w-10 h-10 rounded-full object-cover flex-shrink-0 border-2 border-primary/20"
                                    />
                                  ) : (
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center flex-shrink-0">
                                      <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                    </div>
                                  )}
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                      <h3 className="font-semibold text-sm text-foreground truncate">
                                        {character.name}
                                      </h3>
                                      {selectedCharacter?.id === character.id && (
                                        <Check className="h-4 w-4 text-primary flex-shrink-0" />
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2 mb-1">
                                      <Badge className={`text-xs text-white bg-gradient-to-r ${getRarityColor(character.rarity)}`}>
                                        {getRarityLabel(character.rarity)}
                                      </Badge>
                                      <Badge variant="outline" className="text-xs">
                                        {getCategoryName(character.category)}
                                      </Badge>
                                    </div>
                                    {character.description && (
                                      <p className="text-xs text-muted-foreground line-clamp-2">
                                        {character.description}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                          ))}
                          
                          {/* 获得更多角色卡片 */}
                          <Card
                            className="cursor-pointer hover:shadow-md transition-all duration-200 border-2 border-dashed border-primary/50 hover:border-primary bg-primary/5"
                            onClick={() => {
                              setIsCharacterDialogOpen(false)
                              navigate('/character-management')
                            }}
                          >
                            <CardContent className="p-3">
                              <div className="flex items-center justify-center h-full min-h-[100px] flex-col gap-2">
                                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center border-2 border-primary/30">
                                  <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                                </div>
                                <div className="text-center">
                                  <h3 className="font-semibold text-sm text-foreground mb-1">
                                    获得更多角色
                                  </h3>
                                  <p className="text-xs text-muted-foreground">
                                    解锁更多角色来使用
                                  </p>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </>
                )}
                
                <MultiImageUploader
                  onTextExtracted={(text) => {
                    setInputValue(prev => prev ? `${prev}\n${text}` : text)
                  }}
                  disabled={isSending}
                />
              </div>
              
              {/* 右侧操作按钮 */}
              <div className="flex items-center gap-2">
                {/* 发送按钮 */}
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isSending}
                  size="icon"
                  className="h-8 w-8 rounded-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:text-gray-500 transition-colors"
                  title="发送消息"
                >
                  {isSending ? (
                    <Loader2 className="h-4 w-4 animate-spin text-white" />
                  ) : (
                    <Send className="h-4 w-4 text-white" />
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

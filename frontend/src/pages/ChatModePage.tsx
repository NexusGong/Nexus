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
  User
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

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
  const { user } = useAuthStore()
  
  const [characters, setCharacters] = useState<AICharacter[]>([])
  const [selectedCharacter, setSelectedCharacter] = useState<AICharacter | null>(null)
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [hasGreeted, setHasGreeted] = useState(false)

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 加载角色列表
  useEffect(() => {
    const loadCharacters = async () => {
      try {
        setIsLoading(true)
        const response = await characterApi.getCharacters()
        setCharacters(response.characters || [])
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
    loadCharacters()
  }, [toast])

  // 如果有conversationId，加载对话；如果没有，清除状态并显示角色选择界面
  useEffect(() => {
    if (conversationId) {
      loadConversation(Number(conversationId))
    } else {
      // 当没有conversationId时，清除当前对话状态，显示角色选择界面
      setCurrentConversationId(null)
      setSelectedCharacter(null)
      setMessages([])
      setHasGreeted(false)
      setInputValue('')
    }
  }, [conversationId])

  // 角色选择后加载欢迎语（后端已自动创建）
  useEffect(() => {
    if (selectedCharacter && currentConversationId && messages.length === 0 && !hasGreeted) {
      loadGreeting()
    }
  }, [selectedCharacter, currentConversationId, messages.length, hasGreeted])

  const loadGreeting = async () => {
    if (!selectedCharacter || !currentConversationId || hasGreeted) return

    try {
      // 加载对话消息（包含后端自动创建的欢迎语）
      const messagesResponse = await characterChatApi.getMessages(currentConversationId)
      if (messagesResponse && messagesResponse.length > 0) {
        setMessages(messagesResponse)
        setHasGreeted(true)
      }
    } catch (error) {
      console.error('加载欢迎语失败:', error)
      setHasGreeted(true) // 即使失败也标记为已问候，避免重复尝试
    }
  }

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
        console.log('对话不存在，返回选择页面')
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
    try {
      setIsLoading(true)
      const response = await characterChatApi.createConversation({
        character_id: character.id,
        title: `与${character.name}的对话`
      })
      
      setSelectedCharacter(character)
      setCurrentConversationId(response.id)
      setMessages([])
      setHasGreeted(false)
      
      // 不在这里添加到对话列表，只有在用户成功发送消息后才添加
      
      navigate(`/chat-mode/${response.id}`, { replace: true })
    } catch (error) {
      console.error('创建对话失败:', error)
      toast({
        title: "创建失败",
        description: "无法创建对话",
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
    if (!inputValue.trim() || !currentConversationId || isSending) return

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

    // 不在这里添加到对话列表，只有在消息成功发送后才添加（在onDone回调中）

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
      
      await characterChatApi.sendMessageStream(
        {
          conversation_id: currentConversationId,
          message: userMessage
        },
        // onChunk: 接收流式内容
        (content: string) => {
          fullContent += content
          // 更新AI消息内容
          setMessages(prev => prev.map(msg => 
            msg.id === tempAiMessageId 
              ? { ...msg, content: fullContent }
              : msg
          ))
        },
        // onDone: 流式完成（只有消息成功发送后才添加到最近对话）
        async (messageId: number) => {
          // 更新消息ID为服务器返回的真实ID
          setMessages(prev => prev.map(msg => 
            msg.id === tempAiMessageId 
              ? { ...msg, id: messageId, content: fullContent }
              : msg
          ))
          
          // 消息成功发送后，添加到侧边栏的对话列表
          if (currentConversationId && selectedCharacter) {
            try {
              const convResponse = await characterChatApi.getConversations({ page: 1, size: 100 })
              const conversation = convResponse.conversations?.find((c: any) => c.id === currentConversationId)
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
          // 移除临时消息
          setMessages(prev => prev.filter(m => 
            m.id !== tempUserMessage.id && m.id !== tempAiMessageId
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

  const getCategoryName = (category: string) => {
    switch (category) {
      case 'original':
        return '原创'
      case 'classic':
        return '经典'
      case 'anime':
        return '动漫'
      default:
        return category
    }
  }

  const filteredCharacters = activeCategory === 'all' 
    ? characters 
    : characters.filter(c => c.category === activeCategory)

  const categories = ['all', 'original', 'classic', 'anime']

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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredCharacters.map((character) => (
                  <Card
                    key={character.id}
                    className="cursor-pointer hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-2 hover:border-primary/50"
                    onClick={() => handleSelectCharacter(character)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        {character.avatar_url ? (
                          <img
                            src={character.avatar_url}
                            alt={character.name}
                            className="w-12 h-12 rounded-full object-cover flex-shrink-0 border-2 border-primary/20"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center flex-shrink-0">
                            <Users className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-foreground truncate">{character.name}</h3>
                            <Badge className={`text-xs text-white bg-gradient-to-r ${getRarityColor(character.rarity)}`}>
                              {character.rarity === 'legendary' ? '传说' :
                               character.rarity === 'epic' ? '史诗' :
                               character.rarity === 'rare' ? '稀有' : '普通'}
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
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // 正常聊天界面 - 豆包风格
  return (
    <div className="h-full flex flex-col bg-background">
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
                  <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-3 flex items-center gap-2"
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
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-64">
                      <DropdownMenuLabel>切换角色</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      {characters.map((character) => (
                        <DropdownMenuItem
                          key={character.id}
                          onClick={() => handleSwitchCharacter(character)}
                          className="flex items-center justify-between"
                        >
                          <div className="flex items-center gap-2">
                            {character.avatar_url ? (
                              <img
                                src={character.avatar_url}
                                alt={character.name}
                                className="w-6 h-6 rounded-full object-cover"
                              />
                            ) : (
                              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
                                <Users className="h-3 w-3 text-blue-600 dark:text-blue-400" />
                              </div>
                            )}
                            <div>
                              <div className="font-medium">{character.name}</div>
                              <div className="text-xs text-muted-foreground">{getCategoryName(character.category)}</div>
                            </div>
                          </div>
                          {selectedCharacter?.id === character.id && (
                            <Check className="h-4 w-4" />
                          )}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
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

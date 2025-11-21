import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, Users, Check, ArrowLeft, Lock } from 'lucide-react'
import { characterApi, characterManagementApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'
import UnlockDialog from '@/components/Character/UnlockDialog'
import LoginDialog from '@/components/Auth/LoginDialog'
import RegisterDialog from '@/components/Auth/RegisterDialog'

interface Character {
  id: number
  name: string
  avatar_url?: string
  description?: string
  category: string
  rarity: string
  is_usable?: boolean
  is_locked?: boolean
  owned_at?: string
}

export default function CharacterManagementPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { isAuthenticated } = useAuthStore()
  const [characters, setCharacters] = useState<Character[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [unlockDialogOpen, setUnlockDialogOpen] = useState(false)
  const [characterToUnlock, setCharacterToUnlock] = useState<Character | null>(null)
  const [loginDialogOpen, setLoginDialogOpen] = useState(false)
  const [registerDialogOpen, setRegisterDialogOpen] = useState(false)
  const hasHandledLoginUnlock = useRef(false)

  useEffect(() => {
    loadCharacters()
  }, [isAuthenticated])

  const loadCharacters = async () => {
    try {
      setIsLoading(true)
      // 使用 characterApi 获取角色列表（包含可用性信息）
      const response = await characterApi.getCharacters()
      const charactersList = response.characters || []
      
      // 获取用户已解锁的角色信息（如果已登录）
      if (isAuthenticated) {
        try {
          const myCharactersResponse = await characterManagementApi.getMyCharacters()
          const myCharacters = myCharactersResponse.characters || []
          const ownedMap = new Map(
            myCharacters
              .filter(c => c.is_owned && c.owned_at)
              .map(c => [c.id, c.owned_at])
          )
          
          // 合并解锁时间信息
          charactersList.forEach(char => {
            if (ownedMap.has(char.id)) {
              char.owned_at = ownedMap.get(char.id)
            }
          })
        } catch (error) {
          console.error('获取用户角色信息失败:', error)
        }
      }
      
      setCharacters(charactersList)
    } catch (error: any) {
      console.error('加载角色失败:', error)
      toast({
        title: "加载失败",
        description: error.response?.data?.detail || "无法加载角色列表",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleCharacterClick = (character: Character) => {
    // 检查角色是否锁定
    if (character.is_locked) {
      // 如果角色被锁定，触发解锁流程
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
    
    // 如果角色已解锁，可以在这里添加其他操作（比如查看详情等）
  }

  const handleUnlockSuccess = () => {
    // 解锁成功后刷新角色列表
    loadCharacters()
    setCharacterToUnlock(null)
    hasHandledLoginUnlock.current = false
  }

  // 监听登录状态变化
  useEffect(() => {
    if (isAuthenticated && characterToUnlock && !unlockDialogOpen && !hasHandledLoginUnlock.current) {
      hasHandledLoginUnlock.current = true
      setTimeout(() => {
        setUnlockDialogOpen(true)
      }, 300)
    }
    
    if (!isAuthenticated) {
      hasHandledLoginUnlock.current = false
    }
  }, [isAuthenticated, characterToUnlock, unlockDialogOpen])

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

  const getRarityOrder = (rarity: string) => {
    switch (rarity) {
      case 'legendary': return 4
      case 'epic': return 3
      case 'rare': return 2
      default: return 1
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

  const formatDate = (dateString?: string) => {
    if (!dateString) return ''
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      })
    } catch {
      return ''
    }
  }

  const categories = ['all', 'original', 'classic', 'anime', 'tv_series']

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="flex-1 overflow-y-auto">
        <div className="container mx-auto px-4 py-8 max-w-6xl">
          {/* 头部 */}
          <div className="mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/chat-mode')}
              className="mb-4"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回
            </Button>
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 mb-4">
                <Users className="w-8 h-8 text-purple-600 dark:text-purple-400" />
              </div>
              <h2 className="text-3xl font-bold text-foreground mb-2">角色管理</h2>
              <p className="text-muted-foreground">查看和管理你的角色拥有状态</p>
            </div>
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
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {filteredCharacters.map((character) => {
                const isLocked = character.is_locked ?? false
                const isUsable = character.is_usable ?? false
                return (
                  <Card
                    key={character.id}
                    className={cn(
                      "relative cursor-pointer transition-all duration-200 hover:shadow-md border-2 overflow-hidden",
                      isUsable && !isLocked
                        ? "border-primary/50 hover:border-primary" 
                        : "border-muted/50 opacity-90"
                    )}
                    onClick={() => handleCharacterClick(character)}
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
                                  : "border-primary/20"
                              )}
                            />
                          ) : (
                            <div className={cn(
                              "w-16 h-16 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center border-2 transition-colors relative z-10",
                              isLocked
                                ? "border-primary/30 opacity-85"
                                : "border-primary/20"
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

                        {/* 状态信息 */}
                        <div className="mt-auto relative z-10">
                          {isUsable && !isLocked ? (
                            <div className="space-y-1">
                              <div className="flex items-center justify-center gap-1 text-xs text-primary font-medium">
                                <Check className="h-3 w-3" />
                                已拥有
                              </div>
                              {character.owned_at && (
                                <p className="text-[10px] text-muted-foreground text-center">
                                  解锁于 {formatDate(character.owned_at)}
                                </p>
                              )}
                            </div>
                          ) : (
                            <div className="text-center">
                              <span className="text-xs text-muted-foreground">
                                {!isAuthenticated ? '登录解锁' : '点击解锁'}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* 锁定遮罩 */}
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
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* 解锁对话框 */}
      <UnlockDialog
        open={unlockDialogOpen}
        onOpenChange={(open) => {
          setUnlockDialogOpen(open)
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


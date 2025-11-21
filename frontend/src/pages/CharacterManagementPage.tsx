import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, Users, Check, ArrowLeft } from 'lucide-react'
import { characterManagementApi } from '@/services/api'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

interface Character {
  id: number
  name: string
  avatar_url?: string
  description?: string
  category: string
  rarity: string
  is_owned: boolean
  owned_at?: string
}

export default function CharacterManagementPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [characters, setCharacters] = useState<Character[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState<string>('all')

  useEffect(() => {
    loadCharacters()
  }, [])

  const loadCharacters = async () => {
    try {
      setIsLoading(true)
      const response = await characterManagementApi.getMyCharacters()
      setCharacters(response.characters || [])
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

  const handleOwn = async (characterId: number) => {
    try {
      await characterManagementApi.ownCharacter(characterId)
      toast({
        title: "获得成功",
        description: "角色已获得",
      })
      loadCharacters()
    } catch (error: any) {
      toast({
        title: "获得失败",
        description: error.response?.data?.detail || "获得角色失败",
        variant: "destructive"
      })
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
    const rarityOrder = (r: string) => {
      switch (r) {
        case 'legendary': return 4
        case 'epic': return 3
        case 'rare': return 2
        default: return 1
      }
    }
    const diff = rarityOrder(b.rarity) - rarityOrder(a.rarity)
    if (diff !== 0) return diff
    return a.name.localeCompare(b.name, 'zh-CN')
  })

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
              {filteredCharacters.map((character) => (
                <Card
                  key={character.id}
                  className={cn(
                    "transition-all duration-200 hover:shadow-md border-2 overflow-hidden",
                    character.is_owned 
                      ? "border-primary/50" 
                      : "border-muted opacity-60"
                  )}
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
                              "w-16 h-16 rounded-full object-cover border-2 transition-colors",
                              character.is_owned 
                                ? "border-primary/20" 
                                : "border-muted grayscale"
                            )}
                          />
                        ) : (
                          <div className={cn(
                            "w-16 h-16 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center border-2 transition-colors",
                            character.is_owned 
                              ? "border-primary/20" 
                              : "border-muted grayscale"
                          )}>
                            <Users className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                          </div>
                        )}
                        {/* 稀有度角标 */}
                        <div className={`absolute -top-1 -right-1 w-6 h-6 rounded-full bg-gradient-to-r ${getRarityColor(character.rarity)} flex items-center justify-center border-2 border-background shadow-sm`}>
                          <span className="text-[10px] font-bold text-white leading-none">
                            {getRarityLabel(character.rarity)}
                          </span>
                        </div>
                      </div>
                      
                      {/* 名称 */}
                      <h3 className="font-semibold text-sm text-foreground text-center mb-2 line-clamp-1">
                        {character.name}
                      </h3>
                      
                      {/* 标签 */}
                      <div className="flex items-center justify-center gap-1 mb-2 flex-wrap">
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0.5">
                          {getCategoryName(character.category)}
                        </Badge>
                      </div>
                      
                      {/* 描述 */}
                      {character.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed text-center mb-2 flex-1">
                          {character.description}
                        </p>
                      )}

                      {/* 拥有状态 */}
                      <div className="mt-auto">
                        {character.is_owned ? (
                          <div className="flex items-center justify-center gap-1 text-xs text-primary font-medium">
                            <Check className="h-3 w-3" />
                            已拥有
                          </div>
                        ) : (
                          <Button
                            size="sm"
                            className="w-full text-xs"
                            onClick={() => handleOwn(character.id)}
                          >
                            获得角色
                          </Button>
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


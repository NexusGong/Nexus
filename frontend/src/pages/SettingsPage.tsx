import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useAuthStore } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'
import { User, Edit, Globe, Monitor, Moon, Sun, X, Camera, Users } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { authApi } from '@/services/api'

export default function SettingsPage() {
  const { user, setUser } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const { toast } = useToast()
  const navigate = useNavigate()
  const [username, setUsername] = useState(user?.username || '')
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSaveProfile = async () => {
    if (!username.trim() || username.trim().length < 2) {
      toast({
        title: "用户名无效",
        description: "用户名至少需要2个字符",
        variant: "destructive",
        duration: 500
      })
      return
    }

    setIsSaving(true)
    try {
      const updatedUser = await authApi.updateProfile({ username: username.trim() })
      setUser(updatedUser)
      
      toast({
        title: "保存成功",
        description: "个人资料已更新",
        duration: 500
      })
      setIsEditing(false)
    } catch (error: any) {
      toast({
        title: "保存失败",
        description: error.response?.data?.detail || "更新个人资料失败",
        variant: "destructive",
        duration: 500
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleAvatarClick = () => {
    fileInputRef.current?.click()
  }

  // 压缩图片
  const compressImage = (file: File, maxWidth: number = 400, maxHeight: number = 400, quality: number = 0.8): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const img = new Image()
        img.onload = () => {
          const canvas = document.createElement('canvas')
          let width = img.width
          let height = img.height

          // 计算压缩后的尺寸
          if (width > height) {
            if (width > maxWidth) {
              height = (height * maxWidth) / width
              width = maxWidth
            }
          } else {
            if (height > maxHeight) {
              width = (width * maxHeight) / height
              height = maxHeight
            }
          }

          canvas.width = width
          canvas.height = height

          const ctx = canvas.getContext('2d')
          if (!ctx) {
            reject(new Error('无法创建画布'))
            return
          }

          // 绘制压缩后的图片
          ctx.drawImage(img, 0, 0, width, height)

          // 转换为base64
          const base64String = canvas.toDataURL('image/jpeg', quality)
          resolve(base64String)
        }
        img.onerror = () => reject(new Error('图片加载失败'))
        img.src = e.target?.result as string
      }
      reader.onerror = () => reject(new Error('文件读取失败'))
      reader.readAsDataURL(file)
    })
  }

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      toast({
        title: "文件类型错误",
        description: "请选择图片文件",
        variant: "destructive",
        duration: 500
      })
      return
    }

    // 验证文件大小（最大10MB，压缩后会变小）
    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: "文件过大",
        description: "图片大小不能超过10MB",
        variant: "destructive",
        duration: 500
      })
      return
    }

    // 检查是否已登录
    const { isAuthenticated } = useAuthStore.getState()
    if (!isAuthenticated) {
      toast({
        title: "未登录",
        description: "请先登录后再上传头像",
        variant: "destructive",
        duration: 500
      })
      return
    }

    setIsUploadingAvatar(true)
    try {
      // 压缩图片并转换为base64
      const base64String = await compressImage(file)
      
      // 检查压缩后的base64字符串长度（限制在100KB以内）
      if (base64String.length > 100000) {
        // 如果还是太大，使用更低的压缩质量
        const compressedBase64 = await compressImage(file, 300, 300, 0.6)
        if (compressedBase64.length > 100000) {
          toast({
            title: "图片过大",
            description: "图片压缩后仍然过大，请选择更小的图片",
            variant: "destructive",
            duration: 500
          })
          setIsUploadingAvatar(false)
          return
        }
        
        // 上传压缩后的图片
        const updatedUser = await authApi.updateProfile({ avatar_url: compressedBase64 })
        setUser(updatedUser)
        toast({
          title: "头像更新成功",
          description: "头像已更新",
          duration: 500
        })
      } else {
        // 上传压缩后的图片
        const updatedUser = await authApi.updateProfile({ avatar_url: base64String })
        setUser(updatedUser)
        toast({
          title: "头像更新成功",
          description: "头像已更新",
          duration: 500
        })
      }
    } catch (error: any) {
      if (error.response?.status === 401) {
        toast({
          title: "认证失败",
          description: "登录已过期，请重新登录",
          variant: "destructive",
          duration: 500
        })
      } else if (error.response?.status === 422) {
        toast({
          title: "头像更新失败",
          description: "图片格式不正确或数据过大，请重试",
          variant: "destructive",
          duration: 500
        })
      } else {
        toast({
          title: "头像更新失败",
          description: error.response?.data?.detail || error.message || "更新头像失败",
          variant: "destructive",
          duration: 500
        })
      }
    } finally {
      setIsUploadingAvatar(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">设置</h1>
          <p className="text-muted-foreground">管理您的账户设置和偏好</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/')}
          className="h-9 w-9"
          title="返回主页"
        >
          <X className="h-5 w-5" />
        </Button>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="profile">个人资料</TabsTrigger>
          <TabsTrigger value="preferences">偏好设置</TabsTrigger>
          <TabsTrigger value="device">设备</TabsTrigger>
          <TabsTrigger value="characters">角色管理</TabsTrigger>
        </TabsList>

        {/* 个人资料 */}
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                个人资料
              </CardTitle>
              <CardDescription>
                管理您的个人信息和账户设置
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 头像上传 */}
              <div className="space-y-2">
                <label className="text-sm font-medium">头像</label>
                <div className="flex items-center gap-4">
                  <div className="relative">
                    {user?.avatar_url ? (
                      <img
                        src={user.avatar_url}
                        alt={user.username}
                        className="h-20 w-20 rounded-full object-cover border-2 border-border"
                      />
                    ) : (
                      <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center border-2 border-border">
                        <User className="h-10 w-10 text-primary" />
                      </div>
                    )}
                    {isUploadingAvatar && (
                      <div className="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center">
                        <div className="h-6 w-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleAvatarClick}
                      disabled={isUploadingAvatar}
                      className="flex items-center gap-2"
                    >
                      <Camera className="h-4 w-4" />
                      更换头像
                    </Button>
                    <p className="text-xs text-muted-foreground">
                      支持 JPG、PNG 格式，最大 5MB
                    </p>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarChange}
                    className="hidden"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">用户名</label>
                {isEditing ? (
                  <div className="flex items-center gap-2">
                    <Input
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      disabled={isSaving}
                      maxLength={50}
                      className="flex-1"
                    />
                    <Button
                      onClick={handleSaveProfile}
                      disabled={isSaving}
                      size="sm"
                    >
                      {isSaving ? '保存中...' : '保存'}
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setUsername(user?.username || '')
                        setIsEditing(false)
                      }}
                      disabled={isSaving}
                      size="sm"
                    >
                      取消
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-foreground">{user?.username}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsEditing(true)}
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      编辑
                    </Button>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">邮箱</label>
                <p className="text-sm text-muted-foreground">
                  {user?.email || '未设置'}
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">手机号</label>
                <p className="text-sm text-muted-foreground">
                  {user?.phone || '未设置'}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 偏好设置 */}
        <TabsContent value="preferences">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                偏好设置
              </CardTitle>
              <CardDescription>
                自定义您的使用体验
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <label className="text-sm font-medium">主题模式</label>
                  <p className="text-sm text-muted-foreground">
                    选择浅色或深色主题
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={toggleTheme}
                  className="flex items-center gap-2"
                >
                  {theme === 'dark' ? (
                    <>
                      <Moon className="h-4 w-4" />
                      深色模式
                    </>
                  ) : (
                    <>
                      <Sun className="h-4 w-4" />
                      浅色模式
                    </>
                  )}
                </Button>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <label className="text-sm font-medium">语言</label>
                  <p className="text-sm text-muted-foreground">
                    选择界面显示语言
                  </p>
                </div>
                <Button variant="outline" disabled>
                  简体中文
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 设备 */}
        <TabsContent value="device">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="h-5 w-5" />
                设备
              </CardTitle>
              <CardDescription>
                管理您的设备信息
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">当前设备</label>
                <p className="text-sm text-muted-foreground">
                  {navigator.userAgent.includes('Mac') ? 'macOS' : 
                   navigator.userAgent.includes('Win') ? 'Windows' : 
                   navigator.userAgent.includes('Linux') ? 'Linux' : '未知'}
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">浏览器</label>
                <p className="text-sm text-muted-foreground">
                  {navigator.userAgent.includes('Chrome') ? 'Chrome' : 
                   navigator.userAgent.includes('Firefox') ? 'Firefox' : 
                   navigator.userAgent.includes('Safari') ? 'Safari' : '未知'}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 角色管理 */}
        <TabsContent value="characters">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                角色管理
              </CardTitle>
              <CardDescription>
                管理您的AI角色拥有状态
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  在这里您可以查看和管理所有AI角色的拥有状态。已拥有的角色可以在自由交谈模式中使用。
                </p>
                <Button
                  onClick={() => navigate('/character-management')}
                  className="w-full sm:w-auto"
                >
                  <Users className="h-4 w-4 mr-2" />
                  前往角色管理
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}


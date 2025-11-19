import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Bell } from 'lucide-react'
import { useThemeStore } from '@/store/themeStore'
import { useAuthStore } from '@/store/authStore'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/services/api'
import LoginDialog from '@/components/Auth/LoginDialog'
import RegisterDialog from '@/components/Auth/RegisterDialog'
import UserMenu from '@/components/UserMenu'

export default function Header() {
  const { theme, toggleTheme } = useThemeStore()
  const { user, isAuthenticated, setUser } = useAuthStore()
  const navigate = useNavigate()
  const [showLogin, setShowLogin] = useState(false)
  const [showRegister, setShowRegister] = useState(false)

  // 初始化时恢复登录状态
  useEffect(() => {
    const initAuth = async () => {
      const { token, user: currentUser, isAuthenticated } = useAuthStore.getState()
      const storedToken = localStorage.getItem('auth_token')
      
      // 如果 localStorage 中有 token 但 store 中没有，同步 token
      if (storedToken && !token) {
        useAuthStore.getState().setToken(storedToken)
      }
      
      // 如果有 token（无论是存储的还是恢复的），都需要验证 token 是否有效
      // 即使 currentUser 存在，也可能是因为从持久化存储恢复的，token 可能已过期
      const tokenToVerify = storedToken || token
      if (tokenToVerify) {
        try {
          // 验证 token 并获取用户信息
          const userInfo = await authApi.getMe()
          // 如果获取成功，更新用户信息
          useAuthStore.getState().setUser(userInfo)
          // 获取使用统计
          try {
            const stats = await authApi.getUsageStats()
            useAuthStore.getState().setUsageStats(stats)
          } catch (error) {
            console.error('获取使用统计失败:', error)
          }
        } catch (error: any) {
          // token 无效或过期，清除状态
          console.warn('Token验证失败，清除登录状态:', error)
          if (error.response?.status === 401 || error.response?.status === 403 || (error as any).isTokenExpired) {
            localStorage.removeItem('auth_token')
            useAuthStore.getState().logout()
            console.warn('Token已过期或无效，已清除登录状态')
          }
        }
      } else if (currentUser || isAuthenticated) {
        // 如果没有 token 但显示为已登录，清除登录状态
        console.warn('检测到没有token但显示为已登录，清除登录状态')
        useAuthStore.getState().logout()
      }
    }
    initAuth()
  }, [setUser])

  const handleSwitchToRegister = () => {
    setShowLogin(false)
    setShowRegister(true)
  }

  const handleSwitchToLogin = () => {
    setShowRegister(false)
    setShowLogin(true)
  }

  return (
    <>
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex h-14 items-center justify-between px-6">
          {/* 左侧标题区域 */}
          <div className="flex items-center gap-4">
          </div>

          {/* 右侧用户操作区域 */}
          <div className="flex items-center gap-3 text-foreground">
            {/* 主题切换按钮 */}
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-9 w-9 text-foreground hover:text-foreground"
              onClick={toggleTheme}
              title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
              aria-label={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
            >
              {theme === 'dark' ? (
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="5"/>
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </svg>
              ) : (
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </Button>

            {/* 通知按钮 */}
            <Button variant="ghost" size="icon" className="h-9 w-9 text-foreground" title="通知" aria-label="通知">
              <Bell className="h-4 w-4" />
            </Button>

            {/* 用户区域 */}
            <div className="flex items-center gap-2 pl-2 border-l">
              {isAuthenticated && user ? (
                <UserMenu user={user} />
              ) : (
                <div className="flex items-center gap-2">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setShowLogin(true)}
                    className="text-foreground"
                  >
                    登录
                  </Button>
                  <Button 
                    variant="default" 
                    size="sm"
                    onClick={() => setShowRegister(true)}
                  >
                    注册
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <LoginDialog 
        open={showLogin} 
        onOpenChange={setShowLogin}
        onSwitchToRegister={handleSwitchToRegister}
      />
      <RegisterDialog 
        open={showRegister} 
        onOpenChange={setShowRegister}
        onSwitchToLogin={handleSwitchToLogin}
      />
    </>
  )
}

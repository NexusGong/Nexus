import { Button } from '@/components/ui/button'
import { Bell, User, Settings } from 'lucide-react'
import { useThemeStore } from '@/store/themeStore'
import { useNavigate } from 'react-router-dom'

export default function Header() {
  const { theme, toggleTheme } = useThemeStore()
  const navigate = useNavigate()

  const handleSettingsClick = () => {
    navigate('/settings')
  }

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-6">
        {/* 左侧标题区域 */}
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-foreground">
            对话意图智能分析
          </h1>
        </div>

        {/* 右侧用户操作区域 */}
        <div className="flex items-center gap-3">
          {/* 主题切换按钮 */}
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-9 w-9"
            onClick={toggleTheme}
            title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
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
          <Button variant="ghost" size="icon" className="h-9 w-9" title="通知">
            <Bell className="h-4 w-4" />
          </Button>

          {/* 设置按钮 */}
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-9 w-9" 
            title="设置"
            onClick={handleSettingsClick}
          >
            <Settings className="h-4 w-4" />
          </Button>

          {/* 用户头像 */}
          <div className="flex items-center gap-2 pl-2 border-l">
            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full" title="用户菜单">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="h-4 w-4 text-primary" />
              </div>
            </Button>
          </div>
        </div>
      </div>
    </header>
  )
}

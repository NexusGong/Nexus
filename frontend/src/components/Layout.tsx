import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import { useThemeStore } from '@/store/themeStore'

export default function Layout() {
  const { theme } = useThemeStore()
  
  // 在 html 根元素上切换主题，并在切换瞬间禁用过渡，确保全局渲染速度一致
  // 这样不会影响 hover/交互动效，仅在主题切换时统一“瞬时”完成
  useEffect(() => {
    const root = document.documentElement
    // 禁用过渡
    root.classList.add('theme-changing')
    // 应用主题类
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    // 两帧后恢复过渡，避免长时间禁用
    const id = window.setTimeout(() => {
      root.classList.remove('theme-changing')
    }, 120)
    return () => window.clearTimeout(id)
  }, [theme])

  return (
    <div className={`min-h-screen bg-background`}>
      <div className="flex h-screen">
        {/* 侧边栏 */}
        <Sidebar />
        
        {/* 主内容区域 */}
        <div className="flex-1 flex flex-col">
          <Header />
          <main className="flex-1 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}

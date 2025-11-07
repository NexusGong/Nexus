import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  username: string
  email?: string
  phone?: string
  avatar_url?: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login_at?: string
}

interface UsageStats {
  ocr_fast: {
    used: number
    limit: number
    remaining: number
  }
  ocr_quality: {
    used: number
    limit: number
    remaining: number
  }
  conversation: {
    count: number
    limit: number
    remaining: number
  }
  chat_analysis: {
    used: number
    limit: number
    remaining: number
  }
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  usageStats: UsageStats | null
  sessionToken: string | null
  
  // Actions
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setUsageStats: (stats: UsageStats | null) => void
  login: (token: string, user: User) => void
  logout: () => void
  generateSessionToken: () => string
  getSessionToken: () => string
}

// 生成唯一的session token
function generateSessionToken(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      usageStats: null,
      sessionToken: null,
      
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => {
        if (token) {
          localStorage.setItem('auth_token', token)
        } else {
          localStorage.removeItem('auth_token')
        }
        set({ token })
      },
      setUsageStats: (stats) => set({ usageStats: stats }),
      
      login: (token, user) => {
        localStorage.setItem('auth_token', token)
        set({ 
          token, 
          user, 
          isAuthenticated: true 
        })
      },
      
      logout: () => {
        localStorage.removeItem('auth_token')
        set({ 
          token: null, 
          user: null, 
          isAuthenticated: false,
          usageStats: null
        })
        // 清除对话和卡片数据
        // 注意：这里需要导入 useChatStore，但由于循环依赖问题，我们在 UserMenu 中处理
      },
      
      generateSessionToken: () => {
        const token = generateSessionToken()
        set({ sessionToken: token })
        return token
      },
      
      getSessionToken: () => {
        const state = get()
        if (state.sessionToken) {
          return state.sessionToken
        }
        // 如果还没有session token，生成一个
        const token = generateSessionToken()
        set({ sessionToken: token })
        return token
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
        sessionToken: state.sessionToken
      }),
      onRehydrateStorage: () => (state) => {
        // 恢复状态后，同步 localStorage 中的 token
        if (state?.token) {
          localStorage.setItem('auth_token', state.token)
        } else {
          localStorage.removeItem('auth_token')
        }
        // 如果 token 存在但 user 不存在，需要验证 token 并获取用户信息
        if (state?.token && !state?.user) {
          // 这里会在 Header 组件中处理
        }
      }
    }
  )
)


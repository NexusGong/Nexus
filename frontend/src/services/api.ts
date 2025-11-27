import axios from 'axios'
import type { 
  Conversation, 
  Message, 
  AnalysisResult, 
  ResponseSuggestion 
} from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // 增加到2分钟，给AI分析更多时间
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 添加session token（非登录用户使用）
    const authStore = useAuthStore.getState()
    const sessionToken = authStore.getSessionToken()
    if (sessionToken) {
      config.headers['X-Session-Token'] = sessionToken
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API请求错误:', error)
    
    // 处理401错误（未授权）和403错误（token过期导致的权限问题）
    if (error.response?.status === 401 || error.response?.status === 403) {
      const url = error.config?.url || ''
      const errorDetail = error.response?.data?.detail || ''
      
      // 检查是否是token过期导致的错误
      const isTokenExpired = errorDetail.includes('已过期') || 
                            errorDetail.includes('expired') ||
                            errorDetail.includes('Signature has expired')
      
      // 如果是token过期，或者是在获取用户信息时失败，清除token并退出登录
      if (isTokenExpired || url.includes('/auth/me')) {
        // 清除过期的token
        localStorage.removeItem('auth_token')
        // 清除用户状态
        const authStore = useAuthStore.getState()
        authStore.logout()
        console.warn('Token已过期或无效，已自动退出登录')
        
        // 如果是token过期，不显示错误提示（因为会自动退出登录）
        // 其他401错误正常显示
        if (!isTokenExpired && error.response?.status === 401) {
          return Promise.reject(error)
        }
        
        // token过期时，返回一个特殊的错误，让调用方知道是token过期
        const tokenExpiredError = new Error('Token已过期，请重新登录')
        ;(tokenExpiredError as any).isTokenExpired = true
        return Promise.reject(tokenExpiredError)
      }
    }
    
    return Promise.reject(error)
  }
)

// 对话相关API
export const conversationApi = {
  // 创建对话
  createConversation: async (data: {
    title: string
    description?: string
    context_mode?: string
    analysis_focus?: any
  }): Promise<Conversation> => {
    const response = await api.post('/chat/conversations', data)
    return response.data
  },

  // 获取对话列表
  getConversations: async (page = 1, size = 20): Promise<{
    conversations: Conversation[]
    total: number
    page: number
    size: number
  }> => {
    const response = await api.get('/chat/conversations', {
      params: { page, size }
    })
    return response.data
  },

  // 获取对话详情
  getConversation: async (conversationId: number): Promise<Conversation> => {
    const response = await api.get(`/chat/conversations/${conversationId}`)
    return response.data
  },

  // 获取对话消息
  getMessages: async (
    conversationId: number, 
    page = 1, 
    size = 50
  ): Promise<Message[]> => {
    const response = await api.get(`/chat/conversations/${conversationId}/messages`, {
      params: { page, size }
    })
    return response.data
  },

  // 更新对话
  updateConversation: async (
    conversationId: number,
    data: {
      title?: string
      description?: string
      context_mode?: string
      analysis_focus?: any
    }
  ): Promise<Conversation> => {
    const response = await api.put(`/chat/conversations/${conversationId}`, data)
    return response.data
  },

  // 删除对话
  deleteConversation: async (conversationId: number): Promise<{ message: string }> => {
    const response = await api.delete(`/chat/conversations/${conversationId}`)
    return response.data
  },
}

// 聊天分析API
export const chatApi = {
  // 分析聊天内容
  analyzeChat: async (data: {
    conversation_id: number
    message: string
    context_mode?: string
    analysis_focus?: any
  }): Promise<{
    message: Message
    analysis: AnalysisResult
    suggestions: ResponseSuggestion[]
  }> => {
    const response = await api.post('/chat/analyze', data)
    return response.data
  },

  // 卡片模式：分析聊天内容（不保存对话）
  analyzeChatCardMode: async (data: {
    message: string
    context_mode?: string
  }): Promise<{
    message: Message
    analysis: AnalysisResult
    suggestions: ResponseSuggestion[]
  }> => {
    const response = await api.post('/chat/analyze-card-mode', data)
    return response.data
  },

  // OCR识别（单张图片）
  extractTextFromImage: async (file: File): Promise<{
    text: string
    confidence: number
    language: string
    metadata: any
  }> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post('/chat/ocr', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // OCR识别（多张图片批量）
  extractTextFromImages: async (files: File[], mode: string = 'fast', signal?: AbortSignal): Promise<{
    text: string
    confidence: number
    language: string
    metadata: any
  }> => {
    const formData = new FormData()
    files.forEach((file, index) => {
      formData.append(`files`, file)
    })
    formData.append('mode', mode)
    
    const response = await api.post('/chat/ocr/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      signal,
    })
    return response.data
  },
}

// 分析卡片API
export const cardApi = {
  // 创建分析卡片
  createCard: async (data: {
    title: string
    description?: string
    original_content: string
    analysis_data: AnalysisResult
    response_suggestions?: ResponseSuggestion[]
    context_mode?: string
    card_template?: string
    conversation_id?: number | null
  }) => {
    const response = await api.post('/cards/', data)
    return response.data
  },

  // 获取卡片列表
  getCards: async (params: {
    page?: number
    size?: number
    tags?: string
    is_favorite?: boolean
  } = {}) => {
    const response = await api.get('/cards/', { params })
    return response.data
  },

  // 获取卡片详情
  getCard: async (cardId: number) => {
    const response = await api.get(`/cards/${cardId}`)
    return response.data
  },

  // 更新卡片
  updateCard: async (cardId: number, data: {
    title?: string
    description?: string
    is_favorite?: boolean
    is_public?: boolean
    tags?: string[]
  }) => {
    const response = await api.put(`/cards/${cardId}`, data)
    return response.data
  },

  // 删除卡片
  deleteCard: async (cardId: number) => {
    const response = await api.delete(`/cards/${cardId}`)
    return response.data
  },

  // 导出卡片为图片
  exportCardAsImage: async (cardId: number): Promise<Blob> => {
    const response = await api.get(`/cards/${cardId}/export/image`, {
      responseType: 'blob',
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    })
    return response.data
  },

  // 导出卡片为PDF（已下线）
}

// 认证相关API
export const authApi = {
  // 发送验证码
  sendCode: async (data: {
    contact: string
    code_type: 'register' | 'login'
  }) => {
    const response = await api.post('/auth/send-code', data)
    return response.data
  },

  // 注册
  register: async (data: {
    contact: string
    code: string
    username: string
  }) => {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  // 登录
  login: async (data: {
    contact: string
    code: string
  }) => {
    const response = await api.post('/auth/login', data)
    return response.data
  },

  // 获取当前用户信息
  getMe: async () => {
    const response = await api.get('/auth/me')
    return response.data
  },

  // 获取使用统计
  getUsageStats: async () => {
    const response = await api.get('/auth/usage-stats')
    return response.data
  },

  // 更新用户资料
  updateProfile: async (data: {
    username?: string
    avatar_url?: string
  }) => {
    const response = await api.put('/auth/profile', data)
    return response.data
  },
}

// AI角色API
export const characterApi = {
  // 获取角色列表
  getCharacters: async (category?: string) => {
    const response = await api.get('/characters/', {
      params: category ? { category } : {}
    })
    return response.data
  },

  // 获取角色详情
  getCharacter: async (characterId: number) => {
    const response = await api.get(`/characters/${characterId}`)
    return response.data
  },
}

// 角色管理API
export const characterManagementApi = {
  // 获取我的角色列表（包含拥有状态）
  getMyCharacters: async () => {
    const response = await api.get('/character-management/my-characters')
    return response.data
  },

  // 获得角色（拥有角色）
  ownCharacter: async (characterId: number) => {
    const response = await api.post(`/character-management/own/${characterId}`)
    return response.data
  },
}

// 支付API
export const paymentApi = {
  // 获取角色价格
  getCharacterPrice: async (characterId: number) => {
    const response = await api.get(`/payment/character-price/${characterId}`)
    return response.data
  },

  // 购买角色（解锁角色）
  purchaseCharacter: async (characterId: number) => {
    const response = await api.post(`/payment/purchase-character/${characterId}`)
    return response.data
  },
}

// 卡片模式API
export const cardModeApi = {
  // 生成卡片
  generateCard: async (data: {
    source?: string
    user_history_id?: number
  }) => {
    const response = await api.post('/card-mode/generate', data)
    return response.data
  },
}

// 角色对话API
export const characterChatApi = {
  // 创建角色对话
  createConversation: async (data: {
    character_id: number
    title?: string
  }) => {
    const response = await api.post('/character-chat/conversations', data)
    return response.data
  },

  // 创建角色对话并流式返回欢迎语
  createConversationStream: async (
    data: {
      character_id: number
      title?: string
    },
    onChunk: (greeting: string, conversationId: number, done: boolean) => void,
    onError: (error: string) => void
  ): Promise<void> => {
    const token = localStorage.getItem('auth_token')
    const authStore = useAuthStore.getState()
    const sessionToken = authStore.getSessionToken()
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
    
    if (sessionToken) {
      headers['X-Session-Token'] = sessionToken
    }
    
    const response = await fetch('/api/character-chat/conversations/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '请求失败' }))
      onError(error.detail || '请求失败')
      return
    }
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) {
      onError('无法读取响应流')
      return
    }
    
    let buffer = ''
    let conversationId = 0
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.error) {
              onError(data.error)
              return
            }
            
            if (data.greeting && data.conversation_id) {
              conversationId = data.conversation_id
              onChunk(data.greeting, conversationId, data.done || false)
            }
          } catch (e) {
            console.error('解析流数据失败:', e)
          }
        }
      }
    }
  },

  // 获取角色对话列表
  getConversations: async (params: {
    page?: number
    size?: number
  } = {}) => {
    const response = await api.get('/character-chat/conversations', { params })
    return response.data
  },

  // 删除角色对话
  deleteConversation: async (conversationId: number): Promise<{ message: string }> => {
    const response = await api.delete(`/character-chat/conversations/${conversationId}`)
    return response.data
  },

  // 发送消息给角色（流式）
  sendMessageStream: async (
    data: {
      conversation_id?: number
      character_id?: number
      message: string
    },
    onChunk: (content: string, isGreeting?: boolean) => void,
    onDone: (messageId: number, conversationId?: number) => void,
    onError: (error: string) => void
  ): Promise<void> => {
    const token = localStorage.getItem('auth_token')
    const authStore = useAuthStore.getState()
    const sessionToken = authStore.getSessionToken()
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
    
    if (sessionToken) {
      headers['X-Session-Token'] = sessionToken
    }
    
    const response = await fetch('/api/character-chat/messages/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '请求失败' }))
      onError(error.detail || '请求失败')
      return
    }
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) {
      onError('无法读取响应流')
      return
    }
    
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.error) {
              onError(data.error)
              return
            }
            
            if (data.greeting) {
              onChunk(data.greeting, true)
            }
            
            if (data.content) {
              onChunk(data.content, false)
            }
            
            if (data.done && data.message_id) {
              onDone(data.message_id, data.conversation_id)
              return
            }
          } catch (e) {
            console.error('解析流数据失败:', e)
          }
        }
      }
    }
  },

  // 发送消息给角色（非流式，保留作为备用）
  sendMessage: async (data: {
    conversation_id: number
    message: string
  }) => {
    const response = await api.post('/character-chat/messages', data)
    return response.data
  },

  // 获取对话消息列表
  getMessages: async (conversationId: number, params: {
    page?: number
    size?: number
  } = {}) => {
    const response = await api.get(`/character-chat/conversations/${conversationId}/messages`, { params })
    return response.data
  },

  // 从对话生成卡片
  generateCard: async (data: {
    conversation_id: number
    title?: string
  }) => {
    const response = await api.post('/character-chat/generate-card', data)
    return response.data
  },
}

// 健康检查API
export const healthApi = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
}

export default api

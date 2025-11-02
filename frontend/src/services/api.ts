import axios from 'axios'
import type { 
  Conversation, 
  Message, 
  AnalysisResult, 
  ResponseSuggestion 
} from '@/store/chatStore'

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
    // 可以在这里添加认证token
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
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
  extractTextFromImages: async (files: File[], mode: string = 'fast'): Promise<{
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
    conversation_id: number
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

// 健康检查API
export const healthApi = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
}

export default api

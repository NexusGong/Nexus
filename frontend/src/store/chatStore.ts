import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  message_type: string
  source?: string
  image_url?: string
  image_ocr_result?: string
  analysis_result?: any
  analysis_metadata?: any
  is_processed: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface Conversation {
  id: number
  title: string
  description?: string
  context_mode: string
  analysis_focus?: any
  is_active: string
  message_count: number
  analysis_count: number
  created_at: string
  updated_at: string
  last_message_at?: string
}

export interface AnalysisResult {
  intent: {
    primary: string
    secondary: string[]
    confidence: number
    description: string
  }
  sentiment: {
    overall: string
    intensity: number
    emotions: string[]
    description: string
  }
  tone: {
    style: string
    politeness: string
    confidence: number
    description: string
  }
  relationship: {
    closeness: string
    power_dynamic: string
    trust_level: string
    description: string
  }
  subtext: {
    hidden_meanings: string[]
    implications: string[]
    description: string
  }
  key_points: string[]
  context_analysis: {
    urgency: string
    sensitivity: string
    background: string
    description: string
  }
}

export interface ResponseSuggestion {
  type: string
  title: string
  description: string
  examples: string[]
}

interface ChatState {
  // 当前对话
  currentConversation: Conversation | null
  currentMessages: Message[]
  
  // 对话列表
  conversations: Conversation[]
  
  // 分析结果
  currentAnalysis: AnalysisResult | null
  currentSuggestions: ResponseSuggestion[]
  
  // 加载状态
  isLoading: boolean
  isAnalyzing: boolean
  isUploading: boolean
  
  // 错误状态
  error: string | null
  
  // Actions
  setCurrentConversation: (conversation: Conversation | null) => void
  setCurrentMessages: (messages: Message[]) => void
  addMessage: (message: Message) => void
  setConversations: (conversations: Conversation[]) => void
  addConversation: (conversation: Conversation) => void
  updateConversation: (conversationId: number, updates: Partial<Conversation>) => void
  removeConversation: (conversationId: number) => void
  setCurrentAnalysis: (analysis: AnalysisResult | null) => void
  setCurrentSuggestions: (suggestions: ResponseSuggestion[]) => void
  setLoading: (loading: boolean) => void
  setAnalyzing: (analyzing: boolean) => void
  setUploading: (uploading: boolean) => void
  setError: (error: string | null) => void
  clearCurrentChat: () => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // 初始状态
      currentConversation: null,
      currentMessages: [],
      conversations: [],
      currentAnalysis: null,
      currentSuggestions: [],
      isLoading: false,
      isAnalyzing: false,
      isUploading: false,
      error: null,
      
      // Actions
      setCurrentConversation: (conversation) => set({ currentConversation: conversation }),
      setCurrentMessages: (messages) => set({ currentMessages: messages }),
      addMessage: (message) => set((state) => ({ 
        currentMessages: [...state.currentMessages, message] 
      })),
      setConversations: (conversations) => set({ conversations: Array.isArray(conversations) ? conversations : [] }),
      addConversation: (conversation) => set((state) => {
        const existingConversations = Array.isArray(state.conversations) ? state.conversations : []
        // 检查是否已存在，避免重复添加
        const exists = existingConversations.some(conv => conv.id === conversation.id)
        if (exists) {
          return state
        }
        // 将新对话添加到列表顶部
        return { conversations: [conversation, ...existingConversations] }
      }),
      updateConversation: (conversationId, updates) => set((state) => ({
        conversations: Array.isArray(state.conversations) 
          ? state.conversations.map(conv => 
              conv.id === conversationId ? { ...conv, ...updates } : conv
            )
          : [],
        currentConversation: state.currentConversation?.id === conversationId 
          ? { ...state.currentConversation, ...updates }
          : state.currentConversation
      })),
      removeConversation: (conversationId) => set((state) => ({
        conversations: Array.isArray(state.conversations) 
          ? state.conversations.filter(conv => conv.id !== conversationId)
          : [],
        currentConversation: state.currentConversation?.id === conversationId 
          ? null 
          : state.currentConversation
      })),
      setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
      setCurrentSuggestions: (suggestions) => set({ currentSuggestions: suggestions }),
      setLoading: (loading) => set({ isLoading: loading }),
      setAnalyzing: (analyzing) => set({ isAnalyzing: analyzing }),
      setUploading: (uploading) => set({ isUploading: uploading }),
      setError: (error) => set({ error }),
      clearCurrentChat: () => set({ 
        currentConversation: null, 
        currentMessages: [], 
        currentAnalysis: null, 
        currentSuggestions: [],
        error: null 
      }),
    }),
    {
      name: 'nexus-chat-storage',
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversation: state.currentConversation,
      }),
    }
  )
)


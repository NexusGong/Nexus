import { Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import Layout from '@/components/Layout'
import HomePage from '@/pages/HomePage'
import ChatPage from '@/pages/ChatPage'
import CardsPage from '@/pages/CardsPage'
import SettingsPage from '@/pages/SettingsPage'
import CardModePage from '@/pages/CardModePage'
import ChatModePage from '@/pages/ChatModePage'
import { useThemeStore } from '@/store/themeStore'

function App() {
  const { theme } = useThemeStore()

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'dark' : ''}`}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="chat/:conversationId" element={<ChatPage />} />
          <Route path="cards" element={<CardsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="card-mode" element={<CardModePage />} />
          <Route path="chat-mode" element={<ChatModePage />} />
          <Route path="chat-mode/:conversationId" element={<ChatModePage />} />
        </Route>
      </Routes>
      <Toaster />
    </div>
  )
}

export default App


import { Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import Layout from '@/components/Layout'
import HomePage from '@/pages/HomePage'
import ChatPage from '@/pages/ChatPage'
import CardsPage from '@/pages/CardsPage'
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
        </Route>
      </Routes>
      <Toaster />
    </div>
  )
}

export default App


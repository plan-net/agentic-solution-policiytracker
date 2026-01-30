import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import SlideOutPanel from './components/layout/SlideOutPanel'
import HomePage from './pages/HomePage'
import ChatPage from './pages/ChatPage'
import ChatContextPage from './pages/ChatContextPage'
import WeeklyReportsPage from './pages/WeeklyReportsPage'
import ReportDetailPage from './pages/ReportDetailPage'
import AssessmentsPage from './pages/AssessmentsPage'
import AssessmentDetailPage from './pages/AssessmentDetailPage'
import KnowledgeGraphPage from './pages/KnowledgeGraphPage'
import NewInLast7DaysPage from './pages/NewInLast7DaysPage'
import InterestingPatternsPage from './pages/InterestingPatternsPage'
import EventsPage from './pages/EventsPage'
import { useUIStore } from './stores/uiStore'

function App() {
  const { slideOutPanel, sidebarCollapsed } = useUIStore()

  return (
    <div className="flex min-h-screen bg-content-bg">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <main
        className={`
          flex-1 min-h-screen transition-all duration-300 ease-in-out
          ${sidebarCollapsed ? 'ml-16' : 'ml-64'}
        `}
      >
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:sessionId" element={<ChatPage />} />
          <Route path="/chat-context" element={<ChatContextPage />} />
          <Route path="/reports" element={<WeeklyReportsPage />} />
          <Route path="/reports/:reportId" element={<ReportDetailPage />} />
          <Route path="/assessments" element={<AssessmentsPage />} />
          <Route path="/assessments/:id" element={<AssessmentDetailPage />} />
          <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
          <Route path="/new-last-7-days" element={<NewInLast7DaysPage />} />
          <Route path="/patterns" element={<InterestingPatternsPage />} />
          <Route path="/events" element={<EventsPage />} />
        </Routes>
      </main>

      {/* Slide-out Panel for Entity Details */}
      {slideOutPanel.isOpen && (
        <SlideOutPanel />
      )}
    </div>
  )
}

export default App

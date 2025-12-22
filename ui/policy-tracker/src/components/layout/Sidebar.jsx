import { NavLink, useLocation } from 'react-router-dom'
import {
  Home,
  MessageSquare,
  FileText,
  ClipboardList,
  Share2,
  Calendar,
  Sparkles,
  Clock,
  HelpCircle,
  ChevronRight
} from 'lucide-react'
import { useUIStore } from '../../stores/uiStore'

const navigation = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Weekly Reports', href: '/reports', icon: FileText },
  { name: 'Assessments', href: '/assessments', icon: ClipboardList },
  { name: 'Knowledge Graph', href: '/knowledge-graph', icon: Share2 },
  { name: 'Events', href: '/events', icon: Calendar },
]

const insightLinks = [
  { name: 'New in Last 7 Days', href: '/new-last-7-days', icon: Clock },
  { name: 'Interesting Patterns', href: '/patterns', icon: Sparkles },
]

function Sidebar() {
  const location = useLocation()
  const { recentAssessments } = useUIStore()

  const isActive = (href) => {
    if (href === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(href)
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-sidebar-bg flex flex-col border-r border-sidebar-border">
      {/* Logo */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-red-600 rounded flex items-center justify-center">
            <span className="text-white font-bold text-sm">SP</span>
          </div>
          <span className="text-sidebar-text font-semibold text-lg">Policy Tracker</span>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto dark-scrollbar py-4">
        <div className="px-3 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon
            const active = isActive(item.href)
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                  ${active
                    ? 'bg-sidebar-active text-white'
                    : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text'
                  }
                `}
              >
                <Icon size={18} />
                {item.name}
              </NavLink>
            )
          })}
        </div>

        {/* Insights Section */}
        <div className="px-3 mt-6">
          <div className="px-3 mb-2 text-xs font-semibold text-sidebar-muted uppercase tracking-wider">
            Insights
          </div>
          <div className="space-y-1">
            {insightLinks.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <NavLink
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                    ${active
                      ? 'bg-sidebar-active text-white'
                      : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text'
                    }
                  `}
                >
                  <Icon size={18} />
                  {item.name}
                </NavLink>
              )
            })}
          </div>
        </div>

        {/* Recent Assessments */}
        {recentAssessments.length > 0 && (
          <div className="px-3 mt-6">
            <div className="px-3 mb-2 text-xs font-semibold text-sidebar-muted uppercase tracking-wider">
              Recent Assessments
            </div>
            <div className="space-y-1">
              {recentAssessments.slice(0, 7).map((assessment) => (
                <NavLink
                  key={assessment.id}
                  to={`/assessments/${assessment.id}`}
                  className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors
                    ${location.pathname === `/assessments/${assessment.id}`
                      ? 'bg-sidebar-active text-white'
                      : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text'
                    }
                  `}
                >
                  <FileText size={14} />
                  <span className="truncate flex-1">{assessment.title}</span>
                  <ChevronRight size={14} className="opacity-50" />
                </NavLink>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Support Footer */}
      <div className="p-4 border-t border-sidebar-border">
        <button className="flex items-center gap-2 text-sidebar-muted hover:text-sidebar-text text-sm transition-colors w-full px-3 py-2 rounded-lg hover:bg-sidebar-hover">
          <HelpCircle size={18} />
          Need support?
        </button>
      </div>
    </aside>
  )
}

export default Sidebar

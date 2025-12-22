import { Link } from 'react-router-dom'
import { Share2, FileText, Building2, Calendar } from 'lucide-react'
import HeroCard from '../components/home/HeroCard'
import QuickActionCard from '../components/home/QuickActionCard'
import RecentUpdates from '../components/home/RecentUpdates'

function HomePage() {
  return (
    <div className="p-8 max-w-6xl">
      {/* Welcome Header */}
      <h1 className="text-4xl font-bold text-gray-900 mb-8">Welcome</h1>

      {/* Hero Card */}
      <HeroCard />

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-4 mt-6">
        <QuickActionCard
          to="/knowledge-graph"
          icon={Share2}
          title="Explore the Knowledge Graph"
          description="A time-aware map of policies, connections, context, and the narratives that shape them."
        />
        <QuickActionCard
          to="/reports"
          icon={FileText}
          title="View & add sources"
          description="Official gazettes, national and regional parliaments, regulatory authorities, and trusted media outlets"
        />
      </div>

      {/* Recent Graph Updates */}
      <RecentUpdates />
    </div>
  )
}

export default HomePage

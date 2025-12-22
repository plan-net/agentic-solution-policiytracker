import { Link } from 'react-router-dom'

function QuickActionCard({ to, icon: Icon, title, description }) {
  return (
    <Link
      to={to}
      className="block p-6 bg-content-bgAlt hover:bg-gray-100 rounded-xl transition-colors group"
    >
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm group-hover:shadow transition-shadow">
          <Icon size={20} className="text-gray-600" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
      </div>
    </Link>
  )
}

export default QuickActionCard

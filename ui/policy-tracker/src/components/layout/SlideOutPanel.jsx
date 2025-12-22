import { X, ExternalLink, MapPin, Tag, Sparkles } from 'lucide-react'
import { useUIStore } from '../../stores/uiStore'

function SlideOutPanel() {
  const { slideOutPanel, closeSlideOutPanel } = useUIStore()
  const { entity } = slideOutPanel

  if (!entity) return null

  // Get entity type color
  const getTypeColor = (type) => {
    const colors = {
      risk: 'bg-entity-risk',
      event: 'bg-entity-event',
      association: 'bg-entity-association',
      company: 'bg-entity-company',
      law: 'bg-entity-law',
      regulator: 'bg-entity-regulator',
      official: 'bg-entity-official',
      Policy: 'bg-blue-500',
      Regulation: 'bg-purple-500',
      Person: 'bg-amber-500',
      Organization: 'bg-teal-500',
      Politician: 'bg-green-500',
      Company: 'bg-entity-company',
    }
    return colors[type] || 'bg-gray-500'
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={closeSlideOutPanel}
      />

      {/* Panel */}
      <aside className="fixed right-0 top-0 h-screen w-96 bg-white shadow-xl z-50 flex flex-col border-l border-content-border overflow-hidden animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-content-border">
          <div className="flex items-center gap-2 text-accent-primary text-sm font-medium">
            <Sparkles size={16} />
            Agent insights
          </div>
          <button
            onClick={closeSlideOutPanel}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Entity Name */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              {entity.name}
            </h2>
          </div>

          {/* Type Badge */}
          <div>
            <span className={`inline-flex items-center px-3 py-1 rounded text-white text-sm font-medium ${getTypeColor(entity.type)}`}>
              {entity.type}
            </span>
          </div>

          {/* Image if available */}
          {entity.image && (
            <div className="rounded-lg overflow-hidden border border-content-border">
              <img
                src={entity.image}
                alt={entity.name}
                className="w-full h-48 object-cover"
              />
            </div>
          )}

          {/* Description */}
          {entity.description && (
            <div>
              <p className="text-gray-600 text-sm leading-relaxed">
                {entity.description}
              </p>
            </div>
          )}

          {/* Region / Jurisdiction */}
          {entity.region && (
            <div>
              <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
                Region / Jurisdiction
              </div>
              <div className="flex items-center gap-2 text-gray-700">
                <MapPin size={14} />
                {entity.region}
              </div>
            </div>
          )}

          {/* Focus Areas */}
          {entity.focusAreas && entity.focusAreas.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                Focus area
              </div>
              <ul className="space-y-1.5">
                {entity.focusAreas.map((area, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                    {area}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Properties */}
          {entity.properties && Object.keys(entity.properties).length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                Properties
              </div>
              <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                {Object.entries(entity.properties).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-gray-500">{key}</span>
                    <span className="text-gray-900 font-medium truncate ml-2 max-w-[60%]">
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Closest Entities */}
          {entity.relatedEntities && entity.relatedEntities.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                Closest Entities
              </div>
              <div className="space-y-2">
                {entity.relatedEntities.map((related, index) => (
                  <button
                    key={index}
                    className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-between group"
                  >
                    <span className="text-sm text-gray-700 truncate">
                      {related.name}
                    </span>
                    <ExternalLink size={14} className="text-gray-400 group-hover:text-gray-600" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </aside>

      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in {
          animation: slideIn 0.2s ease-out;
        }
      `}</style>
    </>
  )
}

export default SlideOutPanel

import { useState } from 'react'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, isSameMonth, isSameDay, addMonths, subMonths } from 'date-fns'

// Mock events data
const mockEvents = [
  {
    id: 1,
    title: 'Bitkom Privacy Conference',
    date: new Date(2025, 8, 10), // Sept 10, 2025
    type: 'Conference',
    location: 'Berlin',
  },
  {
    id: 2,
    title: 'EU Commission DSA Review',
    date: new Date(2025, 8, 15), // Sept 15, 2025
    type: 'Regulatory',
    location: 'Brussels',
  },
  {
    id: 3,
    title: 'GDPR Compliance Deadline',
    date: new Date(2025, 8, 20), // Sept 20, 2025
    type: 'Deadline',
    location: 'EU-wide',
  },
  {
    id: 4,
    title: 'Bundestag Digital Committee',
    date: new Date(2025, 8, 25), // Sept 25, 2025
    type: 'Government',
    location: 'Berlin',
  },
]

const eventTypeColors = {
  Conference: 'bg-blue-500',
  Regulatory: 'bg-purple-500',
  Deadline: 'bg-red-500',
  Government: 'bg-green-500',
}

function EventsPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState(null)

  const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1))
  const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1))

  // Get events for a specific date
  const getEventsForDate = (date) => {
    return mockEvents.filter(event => isSameDay(event.date, date))
  }

  // Render calendar header
  const renderHeader = () => {
    return (
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          {format(currentMonth, 'MMMM yyyy')}
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={prevMonth}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft size={20} />
          </button>
          <button
            onClick={() => setCurrentMonth(new Date())}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Today
          </button>
          <button
            onClick={nextMonth}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>
    )
  }

  // Render days of week header
  const renderDays = () => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    return (
      <div className="grid grid-cols-7 mb-2">
        {days.map(day => (
          <div key={day} className="text-center text-sm font-medium text-gray-500 py-2">
            {day}
          </div>
        ))}
      </div>
    )
  }

  // Render calendar cells
  const renderCells = () => {
    const monthStart = startOfMonth(currentMonth)
    const monthEnd = endOfMonth(monthStart)
    const startDate = startOfWeek(monthStart)
    const endDate = endOfWeek(monthEnd)

    const rows = []
    let days = []
    let day = startDate

    while (day <= endDate) {
      for (let i = 0; i < 7; i++) {
        const cloneDay = day
        const dayEvents = getEventsForDate(day)
        const isCurrentMonth = isSameMonth(day, monthStart)
        const isToday = isSameDay(day, new Date())
        const isSelected = selectedDate && isSameDay(day, selectedDate)

        days.push(
          <div
            key={day.toString()}
            onClick={() => setSelectedDate(cloneDay)}
            className={`
              min-h-24 p-2 border-b border-r border-content-border cursor-pointer transition-colors
              ${!isCurrentMonth ? 'bg-gray-50' : 'bg-white hover:bg-gray-50'}
              ${isSelected ? 'ring-2 ring-accent-primary ring-inset' : ''}
            `}
          >
            <div className={`
              w-7 h-7 flex items-center justify-center rounded-full text-sm mb-1
              ${isToday ? 'bg-accent-primary text-white' : ''}
              ${!isCurrentMonth ? 'text-gray-400' : 'text-gray-900'}
            `}>
              {format(day, 'd')}
            </div>
            <div className="space-y-1">
              {dayEvents.slice(0, 2).map(event => (
                <div
                  key={event.id}
                  className={`text-xs px-1.5 py-0.5 rounded truncate text-white ${eventTypeColors[event.type] || 'bg-gray-500'}`}
                >
                  {event.title}
                </div>
              ))}
              {dayEvents.length > 2 && (
                <div className="text-xs text-gray-500 px-1.5">
                  +{dayEvents.length - 2} more
                </div>
              )}
            </div>
          </div>
        )
        day = addDays(day, 1)
      }
      rows.push(
        <div key={day.toString()} className="grid grid-cols-7">
          {days}
        </div>
      )
      days = []
    }
    return <div className="border-t border-l border-content-border rounded-lg overflow-hidden">{rows}</div>
  }

  // Get events for selected date or upcoming
  const displayEvents = selectedDate
    ? getEventsForDate(selectedDate)
    : mockEvents.filter(e => e.date >= new Date()).slice(0, 5)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Events</h1>
          <p className="text-gray-500">Calendar view of regulatory events, deadlines, and conferences</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-sidebar-bg text-white rounded-lg hover:bg-gray-800 transition-colors">
          <Plus size={18} />
          Add Event
        </button>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Calendar */}
        <div className="col-span-2 bg-white rounded-xl border border-content-border p-6">
          {renderHeader()}
          {renderDays()}
          {renderCells()}
        </div>

        {/* Event List Sidebar */}
        <div className="bg-white rounded-xl border border-content-border p-6">
          <h3 className="font-semibold text-gray-900 mb-4">
            {selectedDate ? format(selectedDate, 'MMMM d, yyyy') : 'Upcoming Events'}
          </h3>

          {displayEvents.length > 0 ? (
            <div className="space-y-4">
              {displayEvents.map(event => (
                <div
                  key={event.id}
                  className="p-3 bg-content-bgAlt rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-3 h-3 rounded-full mt-1.5 ${eventTypeColors[event.type] || 'bg-gray-500'}`} />
                    <div>
                      <h4 className="font-medium text-gray-900 text-sm">{event.title}</h4>
                      <p className="text-xs text-gray-500 mt-1">
                        {format(event.date, 'MMMM d, yyyy')} • {event.location}
                      </p>
                      <span className="inline-block mt-2 px-2 py-0.5 bg-white rounded text-xs text-gray-600">
                        {event.type}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No events for this date</p>
          )}

          {/* Legend */}
          <div className="mt-6 pt-4 border-t border-content-border">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Event Types
            </h4>
            <div className="space-y-2">
              {Object.entries(eventTypeColors).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${color}`} />
                  <span className="text-sm text-gray-600">{type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Placeholder Notice */}
      <div className="mt-8 p-4 bg-amber-50 border border-amber-200 rounded-xl">
        <p className="text-amber-800 text-sm">
          <strong>Note:</strong> This calendar shows placeholder events. The backend API for event
          management will be implemented in a future update.
        </p>
      </div>
    </div>
  )
}

export default EventsPage

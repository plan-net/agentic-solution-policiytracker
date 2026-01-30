import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

// Brand colors from Tailwind config
const CHART_COLORS = [
  '#8B5CF6', // accent-primary (purple)
  '#EC4899', // accent-secondary (pink)
  '#3B82F6', // status-working (blue)
  '#10B981', // status-complete (green)
  '#14B8A6', // entity-company (teal)
  '#EF4444', // status-error (red)
  '#F59E0B', // amber
  '#6366F1', // indigo
]

// Status colors for timeline
const STATUS_COLORS = {
  deadline: '#EF4444',
  active: '#10B981',
  upcoming: '#3B82F6',
  phase: '#8B5CF6',
  completed: '#6B7280',
}

function ChartRenderer({ spec }) {
  if (!spec || !spec.type || !spec.data) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
        Invalid chart specification: missing type or data
      </div>
    )
  }

  const { type, title, data, xKey, yKey, colors = CHART_COLORS } = spec

  const renderChart = () => {
    switch (type) {
      case 'bar':
        return renderBarChart()
      case 'line':
        return renderLineChart()
      case 'area':
        return renderAreaChart()
      case 'pie':
        return renderPieChart()
      case 'timeline':
        return renderTimelineChart()
      default:
        return (
          <div className="text-gray-500 text-sm">
            Unsupported chart type: {type}
          </div>
        )
    }
  }

  const renderBarChart = () => {
    if (!xKey || !yKey) {
      return <div className="text-red-500 text-sm">Bar chart requires xKey and yKey</div>
    }

    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis
            dataKey={xKey}
            tick={{ fill: '#6B7280', fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={{ fill: '#6B7280', fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e5e5e5',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          />
          <Legend />
          <Bar dataKey={yKey} fill={colors[0]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  const renderLineChart = () => {
    if (!xKey || !yKey) {
      return <div className="text-red-500 text-sm">Line chart requires xKey and yKey</div>
    }

    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis
            dataKey={xKey}
            tick={{ fill: '#6B7280', fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={{ fill: '#6B7280', fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e5e5e5',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke={colors[0]}
            strokeWidth={2}
            dot={{ fill: colors[0], strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const renderAreaChart = () => {
    if (!xKey || !yKey) {
      return <div className="text-red-500 text-sm">Area chart requires xKey and yKey</div>
    }

    return (
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis
            dataKey={xKey}
            tick={{ fill: '#6B7280', fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={{ fill: '#6B7280', fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e5e5e5',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          />
          <Legend />
          <Area
            type="monotone"
            dataKey={yKey}
            stroke={colors[0]}
            fill={colors[0]}
            fillOpacity={0.3}
          />
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  const renderPieChart = () => {
    const valueKey = yKey || 'value'
    const nameKey = xKey || 'name'

    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
            labelLine={{ stroke: '#6B7280' }}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e5e5e5',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  const renderTimelineChart = () => {
    // Process timeline data
    const timelineData = data.map((item, index) => {
      const startDate = new Date(item.start)
      const endDate = new Date(item.end)
      const statusColor = STATUS_COLORS[item.status] || colors[index % colors.length]

      return {
        ...item,
        startDate,
        endDate,
        color: statusColor,
        isSingleDay: item.start === item.end,
      }
    })

    // Find date range for scale
    const allDates = timelineData.flatMap((d) => [d.startDate, d.endDate])
    const minDate = new Date(Math.min(...allDates))
    const maxDate = new Date(Math.max(...allDates))

    // Add padding to date range
    const rangePadding = (maxDate - minDate) * 0.1
    const displayMinDate = new Date(minDate.getTime() - rangePadding)
    const displayMaxDate = new Date(maxDate.getTime() + rangePadding)
    const totalRange = displayMaxDate - displayMinDate

    const formatDate = (date) => {
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
    }

    return (
      <div className="w-full">
        {/* Timeline header with date range */}
        <div className="flex justify-between text-xs text-gray-500 mb-2 px-2">
          <span>{formatDate(displayMinDate)}</span>
          <span>{formatDate(displayMaxDate)}</span>
        </div>

        {/* Timeline items */}
        <div className="space-y-3">
          {timelineData.map((item, index) => {
            const startPercent = ((item.startDate - displayMinDate) / totalRange) * 100
            const endPercent = ((item.endDate - displayMinDate) / totalRange) * 100
            const widthPercent = Math.max(endPercent - startPercent, 2) // Minimum 2% width for visibility

            return (
              <div key={index} className="relative">
                {/* Label */}
                <div className="text-sm font-medium text-gray-700 mb-1">{item.name}</div>

                {/* Timeline bar container */}
                <div className="relative h-8 bg-gray-100 rounded-lg overflow-hidden">
                  {/* Bar */}
                  <div
                    className="absolute h-full rounded-lg flex items-center justify-center text-white text-xs font-medium transition-all"
                    style={{
                      left: `${startPercent}%`,
                      width: `${widthPercent}%`,
                      backgroundColor: item.color,
                      minWidth: item.isSingleDay ? '24px' : undefined,
                    }}
                  >
                    {item.isSingleDay ? (
                      <span className="px-1">{formatDate(item.startDate)}</span>
                    ) : (
                      <span className="px-2 truncate">
                        {formatDate(item.startDate)} - {formatDate(item.endDate)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Status badge */}
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-xs text-gray-500 capitalize">{item.status}</span>
                </div>
              </div>
            )
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 pt-4 border-t border-gray-200 flex flex-wrap gap-4">
          {Object.entries(STATUS_COLORS).map(([status, color]) => (
            <div key={status} className="flex items-center gap-2">
              <span
                className="inline-block w-3 h-3 rounded"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-gray-600 capitalize">{status}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="chart-container my-6 p-4 bg-white rounded-lg border border-content-border">
      {title && (
        <h4 className="text-lg font-semibold text-gray-800 mb-4 text-center">{title}</h4>
      )}
      {renderChart()}
    </div>
  )
}

export default ChartRenderer

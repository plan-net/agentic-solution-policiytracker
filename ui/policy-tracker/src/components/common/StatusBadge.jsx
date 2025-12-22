import { CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react'

const statusConfig = {
  complete: {
    label: 'Complete',
    bgColor: 'bg-status-complete',
    textColor: 'text-white',
    icon: CheckCircle,
  },
  working: {
    label: 'Working',
    bgColor: 'bg-status-working',
    textColor: 'text-white',
    icon: Loader2,
    animate: true,
  },
  ready: {
    label: 'Ready',
    bgColor: 'bg-status-ready',
    textColor: 'text-white',
    icon: CheckCircle,
  },
  pending: {
    label: 'Pending',
    bgColor: 'bg-gray-400',
    textColor: 'text-white',
    icon: Clock,
  },
  draft: {
    label: 'Draft',
    bgColor: 'bg-status-draft',
    textColor: 'text-white',
    icon: Clock,
  },
  failed: {
    label: 'Failed',
    bgColor: 'bg-red-500',
    textColor: 'text-white',
    icon: AlertCircle,
  },
  error: {
    label: 'Error',
    bgColor: 'bg-status-error',
    textColor: 'text-white',
    icon: AlertCircle,
  },
}

function StatusBadge({ status, showIcon = true, size = 'default' }) {
  const config = statusConfig[status] || statusConfig.draft
  const Icon = config.icon

  const sizeClasses = {
    small: 'px-2 py-0.5 text-xs',
    default: 'px-2.5 py-1 text-sm',
    large: 'px-3 py-1.5 text-base',
  }

  const iconSizes = {
    small: 12,
    default: 14,
    large: 16,
  }

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded-full font-medium
        ${config.bgColor} ${config.textColor}
        ${sizeClasses[size]}
      `}
    >
      {showIcon && (
        <Icon
          size={iconSizes[size]}
          className={config.animate ? 'animate-spin' : ''}
        />
      )}
      {config.label}
    </span>
  )
}

export default StatusBadge

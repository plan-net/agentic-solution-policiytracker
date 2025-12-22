import { ENTITY_COLORS } from '../../utils/constants'

function EntityBadge({ type, size = 'default', onClick = null }) {
  const color = ENTITY_COLORS[type] || ENTITY_COLORS.Unknown

  const sizeClasses = {
    small: 'px-2 py-0.5 text-xs',
    default: 'px-2.5 py-1 text-sm',
    large: 'px-3 py-1.5 text-base',
  }

  const Component = onClick ? 'button' : 'span'

  return (
    <Component
      onClick={onClick}
      className={`
        inline-flex items-center rounded font-medium text-white
        ${sizeClasses[size]}
        ${onClick ? 'cursor-pointer hover:opacity-80 transition-opacity' : ''}
      `}
      style={{ backgroundColor: color }}
    >
      {type}
    </Component>
  )
}

export default EntityBadge

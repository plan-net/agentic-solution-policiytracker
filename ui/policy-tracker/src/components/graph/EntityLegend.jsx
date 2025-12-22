function EntityLegend({ categories, selectedCategories, onToggle }) {
  return (
    <div className="flex items-center gap-2 p-4 border-b border-content-border bg-gray-50">
      {categories.map((category) => {
        const isSelected = selectedCategories.includes(category.key)
        return (
          <button
            key={category.key}
            onClick={() => onToggle(category.key)}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all
              ${isSelected
                ? 'bg-white shadow-sm'
                : 'bg-transparent opacity-50 hover:opacity-75'
              }
            `}
          >
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: category.color }}
            />
            {category.key}
          </button>
        )
      })}
    </div>
  )
}

export default EntityLegend

/**
 * Enhanced table components for markdown rendering
 * Provides consistent styling for tables in chat messages and reports
 */

function DataTable({ children }) {
  return (
    <div className="data-table-wrapper overflow-x-auto my-4 rounded-lg border border-content-border">
      <table className="data-table min-w-full divide-y divide-gray-200">
        {children}
      </table>
    </div>
  )
}

function DataTableHead({ children }) {
  return <thead className="bg-content-bgAlt">{children}</thead>
}

function DataTableBody({ children }) {
  return <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>
}

function DataTableRow({ children }) {
  return <tr className="hover:bg-gray-50 transition-colors">{children}</tr>
}

function DataTableHeaderCell({ children }) {
  return (
    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 whitespace-nowrap">
      {children}
    </th>
  )
}

function DataTableCell({ children }) {
  return (
    <td className="px-4 py-3 text-sm text-gray-600">
      {children}
    </td>
  )
}

export {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataTableRow,
  DataTableHeaderCell,
  DataTableCell,
}

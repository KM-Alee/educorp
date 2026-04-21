import { Button } from '../ui/Button'

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  totalItems?: number
}

export function Pagination({ page, totalPages, onPageChange, totalItems }: PaginationProps) {
  if (totalPages <= 1) return null

  return (
    <div className="pagination">
      {totalItems != null ? (
        <span className="pagination__info">{totalItems} items</span>
      ) : null}
      <Button
        variant="secondary"
        size="sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      <span className="text-sm text-muted">
        {page} of {totalPages}
      </span>
      <Button
        variant="secondary"
        size="sm"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </div>
  )
}

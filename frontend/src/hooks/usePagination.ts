import { ref, computed } from 'vue'

export function usePagination(fetchFn: (params: any) => Promise<any>) {
  const currentPage = ref(1)
  const pageSize = ref(10)
  const total = ref(0)

  const paginationLayout = computed(() =>
    total.value > 100
      ? 'total, sizes, prev, pager, next, jumper'
      : 'total, sizes, prev, pager, next'
  )

  function handleCurrentChange(page: number) {
    currentPage.value = page
    fetchFn({ page, page_size: pageSize.value })
  }

  function handleSizeChange(size: number) {
    pageSize.value = size
    currentPage.value = 1
    fetchFn({ page: 1, page_size: size })
  }

  function resetPagination() {
    currentPage.value = 1
  }

  return {
    currentPage,
    pageSize,
    total,
    paginationLayout,
    handleCurrentChange,
    handleSizeChange,
    resetPagination,
  }
}

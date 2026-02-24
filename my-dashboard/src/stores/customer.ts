import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCustomerStore = defineStore('customer', () => {
  // State
  const orders = ref<any[]>([])
  const subscriptions = ref<any[]>([])
  const items = ref<any[]>([])
  const activeSubsMap = ref<Record<string, string>>({})
  const pendingSubsMap = ref<Record<string, string>>({})
  const scheduleMap = ref<Record<string, any>>({})
  const lastUpdated = ref<Date | null>(null)
  const isRefreshing = ref(false)

  // Computed
  const hasActiveOrders = computed(() =>
    orders.value.some(o => o.docstatus === 1 && o.status !== 'Completed')
  )

  const pendingOrderCount = computed(() =>
    orders.value.filter(o => o.docstatus === 0).length
  )

  // Actions
  const setOrders = (data: any[]) => {
    orders.value = data
    lastUpdated.value = new Date()
  }

  const setSubscriptions = (data: any[]) => {
    subscriptions.value = data
  }

  const setItems = (data: any[]) => {
    items.value = data
  }

  const setSubsStatus = (active: any, pending: any, schedule: any) => {
    activeSubsMap.value = active || {}
    pendingSubsMap.value = pending || {}
    scheduleMap.value = schedule || {}
  }

  const setRefreshing = (val: boolean) => {
    isRefreshing.value = val
  }

  const reset = () => {
    orders.value = []
    subscriptions.value = []
    items.value = []
    activeSubsMap.value = {}
    pendingSubsMap.value = {}
    scheduleMap.value = {}
    lastUpdated.value = null
  }

  return {
    orders,
    subscriptions,
    items,
    activeSubsMap,
    pendingSubsMap,
    scheduleMap,
    lastUpdated,
    isRefreshing,
    hasActiveOrders,
    pendingOrderCount,
    setOrders,
    setSubscriptions,
    setItems,
    setSubsStatus,
    setRefreshing,
    reset
  }
})
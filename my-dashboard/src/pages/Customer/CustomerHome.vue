<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { createResource, Badge, Button, Dialog } from 'frappe-ui'
import {
  ShoppingCart, Package, RefreshCcw, Store, Plus, Minus,
  Trash2, MapPin, ShoppingBag, CheckCircle, ClipboardList,
  ChevronDown, ChevronUp, XCircle, Clock, Truck, FileText,
  Calendar, TrendingUp, AlertCircle, Newspaper, X,
  Layers, Hash, Hourglass, Star
} from 'lucide-vue-next'

const props = defineProps<{
  filters: {
    pincode?: string
    society?: string
    category?: string
    seller?: string
    customer?: string
    delivery_address?: string
  }
}>()

// ─── TABS ───
const activeTab = ref<'shop' | 'orders' | 'subscriptions'>('shop')

// ─── SHOP STATE ───
const cart = ref<Record<string, number>>({})
const checkoutOpen = ref(false)
const isPlacingOrder = ref(false)
const placeOrderError = ref('')
const orderPlaced = ref(false)
const placedOrderId = ref('')
const placedOrderTotal = ref('')
const skippedItems = ref<string[]>([])

// ─── SUBSCRIPTION MODAL STATE ───
const subscriptionModalOpen = ref(false)
const selectedSubscriptionItem = ref<any>(null)
const isCreatingSubscription = ref(false)
const subscriptionError = ref('')
const subscriptionSuccess = ref(false)
const subscriptionSuccessMsg = ref('')

// ─── DAY-WISE SUBSCRIPTION FORM ───
// schedule: { item_code: { Monday: qty, Tuesday: qty, ... } }
// additionalItems: [{ item_code, item_name, ... }]
const subForm = ref({
  startDate: new Date().toISOString().split('T')[0],
  months: 1,
  // day-wise qty per item_code
  schedule: {} as Record<string, Record<string, number>>,
  // additional items selected (beyond primary)
  additionalItems: [] as string[]
})

// ─── SUBSCRIPTION STATUS MAPS ───
const activeSubsMap = ref<Record<string, string>>({})
const pendingSubsMap = ref<Record<string, string>>({})
const scheduleMap = ref<Record<string, Record<string, number>>>({})

// ─── TODAY INFO ───
const todayName = computed(() => {
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  return days[new Date().getDay()]
})
const todayShort = computed(() => todayName.value.slice(0, 3))

const ALL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_SHORT: Record<string, string> = {
  Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed',
  Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun'
}
const DAY_QTY_FIELD: Record<string, string> = {
  Monday: 'monday_qty', Tuesday: 'tuesday_qty', Wednesday: 'wednesday_qty',
  Thursday: 'thursday_qty', Friday: 'friday_qty', Saturday: 'saturday_qty', Sunday: 'sunday_qty'
}

// ─── ORDERS STATE ───
const expandedOrder = ref<string | null>(null)
const cancelConfirmOpen = ref(false)
const cancelTargetOrder = ref<string | null>(null)

// ─── RESOURCES ───
const items = createResource({
  url: 'my_frappe_app.api.get_seller_items',
  debounce: 300,
})

const ordersResource = createResource({
  url: 'my_frappe_app.api.get_customer_orders',
})

const activeSubsResource = createResource({
  url: 'my_frappe_app.api.get_customer_subscription_status',
  onSuccess(data: any) {
    activeSubsMap.value = data?.active || {}
    pendingSubsMap.value = data?.pending || {}
    scheduleMap.value = data?.schedule || {}
  }
})

const cancelOrderResource = createResource({
  url: 'my_frappe_app.api.cancel_order',
  onSuccess(data: any) {
    cancelConfirmOpen.value = false
    cancelTargetOrder.value = null
    if (data.status === 'success') ordersResource.reload()
  },
})

const placeOrderResource = createResource({
  url: 'my_frappe_app.api.place_order',
  onSuccess(data: any) {
    isPlacingOrder.value = false
    if (data.status === 'success') {
      placedOrderId.value = data.order_id
      placedOrderTotal.value = data.formatted_total
      skippedItems.value = data.skipped_items || []
      cart.value = {}
      checkoutOpen.value = false
      orderPlaced.value = true
      if (props.filters.customer) {
        ordersResource.fetch({ customer: props.filters.customer })
      }
    } else {
      placeOrderError.value = data.message || 'Something went wrong.'
    }
  },
  onError(err: any) {
    isPlacingOrder.value = false
    placeOrderError.value = err?.message || 'Failed to place order.'
  },
})

const createSubscriptionResource = createResource({
  url: 'my_frappe_app.api.create_subscription',
  onSuccess(data: any) {
    isCreatingSubscription.value = false
    if (data.status === 'success') {
      subscriptionModalOpen.value = false
      subscriptionSuccess.value = true
      subscriptionSuccessMsg.value = data.message || 'Subscription request sent!'
      if (props.filters.customer && props.filters.seller) {
        activeSubsResource.fetch({
          customer: props.filters.customer,
          seller: props.filters.seller
        })
        ordersResource.fetch({ customer: props.filters.customer })
      }
    } else {
      subscriptionError.value = data.message || 'Failed to create subscription'
    }
  },
  onError(err: any) {
    isCreatingSubscription.value = false
    subscriptionError.value = err?.message || 'Failed to create subscription'
  }
})

// ─── WATCHERS ───
watch(
  () => props.filters,
  (f) => {
    if (f?.seller && f?.category) {
      items.fetch({ seller: f.seller, category: f.category })
      cart.value = {}
    } else {
      items.data = null
    }
    if (f?.customer) {
      ordersResource.fetch({ customer: f.customer })
    }
    if (f?.customer && f?.seller) {
      activeSubsResource.fetch({ customer: f.customer, seller: f.seller })
    }
  },
  { deep: true, immediate: true }
)

watch(activeTab, (tab) => {
  if (tab === 'orders' && props.filters.customer) {
    ordersResource.fetch({ customer: props.filters.customer })
  }
})

// ─── COMPUTED ───
const allItems = computed(() => (items.data as any[]) || [])
const availableItems = computed(() => allItems.value.filter((i: any) => i.price_available))
const unavailableItems = computed(() => allItems.value.filter((i: any) => !i.price_available))
const subscriptionItems = computed(() => availableItems.value.filter((i: any) => i.is_subscription_item === true))
const regularItems = computed(() => availableItems.value.filter((i: any) => !i.is_subscription_item))

const allOrders = computed(() => (ordersResource.data as any)?.orders || [])
const allSubscriptions = computed(() => (ordersResource.data as any)?.subscriptions || [])

// ─── SUBSCRIPTION HELPERS ───
// Naya — aaj ke din ki qty bhi check karo
const isActiveSubscribed = (itemCode: string) => {
  if (!activeSubsMap.value[itemCode]) return false
  const sched = scheduleMap.value[itemCode]
  if (!sched) return true
  return (sched[todayName.value] ?? 0) > 0
}

const isPendingSubscribed = (itemCode: string) => {
  if (!pendingSubsMap.value[itemCode]) return false
  const sched = scheduleMap.value[itemCode]
  if (!sched) return true
  return (sched[todayName.value] ?? 0) > 0
}

const isAnySubscribed = (itemCode: string) => isActiveSubscribed(itemCode) || isPendingSubscribed(itemCode)

const getSubName = (itemCode: string) =>
  activeSubsMap.value[itemCode] || pendingSubsMap.value[itemCode] || ''

const isNormalOrderBlocked = (itemCode: string) => {
  if (!isActiveSubscribed(itemCode)) return false
  const sched = scheduleMap.value[itemCode]
  if (!sched) return true
  return (sched[todayName.value] ?? 0) > 0
}

// ─── SUBSCRIPTION MODAL HELPERS ───
const openSubscriptionModal = (item: any) => {
  selectedSubscriptionItem.value = item
  subscriptionError.value = ''
  subForm.value = {
    startDate: new Date().toISOString().split('T')[0],
    months: 1,
    schedule: {
      [item.item_code]: {
        Monday: 1, Tuesday: 1, Wednesday: 1, Thursday: 1, Friday: 1, Saturday: 1, Sunday: 1
      }
    },
    additionalItems: []
  }
  subscriptionModalOpen.value = true
}

// Get day qty for an item in the form
const getDayQty = (itemCode: string, day: string): number => {
  return subForm.value.schedule[itemCode]?.[day] ?? 0
}

const setDayQty = (itemCode: string, day: string, qty: number) => {
  if (!subForm.value.schedule[itemCode]) {
    subForm.value.schedule[itemCode] = {}
  }
  subForm.value.schedule[itemCode][day] = Math.max(0, Math.min(qty, 99))
}

const toggleDay = (itemCode: string, day: string) => {
  const current = getDayQty(itemCode, day)
  setDayQty(itemCode, day, current > 0 ? 0 : 1)
}

const isDayActive = (itemCode: string, day: string) => getDayQty(itemCode, day) > 0

// Additional items (subscription items other than primary)
const availableAdditionalItems = computed(() =>
  subscriptionItems.value.filter(
    (i: any) => i.item_code !== selectedSubscriptionItem.value?.item_code
  )
)

const isAdditionalItemSelected = (itemCode: string) =>
  subForm.value.additionalItems.includes(itemCode)

const toggleAdditionalItem = (item: any) => {
  const idx = subForm.value.additionalItems.indexOf(item.item_code)
  if (idx === -1) {
    subForm.value.additionalItems.push(item.item_code)
    // init schedule for this item with all days = 0
    if (!subForm.value.schedule[item.item_code]) {
      subForm.value.schedule[item.item_code] = {
        Monday: 0, Tuesday: 0, Wednesday: 0, Thursday: 0, Friday: 0, Saturday: 0, Sunday: 0
      }
    }
  } else {
    subForm.value.additionalItems.splice(idx, 1)
    delete subForm.value.schedule[item.item_code]
  }
}

// Get item price for a specific day
const getDayPrice = (item: any, day: string): number => {
  return item.day_prices?.[day] ?? 0
}

const formatPrice = (val: number) =>
  val > 0 ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2 }).format(val) : '—'

// Weekly cost estimate
const weeklyEstimate = computed(() => {
  if (!selectedSubscriptionItem.value) return 0
  let total = 0
  const allItemCodes = [
    selectedSubscriptionItem.value.item_code,
    ...subForm.value.additionalItems
  ]
  for (const ic of allItemCodes) {
    const sched = subForm.value.schedule[ic] || {}
    const itemObj = allItems.value.find((i: any) => i.item_code === ic)
    if (!itemObj) continue
    for (const day of ALL_DAYS) {
      const qty = sched[day] || 0
      const price = getDayPrice(itemObj, day)
      total += qty * price
    }
  }
  return total
})

const handleCreateSubscription = () => {
  if (!props.filters.customer || !props.filters.seller) {
    subscriptionError.value = 'Customer or seller information missing'
    return
  }
  if (!selectedSubscriptionItem.value) return

  // Build schedule_items array
  const primaryCode = selectedSubscriptionItem.value.item_code
  const allItemCodes = [primaryCode, ...subForm.value.additionalItems]

  const scheduleItems = allItemCodes.map((ic, idx) => {
    const sched = subForm.value.schedule[ic] || {}
    return {
      item_code: ic,
      is_primary_item: ic === primaryCode ? 1 : 0,
      monday_qty: sched['Monday'] || 0,
      tuesday_qty: sched['Tuesday'] || 0,
      wednesday_qty: sched['Wednesday'] || 0,
      thursday_qty: sched['Thursday'] || 0,
      friday_qty: sched['Friday'] || 0,
      saturday_qty: sched['Saturday'] || 0,
      sunday_qty: sched['Sunday'] || 0,
    }
  })

  // Validate primary has at least one day
  const primarySched = scheduleItems.find(s => s.is_primary_item)
  const hasAnyDay = primarySched && ALL_DAYS.some(d => primarySched[DAY_QTY_FIELD[d] as keyof typeof primarySched] as number > 0)
  if (!hasAnyDay) {
    subscriptionError.value = 'Please select at least one day for the primary item.'
    return
  }

  subscriptionError.value = ''
  isCreatingSubscription.value = true

  createSubscriptionResource.fetch({
    customer: props.filters.customer,
    seller: props.filters.seller,
    schedule_items: JSON.stringify(scheduleItems),
    start_date: subForm.value.startDate,
    months: subForm.value.months
  })
}

// ─── CART HELPERS ───
const updateCart = (itemName: string, delta: number) => {
  const next = (cart.value[itemName] || 0) + delta
  const updated = { ...cart.value }
  if (next <= 0) delete updated[itemName]
  else updated[itemName] = next
  cart.value = updated
}

const removeFromCart = (itemName: string) => {
  const updated = { ...cart.value }
  delete updated[itemName]
  cart.value = updated
}

const totalCartItems = computed(() =>
  Object.values(cart.value).reduce((a, b) => a + b, 0)
)

const cartItemsWithDetails = computed(() => {
  if (!items.data) return []
  return Object.entries(cart.value)
    .map(([name, qty]) => {
      const item = allItems.value.find((i: any) => i.name === name)
      return item ? { ...item, qty, subtotal: item.price * qty } : null
    })
    .filter(Boolean)
})

const cartTotal = computed(() =>
  cartItemsWithDetails.value.reduce((sum: number, item: any) => sum + item.subtotal, 0)
)

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val)

const hasDailyPrice = (item: any) =>
  item.price_available &&
  item.standard_rate != null &&
  Math.abs(item.price - item.standard_rate) > 0.01

// ─── PLACE ORDER ───
const handlePlaceOrder = () => {
  if (!props.filters.seller || !props.filters.customer) {
    placeOrderError.value = 'Seller or customer info missing.'
    return
  }
  if (!Object.keys(cart.value).length) {
    placeOrderError.value = 'Your cart is empty.'
    return
  }
  placeOrderError.value = ''
  isPlacingOrder.value = true

  placeOrderResource.fetch({
    cart_data: JSON.stringify(cart.value),
    customer: props.filters.customer,
    seller: props.filters.seller,
    pincode: props.filters.pincode || '',
    society: props.filters.society || null,
    delivery_address: props.filters.delivery_address || null,
  })
}

const openCheckout = () => {
  placeOrderError.value = ''
  checkoutOpen.value = true
}

// ─── ORDER STATUS HELPERS ───
type BadgeTheme = 'blue' | 'green' | 'red' | 'orange' | 'gray'
const badgeTheme = (color: string): BadgeTheme =>
  ({ orange: 'orange', blue: 'blue', green: 'green', red: 'red', gray: 'gray' }[color] as BadgeTheme) || 'gray'

const statusIcon = (color: string) => ({
  orange: Clock, blue: CheckCircle, green: CheckCircle,
  red: XCircle, gray: Clock,
}[color] || Clock)

const statusIconClass = (color: string) => ({
  orange: 'text-orange-500', blue: 'text-blue-500',
  green: 'text-green-500', red: 'text-red-500', gray: 'text-gray-400',
}[color] || 'text-gray-400')

const statusBg = (color: string) => ({
  orange: 'bg-orange-50', blue: 'bg-blue-50',
  green: 'bg-green-50', red: 'bg-red-50', gray: 'bg-gray-50',
}[color] || 'bg-gray-50')

const toggleExpand = (name: string) => { expandedOrder.value = expandedOrder.value === name ? null : name }
const confirmCancel = (name: string) => { cancelTargetOrder.value = name; cancelConfirmOpen.value = true }
const executeCancel = () => { if (cancelTargetOrder.value) cancelOrderResource.fetch({ order_id: cancelTargetOrder.value }) }

const timelineSteps = (order: any) => [
  { key: 'placed', label: 'Placed', icon: CheckCircle, done: true, lineAfter: order.docstatus >= 1 },
  { key: 'accepted', label: 'Accepted', icon: CheckCircle, done: order.docstatus >= 1, lineAfter: order.per_delivered >= 100 },
  { key: 'delivered', label: 'Delivered', icon: Truck, done: order.per_delivered >= 100, lineAfter: order.status === 'Completed' },
  { key: 'completed', label: 'Completed', icon: CheckCircle, done: order.status === 'Completed', lineAfter: false },
]

// ─── SUBSCRIPTION STATUS COLOR ───
const subStatusColor: Record<string, string> = {
  'Active': 'bg-green-100 text-green-700 border-green-200',
  'Accept Pending': 'bg-amber-100 text-amber-700 border-amber-200',
  'Expired': 'bg-gray-100 text-gray-500 border-gray-200',
  'Cancelled': 'bg-red-100 text-red-600 border-red-200',
}

// Day schedule summary for display
const getDayScheduleSummary = (scheduleItems: any[]) => {
  const summary: string[] = []
  for (const si of scheduleItems) {
    const days = ALL_DAYS.filter(d => (si[DAY_QTY_FIELD[d]] || 0) > 0)
    if (days.length === 0) continue
    const daysStr = days.map(d => DAY_SHORT[d]).join(', ')
    summary.push(`${si.item_name}: ${daysStr}`)
  }
  return summary
}
</script>

<template>
  <div class="p-4 md:p-6 space-y-5 max-w-7xl mx-auto">

    <!-- ─── HEADER ─── -->
    <div class="flex justify-between items-center bg-white p-4 md:p-5 rounded-2xl border border-gray-100 shadow-sm">
      <div class="flex items-center gap-3 md:gap-4">
        <div class="p-2.5 bg-blue-600 rounded-xl text-white shadow-lg">
          <ShoppingCart class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-base md:text-lg font-bold text-gray-900">Customer Portal</h2>
          <p class="text-xs text-gray-400 max-w-[180px] md:max-w-none truncate">
            <span v-if="!filters.category">Select category from sidebar</span>
            <span v-else-if="!filters.seller">Select a seller to browse</span>
            <span v-else>{{ filters.seller }} · {{ filters.category }}</span>
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2 flex-shrink-0">
        <Button v-if="activeTab === 'shop' && filters.seller && filters.category" variant="outline" size="sm"
          :loading="items.loading" @click="items.fetch({ seller: filters.seller, category: filters.category })">
          <template #prefix>
            <RefreshCcw class="w-3.5 h-3.5" />
          </template>
        </Button>

        <Button v-if="activeTab === 'orders'" variant="outline" size="sm" :loading="ordersResource.loading"
          @click="ordersResource.reload()">
          <template #prefix>
            <RefreshCcw class="w-3.5 h-3.5" />
          </template>
        </Button>

        <Button v-if="totalCartItems > 0 && activeTab === 'shop'" variant="solid" theme="blue" @click="openCheckout">
          <template #prefix>
            <ShoppingBag class="w-4 h-4" />
          </template>
          {{ totalCartItems }} · {{ formatCurrency(cartTotal) }}
        </Button>
      </div>
    </div>

    <!-- ─── TABS ─── -->
    <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
      <button @click="activeTab = 'shop'" :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all',
        activeTab === 'shop' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']">
        <Store class="w-4 h-4" /> Shop
      </button>
      <button @click="activeTab = 'orders'" :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all',
        activeTab === 'orders' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']">
        <ClipboardList class="w-4 h-4" /> My Orders
        <Badge v-if="allOrders.length > 0" :label="String(allOrders.length)" theme="blue" size="sm" />
      </button>
      <button @click="activeTab = 'subscriptions'" :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all',
        activeTab === 'subscriptions' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']">
        <Newspaper class="w-4 h-4" /> My Plans
        <Badge v-if="allSubscriptions.length > 0" :label="String(allSubscriptions.length)" theme="green" size="sm" />
      </button>
    </div>

    <!-- ─── SUCCESS BANNERS ─── -->
    <div v-if="orderPlaced" class="bg-green-50 border border-green-200 rounded-2xl p-4 space-y-2">
      <div class="flex items-start justify-between">
        <div class="flex gap-3">
          <CheckCircle class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
          <div>
            <p class="font-bold text-green-800 text-sm">Order placed successfully!</p>
            <p class="text-xs text-green-700 mt-0.5">
              <span class="font-mono font-semibold">{{ placedOrderId }}</span>
              · Total: <span class="font-semibold">{{ placedOrderTotal }}</span>
            </p>
          </div>
        </div>
        <button @click="orderPlaced = false" class="text-green-400 hover:text-green-600">
          <X class="w-4 h-4" />
        </button>
      </div>
      <div v-if="skippedItems.length"
        class="flex items-start gap-2 bg-orange-50 border border-orange-200 rounded-xl px-3 py-2 ml-8">
        <AlertCircle class="w-3.5 h-3.5 text-orange-500 mt-0.5 flex-shrink-0" />
        <p class="text-xs text-orange-700">
          <span class="font-semibold">{{ skippedItems.length }} item(s) skipped</span> — no price for today:
          <span class="font-semibold">{{ skippedItems.join(', ') }}</span>
        </p>
      </div>
    </div>

    <div v-if="subscriptionSuccess" class="bg-amber-50 border border-amber-200 rounded-2xl p-4">
      <div class="flex items-start justify-between">
        <div class="flex gap-3">
          <Hourglass class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
          <div>
            <p class="font-bold text-amber-800 text-sm">Subscription request sent!</p>
            <p class="text-xs text-amber-700 mt-0.5">{{ subscriptionSuccessMsg }}</p>
            <p class="text-xs text-amber-600 mt-1">⏳ Once seller accepts, daily delivery starts from next day.</p>
          </div>
        </div>
        <button @click="subscriptionSuccess = false" class="text-amber-400 hover:text-amber-600">
          <X class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- ════════════════════════════════════════ -->
    <!-- SHOP TAB                                 -->
    <!-- ════════════════════════════════════════ -->
    <template v-if="activeTab === 'shop'">

      <div v-if="!filters.category"
        class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-24 text-center">
        <Layers class="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 class="text-base font-bold text-gray-700">Select a Category</h3>
        <p class="text-sm text-gray-400 mt-1">Sidebar → Pincode → Category → Seller</p>
      </div>

      <div v-else-if="!filters.seller"
        class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-24 text-center">
        <Store class="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 class="text-base font-bold text-gray-700">Select a Seller</h3>
        <p class="text-sm text-gray-400 mt-1">Category selected! Now pick a seller from the sidebar.</p>
      </div>

      <div v-else-if="items.loading" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        <div v-for="i in 8" :key="i" class="h-60 bg-gray-100 rounded-2xl animate-pulse" />
      </div>

      <template v-else-if="allItems.length > 0">

        <div class="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-xl px-4 py-2.5">
          <TrendingUp class="w-4 h-4 text-blue-500 flex-shrink-0" />
          <p class="text-xs text-blue-700">
            Prices shown are <span class="font-semibold">{{ todayName }}'s rates</span>.
            <span v-if="unavailableItems.length" class="text-orange-600 font-semibold ml-1">
              · {{ unavailableItems.length }} item(s) unavailable today.
            </span>
          </p>
        </div>

        <!-- ══ SUBSCRIPTION ITEMS ══ -->
        <div v-if="subscriptionItems.length > 0" class="mb-6">
          <div class="flex items-center gap-2 mb-4">
            <Newspaper class="w-5 h-5 text-blue-600" />
            <h3 class="text-base font-bold text-gray-900">Newspaper Subscriptions</h3>
            <Badge label="Day-wise Delivery" theme="blue" size="sm" />
          </div>

          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            <div v-for="item in subscriptionItems" :key="item.name"
              class="bg-gradient-to-br from-blue-50 to-white rounded-2xl border-2 border-blue-100 overflow-hidden hover:shadow-lg transition-all flex flex-col group">
              <div class="aspect-square bg-white relative overflow-hidden">
                <img v-if="item.image" :src="item.image"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                <div v-else class="w-full h-full flex items-center justify-center bg-blue-50">
                  <Newspaper class="w-12 h-12 text-blue-200" />
                </div>

                <!-- Status badge overlay -->
                <div class="absolute top-2 left-2">
                  <div v-if="isActiveSubscribed(item.item_code)"
                    class="bg-green-500 text-white text-[9px] font-bold px-2 py-1 rounded-full flex items-center gap-1 shadow">
                    <CheckCircle class="w-2.5 h-2.5" /> Active
                  </div>
                  <div v-else-if="isPendingSubscribed(item.item_code)"
                    class="bg-amber-500 text-white text-[9px] font-bold px-2 py-1 rounded-full flex items-center gap-1 shadow">
                    <Hourglass class="w-2.5 h-2.5" /> Pending
                  </div>
                  <div v-else
                    class="bg-blue-600 text-white text-[9px] font-bold px-2 py-1 rounded-full flex items-center gap-1 shadow">
                    <Calendar class="w-2.5 h-2.5" /> Subscribe
                  </div>
                </div>
              </div>

              <div class="p-3 flex-1 flex flex-col justify-between">
                <div>
                  <h4 class="font-bold text-gray-800 line-clamp-2 text-sm">{{ item.item_name }}</h4>
                  <p class="text-[10px] text-blue-600 mt-0.5 uppercase tracking-tight font-semibold">{{ item.item_group
                    }}</p>
                  <p v-if="getSubName(item.item_code)" class="text-[10px] font-semibold mt-0.5 truncate"
                    :class="isPendingSubscribed(item.item_code) ? 'text-amber-600' : 'text-green-600'">
                    {{ getSubName(item.item_code) }}
                  </p>

                  <!-- Day price preview (mini) -->
                  <div class="flex flex-wrap gap-0.5 mt-2">
                    <template v-for="day in ALL_DAYS" :key="day">
                      <div v-if="item.day_prices?.[day] > 0"
                        class="text-[8px] px-1 py-0.5 rounded bg-blue-50 border border-blue-100 text-blue-600 font-semibold"
                        :title="`${day}: ₹${item.day_prices[day]}`">{{ DAY_SHORT[day] }}</div>
                    </template>
                  </div>
                </div>

                <div class="mt-3 space-y-1.5">
                  <div class="flex items-baseline gap-1">
                    <span class="text-base font-black text-gray-900">{{ item.formatted_price }}</span>
                    <span class="text-[10px] text-gray-400">today</span>
                  </div>

                  <div v-if="isActiveSubscribed(item.item_code)"
                    class="text-center py-1.5 text-[10px] text-green-600 font-bold bg-green-50 rounded-lg border border-green-100">
                    ✓ Active Subscription
                  </div>

                  <div v-else-if="isPendingSubscribed(item.item_code)"
                    class="text-center py-2 text-[10px] text-amber-700 font-bold bg-amber-50 rounded-lg border border-amber-200">
                    <Hourglass class="w-3 h-3 inline mr-1" />
                    Awaiting Seller Approval
                  </div>

                  <Button v-else variant="solid" theme="blue" class="w-full" size="sm"
                    @click="openSubscriptionModal(item)">
                    <template #prefix>
                      <Calendar class="w-3 h-3" />
                    </template>
                    Subscribe
                  </Button>

                  <!-- Block manual order if active sub -->
                  <div v-if="isNormalOrderBlocked(item.item_code)"
                    class="text-center py-1.5 text-[10px] text-gray-400 font-medium bg-gray-50 rounded-lg">
                    📦 Auto-delivered today via subscription
                  </div>
                  <div v-else-if="isPendingSubscribed(item.item_code)"
                    class="text-center py-1.5 text-[10px] text-amber-500 font-medium bg-amber-50 rounded-lg">
                    Manual order blocked — awaiting activation
                  </div>
                  <template v-else>
                    <Button v-if="!cart[item.name]" variant="outline" class="w-full" size="sm"
                      @click="updateCart(item.name, 1)">
                      Buy Today
                    </Button>
                    <div v-else class="flex items-center justify-between bg-gray-50 rounded-lg p-0.5 border">
                      <Button variant="ghost" size="sm" @click="updateCart(item.name, -1)">
                        <template #icon>
                          <Minus class="w-3 h-3" />
                        </template>
                      </Button>
                      <span class="font-bold text-sm text-blue-600">{{ cart[item.name] }}</span>
                      <Button variant="ghost" size="sm" @click="updateCart(item.name, 1)">
                        <template #icon>
                          <Plus class="w-3 h-3" />
                        </template>
                      </Button>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ══ REGULAR ITEMS ══ -->
        <div v-if="regularItems.length > 0">
          <div v-if="subscriptionItems.length > 0" class="flex items-center gap-2 mb-4">
            <Package class="w-5 h-5 text-gray-600" />
            <h3 class="text-base font-bold text-gray-900">Regular Products</h3>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5 mb-6">
            <div v-for="item in regularItems" :key="item.name"
              class="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-lg transition-all flex flex-col group">
              <div class="aspect-square bg-gray-50 relative overflow-hidden">
                <img v-if="item.image" :src="item.image"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <Package class="w-10 h-10 text-gray-200" />
                </div>
                <div v-if="cart[item.name]" class="absolute top-2 right-2">
                  <Badge :label="`${cart[item.name]}`" theme="blue" />
                </div>
                <div v-if="hasDailyPrice(item)" class="absolute top-2 left-2">
                  <div
                    class="bg-emerald-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full flex items-center gap-0.5 shadow">
                    <TrendingUp class="w-2.5 h-2.5" />{{ todayShort }}
                  </div>
                </div>
              </div>
              <div class="p-3 flex-1 flex flex-col justify-between">
                <div>
                  <h4 class="font-bold text-gray-800 line-clamp-2 text-sm">{{ item.item_name }}</h4>
                  <p class="text-[10px] text-gray-400 mt-0.5 uppercase tracking-tight">{{ item.item_group }}</p>
                </div>
                <div class="mt-3">
                  <div class="flex items-baseline gap-1 mb-1">
                    <span class="text-base font-black text-gray-900">{{ item.formatted_price }}</span>
                    <span class="text-[10px] text-gray-400">/ {{ item.stock_uom }}</span>
                  </div>
                  <Button v-if="!cart[item.name]" variant="outline" class="w-full" size="sm"
                    @click="updateCart(item.name, 1)">
                    Add to Cart
                  </Button>
                  <div v-else class="flex items-center justify-between bg-gray-50 rounded-lg p-0.5 border">
                    <Button variant="ghost" size="sm" @click="updateCart(item.name, -1)">
                      <template #icon>
                        <Minus class="w-3 h-3" />
                      </template>
                    </Button>
                    <span class="font-bold text-sm text-blue-600">{{ cart[item.name] }}</span>
                    <Button variant="ghost" size="sm" @click="updateCart(item.name, 1)">
                      <template #icon>
                        <Plus class="w-3 h-3" />
                      </template>
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Unavailable -->
        <div v-if="unavailableItems.length > 0" class="space-y-3">
          <div class="flex items-center gap-2">
            <div class="flex-1 h-px bg-gray-100" />
            <div class="flex items-center gap-1.5 text-xs text-gray-400 font-semibold px-2">
              <AlertCircle class="w-3.5 h-3.5 text-orange-400" /> Not Available Today
            </div>
            <div class="flex-1 h-px bg-gray-100" />
          </div>
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            <div v-for="item in unavailableItems" :key="item.name"
              class="bg-gray-50 rounded-2xl border border-gray-100 overflow-hidden flex flex-col opacity-60">
              <div class="aspect-square bg-gray-100 relative overflow-hidden">
                <img v-if="item.image" :src="item.image" class="w-full h-full object-cover grayscale" />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <Package class="w-10 h-10 text-gray-300" />
                </div>
                <div class="absolute inset-0 flex items-center justify-center">
                  <div class="bg-white/90 border border-orange-200 rounded-lg px-2 py-1 flex items-center gap-1">
                    <AlertCircle class="w-3 h-3 text-orange-500" />
                    <span class="text-[10px] font-bold text-orange-600">Unavailable</span>
                  </div>
                </div>
              </div>
              <div class="p-3">
                <h4 class="font-bold text-gray-500 text-sm line-clamp-2">{{ item.item_name }}</h4>
                <p class="text-[10px] text-orange-500 font-semibold mt-1">{{ item.price_reason || `No price for
                  ${todayName}` }}
                </p>
              </div>
            </div>
          </div>
        </div>

      </template>

      <div v-else-if="!items.loading && filters.seller && filters.category" class="text-center py-20">
        <Package class="w-10 h-10 text-gray-300 mx-auto mb-2" />
        <p class="text-gray-500 text-sm">No products found.</p>
      </div>

    </template>

    <!-- ════════════════════════════════════════ -->
    <!-- MY ORDERS TAB                            -->
    <!-- ════════════════════════════════════════ -->
    <template v-if="activeTab === 'orders'">
      <div v-if="ordersResource.loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-20 bg-gray-100 rounded-2xl animate-pulse" />
      </div>

      <div v-else-if="allOrders.length === 0"
        class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-28 text-center">
        <ClipboardList class="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 class="text-base font-bold text-gray-700">No Orders Yet</h3>
        <p class="text-sm text-gray-400 mt-1">Your placed orders will appear here.</p>
        <Button variant="outline" class="mt-4" @click="activeTab = 'shop'">
          <template #prefix>
            <Store class="w-4 h-4" />
          </template>
          Start Shopping
        </Button>
      </div>

      <div v-else class="space-y-3">
        <div v-for="order in allOrders" :key="order.name" :class="[
          'rounded-2xl border overflow-hidden hover:shadow-md transition-shadow',
          order.is_subscription_order ? 'bg-blue-50/40 border-blue-100' : 'bg-white border-gray-100'
        ]">
          <div class="flex items-center justify-between p-4 gap-3">
            <div class="flex items-center gap-3 min-w-0">
              <div :class="['p-2 rounded-xl flex-shrink-0', statusBg(order.status_color)]">
                <component :is="statusIcon(order.status_color)"
                  :class="['w-4 h-4', statusIconClass(order.status_color)]" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-bold text-gray-900 text-sm font-mono">{{ order.name }}</span>
                  <Badge :label="order.display_status" :theme="badgeTheme(order.status_color)" size="sm" />
                  <span v-if="order.is_subscription_order"
                    class="inline-flex items-center gap-1 bg-blue-100 text-blue-700 text-[9px] font-bold px-2 py-0.5 rounded-full">
                    <Newspaper class="w-2.5 h-2.5" /> Subscription Order
                  </span>
                </div>
                <p class="text-xs text-gray-400 mt-0.5">
                  {{ order.formatted_date }}<span v-if="order.seller"> · {{ order.seller }}</span>
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <span class="font-black text-gray-900 text-sm">{{ order.formatted_total }}</span>
              <Button v-if="order.can_cancel && !order.is_subscription_order" variant="subtle" theme="red" size="sm"
                @click="confirmCancel(order.name)">Cancel</Button>
              <Button variant="ghost" size="sm" @click="toggleExpand(order.name)">
                <template #icon>
                  <ChevronUp v-if="expandedOrder === order.name" class="w-4 h-4" />
                  <ChevronDown v-else class="w-4 h-4" />
                </template>
              </Button>
            </div>
          </div>

          <div v-if="expandedOrder === order.name" class="border-t border-gray-100/80 px-4 pb-5 pt-4 space-y-4">
            <div v-if="order.is_subscription_order"
              class="flex items-start gap-2 bg-blue-50 border border-blue-100 rounded-xl px-3 py-2.5">
              <Newspaper class="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
              <p class="text-xs text-blue-700">
                Auto-generated daily delivery order from your subscription plan.
              </p>
            </div>

            <div class="flex items-center gap-1">
              <template v-for="(step, idx) in timelineSteps(order)" :key="step.key">
                <div class="flex flex-col items-center gap-1">
                  <div :class="['w-7 h-7 rounded-full flex items-center justify-center',
                    step.done ? (step.key === 'completed' ? 'bg-green-500' : 'bg-blue-500') : 'bg-gray-100']">
                    <component :is="step.icon" :class="['w-3.5 h-3.5', step.done ? 'text-white' : 'text-gray-300']" />
                  </div>
                  <span :class="['text-[10px] font-semibold whitespace-nowrap',
                    step.done ? (step.key === 'completed' ? 'text-green-600' : 'text-blue-600') : 'text-gray-400']">
                    {{ step.label }}
                  </span>
                </div>
                <div v-if="idx < timelineSteps(order).length - 1"
                  :class="['flex-1 h-px mb-4', step.lineAfter ? 'bg-blue-200' : 'bg-gray-100']" />
              </template>
            </div>

            <div class="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
              <FileText class="w-4 h-4 text-gray-400 flex-shrink-0" />
              <p class="text-xs text-gray-500">
                Expected delivery: <span class="font-semibold text-gray-700">{{ order.delivery_date || 'To be confirmed'
                  }}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ════════════════════════════════════════ -->
    <!-- MY PLANS (SUBSCRIPTIONS) TAB             -->
    <!-- ════════════════════════════════════════ -->
    <template v-if="activeTab === 'subscriptions'">
      <div v-if="ordersResource.loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-32 bg-gray-100 rounded-2xl animate-pulse" />
      </div>

      <div v-else-if="allSubscriptions.length === 0"
        class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-28 text-center">
        <Newspaper class="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 class="text-base font-bold text-gray-700">No Subscription Plans Yet</h3>
        <p class="text-sm text-gray-400 mt-1">Browse newspapers to subscribe for daily delivery.</p>
        <Button variant="outline" class="mt-4" @click="activeTab = 'shop'">
          <template #prefix>
            <Store class="w-4 h-4" />
          </template>
          Browse Products
        </Button>
      </div>

      <div v-else class="space-y-4">
        <div v-for="sub in allSubscriptions" :key="sub.name"
          class="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
          <div class="p-4 flex items-start justify-between gap-3">
            <div class="flex items-center gap-3">
              <div class="p-2.5 bg-blue-50 rounded-xl text-blue-600">
                <Newspaper class="w-5 h-5" />
              </div>
              <div>
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-bold text-gray-900 text-sm font-mono">{{ sub.name }}</span>
                  <span
                    :class="['text-[10px] font-bold px-2 py-0.5 rounded-full border', subStatusColor[sub.status] || 'bg-gray-100 text-gray-500 border-gray-200']">
                    {{ sub.status }}
                  </span>
                </div>
                <p class="text-xs text-gray-400 mt-0.5">
                  {{ sub.formatted_start }} → {{ sub.formatted_end }}
                  <span v-if="sub.seller" class="ml-2">· {{ sub.seller }}</span>
                </p>
              </div>
            </div>
          </div>

          <!-- Schedule summary -->
          <div class="px-4 pb-4 space-y-3">
            <div v-for="si in sub.schedule_items" :key="si.item_code"
              class="bg-gray-50 rounded-xl p-3 border border-gray-100">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-gray-700">{{ si.item_name }}</span>
                <span v-if="si.is_primary_item"
                  class="text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-bold">Primary</span>
              </div>
              <div class="flex gap-1.5 flex-wrap">
                <template v-for="day in ALL_DAYS" :key="day">
                  <div :class="[
                    'flex flex-col items-center px-2 py-1 rounded-lg text-[9px] font-bold',
                    (si[DAY_QTY_FIELD[day]] || 0) > 0
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-400'
                  ]">
                    <span>{{ DAY_SHORT[day] }}</span>
                    <span v-if="(si[DAY_QTY_FIELD[day]] || 0) > 0" class="text-[8px] opacity-80">
                      ×{{ si[DAY_QTY_FIELD[day]] }}
                    </span>
                  </div>
                </template>
              </div>
            </div>

            <div v-if="sub.status === 'Accept Pending'"
              class="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
              <Hourglass class="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
              <p class="text-xs text-amber-700">Waiting for seller approval. Once accepted, daily delivery starts from
                next
                day.</p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ════════════════════════════════════════ -->
    <!-- SUBSCRIPTION MODAL — DAY-WISE            -->
    <!-- ════════════════════════════════════════ -->
    <Dialog v-model="subscriptionModalOpen" :options="{ title: 'Create Subscription Plan', size: 'lg' }">
      <template #body-content>
        <div class="space-y-5">

          <!-- Flow info -->
          <div class="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
            <Hourglass class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <p class="font-semibold text-sm text-amber-800">How it works</p>
              <p class="text-xs text-amber-700 mt-1">
                After you send the request, seller will review it. Once accepted, daily delivery starts from the next
                day automatically via our system.
              </p>
            </div>
          </div>

          <!-- Primary item info -->
          <div class="flex items-start gap-3 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
            <Newspaper class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div class="flex-1">
              <p class="font-semibold text-sm text-blue-900">{{ selectedSubscriptionItem?.item_name }}</p>
              <p class="text-xs text-blue-600 mt-0.5">Primary item — configure day-wise delivery below</p>
            </div>
          </div>

          <!-- PRIMARY ITEM — DAY-WISE SCHEDULE -->
          <div v-if="selectedSubscriptionItem">
            <label class="text-xs font-bold text-gray-700 mb-2 block uppercase tracking-wide">
              📅 Day-wise Delivery Schedule — {{ selectedSubscriptionItem.item_name }}
            </label>
            <div class="border border-gray-200 rounded-xl overflow-hidden">
              <table class="w-full text-xs">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th class="px-3 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Day</th>
                    <th class="px-3 py-2 text-center font-bold text-gray-500 uppercase tracking-wide">Deliver?</th>
                    <th class="px-3 py-2 text-center font-bold text-gray-500 uppercase tracking-wide">Qty</th>
                    <th class="px-3 py-2 text-right font-bold text-gray-500 uppercase tracking-wide">Price/copy</th>
                    <th class="px-3 py-2 text-right font-bold text-gray-500 uppercase tracking-wide">Day Cost</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="day in ALL_DAYS" :key="day"
                    :class="isDayActive(selectedSubscriptionItem.item_code, day) ? 'bg-blue-50/50' : 'bg-white'">
                    <td class="px-3 py-2 font-semibold text-gray-700">{{ day }}</td>
                    <td class="px-3 py-2 text-center">
                      <button @click="toggleDay(selectedSubscriptionItem.item_code, day)" :class="[
                        'w-8 h-5 rounded-full transition-colors relative',
                        isDayActive(selectedSubscriptionItem.item_code, day) ? 'bg-blue-600' : 'bg-gray-200'
                      ]">
                        <span :class="[
                          'absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform',
                          isDayActive(selectedSubscriptionItem.item_code, day) ? 'translate-x-3' : 'translate-x-0.5'
                        ]" />
                      </button>
                    </td>
                    <td class="px-3 py-2">
                      <div v-if="isDayActive(selectedSubscriptionItem.item_code, day)"
                        class="flex items-center justify-center gap-1">
                        <button
                          @click="setDayQty(selectedSubscriptionItem.item_code, day, getDayQty(selectedSubscriptionItem.item_code, day) - 1)"
                          :disabled="getDayQty(selectedSubscriptionItem.item_code, day) <= 1"
                          class="w-5 h-5 rounded bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 font-bold disabled:opacity-30 text-xs">−</button>
                        <span class="w-5 text-center font-black text-blue-600 text-sm">
                          {{ getDayQty(selectedSubscriptionItem.item_code, day) }}
                        </span>
                        <button
                          @click="setDayQty(selectedSubscriptionItem.item_code, day, getDayQty(selectedSubscriptionItem.item_code, day) + 1)"
                          :disabled="getDayQty(selectedSubscriptionItem.item_code, day) >= 99"
                          class="w-5 h-5 rounded bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 font-bold disabled:opacity-30 text-xs">+</button>
                      </div>
                      <span v-else class="block text-center text-gray-300 font-bold">—</span>
                    </td>
                    <td class="px-3 py-2 text-right text-gray-500">
                      <span v-if="getDayPrice(selectedSubscriptionItem, day) > 0">
                        ₹{{ getDayPrice(selectedSubscriptionItem, day) }}
                      </span>
                      <span v-else class="text-red-400 text-[10px]">No price</span>
                    </td>
                    <td class="px-3 py-2 text-right font-bold"
                      :class="isDayActive(selectedSubscriptionItem.item_code, day) ? 'text-gray-800' : 'text-gray-300'">
                      <span
                        v-if="isDayActive(selectedSubscriptionItem.item_code, day) && getDayPrice(selectedSubscriptionItem, day) > 0">
                        ₹{{ (getDayQty(selectedSubscriptionItem.item_code, day) * getDayPrice(selectedSubscriptionItem,
                        day)).toFixed(2) }}
                      </span>
                      <span v-else>—</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- ADDITIONAL ITEMS -->
          <div v-if="availableAdditionalItems.length > 0">
            <label class="text-xs font-bold text-gray-700 mb-2 block uppercase tracking-wide">
              ➕ Add More Items (Optional)
            </label>
            <div class="space-y-3">
              <div v-for="aitem in availableAdditionalItems" :key="aitem.item_code">
                <!-- Select/Deselect button -->
                <div @click="toggleAdditionalItem(aitem)" :class="[
                  'flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all',
                  isAdditionalItemSelected(aitem.item_code)
                    ? 'border-purple-300 bg-purple-50'
                    : 'border-gray-200 bg-gray-50 hover:border-gray-300'
                ]">
                  <div class="flex items-center gap-2">
                    <div :class="[
                      'w-4 h-4 rounded border-2 flex items-center justify-center',
                      isAdditionalItemSelected(aitem.item_code) ? 'border-purple-500 bg-purple-500' : 'border-gray-300'
                    ]">
                      <CheckCircle v-if="isAdditionalItemSelected(aitem.item_code)" class="w-3 h-3 text-white" />
                    </div>
                    <span class="text-xs font-semibold text-gray-700">{{ aitem.item_name }}</span>
                  </div>
                  <span class="text-[10px] text-gray-500">Today: {{ aitem.formatted_price }}</span>
                </div>

                <!-- Day-wise schedule for additional item -->
                <div v-if="isAdditionalItemSelected(aitem.item_code)"
                  class="mt-2 ml-2 border border-purple-200 rounded-xl overflow-hidden">
                  <table class="w-full text-xs">
                    <thead class="bg-purple-50 border-b border-purple-200">
                      <tr>
                        <th class="px-3 py-1.5 text-left font-bold text-purple-600">Day</th>
                        <th class="px-3 py-1.5 text-center font-bold text-purple-600">Deliver?</th>
                        <th class="px-3 py-1.5 text-center font-bold text-purple-600">Qty</th>
                        <th class="px-3 py-1.5 text-right font-bold text-purple-600">Price</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-purple-100">
                      <tr v-for="day in ALL_DAYS" :key="day"
                        :class="isDayActive(aitem.item_code, day) ? 'bg-purple-50/30' : 'bg-white'">
                        <td class="px-3 py-1.5 font-semibold text-gray-600">{{ DAY_SHORT[day] }}</td>
                        <td class="px-3 py-1.5 text-center">
                          <button @click="toggleDay(aitem.item_code, day)" :class="[
                            'w-7 h-4 rounded-full transition-colors relative',
                            isDayActive(aitem.item_code, day) ? 'bg-purple-500' : 'bg-gray-200'
                          ]">
                            <span :class="[
                              'absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform',
                              isDayActive(aitem.item_code, day) ? 'translate-x-3' : 'translate-x-0.5'
                            ]" />
                          </button>
                        </td>
                        <td class="px-3 py-1.5">
                          <div v-if="isDayActive(aitem.item_code, day)" class="flex items-center justify-center gap-1">
                            <button @click="setDayQty(aitem.item_code, day, getDayQty(aitem.item_code, day) - 1)"
                              :disabled="getDayQty(aitem.item_code, day) <= 1"
                              class="w-4 h-4 rounded bg-gray-100 hover:bg-gray-200 flex items-center justify-center font-bold disabled:opacity-30 text-xs">−</button>
                            <span class="w-4 text-center font-black text-purple-600">{{ getDayQty(aitem.item_code, day)
                              }}</span>
                            <button @click="setDayQty(aitem.item_code, day, getDayQty(aitem.item_code, day) + 1)"
                              :disabled="getDayQty(aitem.item_code, day) >= 99"
                              class="w-4 h-4 rounded bg-gray-100 hover:bg-gray-200 flex items-center justify-center font-bold disabled:opacity-30 text-xs">+</button>
                          </div>
                          <span v-else class="block text-center text-gray-300">—</span>
                        </td>
                        <td class="px-3 py-1.5 text-right text-gray-500">
                          <span v-if="getDayPrice(aitem, day) > 0">₹{{ getDayPrice(aitem, day) }}</span>
                          <span v-else class="text-red-400 text-[9px]">No price</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <!-- START DATE & DURATION -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs font-bold text-gray-700 mb-1.5 block">Start Date</label>
              <input type="date" v-model="subForm.startDate"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
            </div>
            <div>
              <label class="text-xs font-bold text-gray-700 mb-1.5 block">Duration</label>
              <select v-model="subForm.months"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option :value="1">1 Month</option>
                <option :value="3">3 Months</option>
                <option :value="6">6 Months</option>
                <option :value="12">12 Months</option>
              </select>
            </div>
          </div>
          <!-- Error -->
          <div v-if="subscriptionError" class="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
            <p class="text-xs text-red-700">{{ subscriptionError }}</p>
          </div>
        </div>
      </template>

      <template #actions>
        <div class="flex gap-2 w-full">
          <Button variant="outline" class="flex-1" @click="subscriptionModalOpen = false">Cancel</Button>
          <Button variant="solid" theme="blue" class="flex-1" :loading="isCreatingSubscription"
            @click="handleCreateSubscription">
            <template #prefix>
              <CheckCircle v-if="!isCreatingSubscription" class="w-4 h-4" />
            </template>
            Send Subscription Request
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- ════════════════════════════════════════ -->
    <!-- CHECKOUT DIALOG                          -->
    <!-- ════════════════════════════════════════ -->
    <Dialog v-model="checkoutOpen" :options="{ title: 'Order Summary', size: 'lg' }">
      <template #body-content>
        <div class="space-y-4">
          <div v-if="filters.pincode || filters.society"
            class="flex items-start gap-2 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
            <MapPin class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
            <p class="text-xs text-blue-700">
              <span class="font-semibold">Delivery to: </span>
              <span v-if="filters.society">{{ filters.society }}</span>
              <span v-if="filters.society && filters.pincode"> · </span>
              <span v-if="filters.pincode">PIN {{ filters.pincode }}</span>
            </p>
          </div>

          <div class="space-y-2 max-h-72 overflow-y-auto pr-1">
            <div v-for="item in cartItemsWithDetails" :key="item.name"
              class="flex items-center gap-3 bg-gray-50 rounded-xl p-3 border border-gray-100">
              <div
                class="w-11 h-11 rounded-lg overflow-hidden bg-white border border-gray-100 flex-shrink-0 flex items-center justify-center">
                <img v-if="item.image" :src="item.image" class="w-full h-full object-cover" />
                <Package v-else class="w-5 h-5 text-gray-200" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-semibold text-gray-800 text-sm line-clamp-1">{{ item.item_name }}</p>
                <p class="text-xs text-gray-400">{{ item.formatted_price }} / {{ item.stock_uom }}</p>
                <div class="flex items-center gap-1 mt-1.5 bg-white rounded-lg border border-gray-200 w-fit p-0.5">
                  <Button variant="ghost" size="sm" @click="updateCart(item.name, -1)">
                    <template #icon>
                      <Minus class="w-3 h-3" />
                    </template>
                  </Button>
                  <span class="font-bold text-sm text-blue-600 w-5 text-center">{{ item.qty }}</span>
                  <Button variant="ghost" size="sm" @click="updateCart(item.name, 1)">
                    <template #icon>
                      <Plus class="w-3 h-3" />
                    </template>
                  </Button>
                </div>
              </div>
              <div class="flex flex-col items-end gap-2 flex-shrink-0">
                <span class="font-bold text-sm text-gray-900">{{ formatCurrency(item.subtotal) }}</span>
                <Button variant="ghost" size="sm" theme="red" @click="removeFromCart(item.name)">
                  <template #icon>
                    <Trash2 class="w-3 h-3" />
                  </template>
                </Button>
              </div>
            </div>
          </div>

          <div class="border-t border-gray-100 pt-3 space-y-1.5 text-sm">
            <div class="flex justify-between text-gray-500">
              <span>Subtotal ({{ totalCartItems }} items)</span>
              <span>{{ formatCurrency(cartTotal) }}</span>
            </div>
            <div class="flex justify-between text-gray-500">
              <span>Delivery</span>
              <span class="text-green-600 font-semibold">Free</span>
            </div>
            <div class="flex justify-between font-black text-gray-900 pt-2 border-t border-gray-100">
              <span>Total</span>
              <span>{{ formatCurrency(cartTotal) }}</span>
            </div>
          </div>

          <div v-if="placeOrderError" class="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl px-4 py-3">
            {{ placeOrderError }}
          </div>
        </div>
      </template>

      <template #actions>
        <div class="flex gap-2 w-full">
          <Button variant="outline" class="flex-1" @click="checkoutOpen = false">Cancel</Button>
          <Button variant="solid" theme="blue" class="flex-1" :loading="isPlacingOrder"
            :disabled="isPlacingOrder || cartItemsWithDetails.length === 0" @click="handlePlaceOrder">
            <template #prefix>
              <CheckCircle v-if="!isPlacingOrder" class="w-4 h-4" />
            </template>
            {{ isPlacingOrder ? 'Placing Order...' : 'Place Order' }}
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- Cancel Confirm -->
    <Dialog v-model="cancelConfirmOpen"
      :options="{ title: 'Cancel Order', message: `Are you sure you want to cancel ${cancelTargetOrder}?`, size: 'sm' }">
      <template #actions>
        <div class="flex gap-2 w-full">
          <Button variant="outline" class="flex-1" @click="cancelConfirmOpen = false">Keep Order</Button>
          <Button variant="solid" theme="red" class="flex-1" :loading="cancelOrderResource.loading"
            @click="executeCancel">Yes, Cancel</Button>
        </div>
      </template>
    </Dialog>

  </div>
</template>
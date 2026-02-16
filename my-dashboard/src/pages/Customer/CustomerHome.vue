<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { createResource, Badge, Button, Dialog } from 'frappe-ui'
import {
  ShoppingCart, Package, RefreshCcw, Store, Plus, Minus,
  Trash2, MapPin, ShoppingBag, CheckCircle, ClipboardList,
  ChevronDown, ChevronUp, XCircle, Clock, Truck, FileText,
  Calendar, TrendingUp, AlertCircle, Info
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
const activeTab = ref<'shop' | 'orders'>('shop')

// ─── SHOP STATE ───
const cart = ref<Record<string, number>>({})
const checkoutOpen   = ref(false)
const isPlacingOrder = ref(false)
const placeOrderError = ref('')
const orderPlaced    = ref(false)
const placedOrderId  = ref('')
const placedOrderTotal = ref('')
const skippedItems   = ref<string[]>([])  // unavailable items jo order mein nahi gaye

// ─── ORDERS STATE ───
const expandedOrder     = ref<string | null>(null)
const cancelConfirmOpen = ref(false)
const cancelTargetOrder = ref<string | null>(null)

// ─── TODAY INFO ───
const todayName = computed(() => {
  const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
  return days[new Date().getDay()]
})
const todayShort = computed(() => todayName.value.slice(0, 3))

// ─── RESOURCES ───
const items = createResource({
  url: 'my_frappe_app.api.get_seller_items',
  debounce: 300,
})

const ordersResource = createResource({
  url: 'my_frappe_app.api.get_customer_orders',
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
      placedOrderId.value    = data.order_id
      placedOrderTotal.value = data.formatted_total
      skippedItems.value     = data.skipped_items || []
      cart.value             = {}
      checkoutOpen.value     = false
      orderPlaced.value      = true
      if (props.filters.customer) {
        ordersResource.fetch({ customer: props.filters.customer })
      }
    } else {
      placeOrderError.value = data.message || 'Something went wrong.'
    }
  },
  onError(err: any) {
    isPlacingOrder.value  = false
    placeOrderError.value = err?.message || 'Failed to place order.'
  },
})

// ─── WATCHERS ───
watch(
  () => props.filters,
  (f) => {
    if (f?.seller) {
      items.fetch({ seller: f.seller, category: f.category || null })
    }
    if (f?.customer) {
      ordersResource.fetch({ customer: f.customer })
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

// Available items - jinki price_available = true hai
const availableItems = computed(() =>
  allItems.value.filter((i: any) => i.price_available)
)

// Unavailable items - seller ne price set nahi ki aaj ke liye
const unavailableItems = computed(() =>
  allItems.value.filter((i: any) => !i.price_available)
)

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

// Daily price badge - price standard_rate se alag hai
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
  isPlacingOrder.value  = true

  placeOrderResource.fetch({
    cart_data:        JSON.stringify(cart.value),
    customer:         props.filters.customer,
    seller:           props.filters.seller,
    pincode:          props.filters.pincode || '',
    society:          props.filters.society || null,
    delivery_address: props.filters.delivery_address || null,
  })
}

const openCheckout = () => {
  placeOrderError.value = ''
  checkoutOpen.value    = true
}

// ─── ORDER STATUS HELPERS ───
const orders = computed(() => (ordersResource.data as any)?.orders || [])

const statusIcon = (color: string) => ({
  orange: Clock, blue: CheckCircle, purple: Truck,
  green: CheckCircle, red: XCircle, gray: Clock,
}[color] || Clock)

const statusIconClass = (color: string) => ({
  orange: 'text-orange-500', blue: 'text-blue-500',
  purple: 'text-blue-500',  green: 'text-green-500',
  red: 'text-red-500',      gray: 'text-gray-400',
}[color] || 'text-gray-400')

const statusBg = (color: string) => ({
  orange: 'bg-orange-50', blue: 'bg-blue-50',
  purple: 'bg-blue-50',  green: 'bg-green-50',
  red: 'bg-red-50',      gray: 'bg-gray-50',
}[color] || 'bg-gray-50')

type BadgeTheme = 'blue' | 'green' | 'red' | 'orange' | 'gray'
const badgeTheme = (color: string): BadgeTheme =>
  ({ orange:'orange', blue:'blue', purple:'blue', green:'green', red:'red', gray:'gray' }[color] as BadgeTheme) || 'gray'

const toggleExpand  = (name: string) => {
  expandedOrder.value = expandedOrder.value === name ? null : name
}
const confirmCancel = (name: string) => {
  cancelTargetOrder.value = name
  cancelConfirmOpen.value = true
}
const executeCancel = () => {
  if (cancelTargetOrder.value)
    cancelOrderResource.fetch({ order_id: cancelTargetOrder.value })
}

const timelineSteps = (order: any) => [
  { key:'placed',    label:'Placed',    icon:CheckCircle, done:true,                        lineAfter: order.docstatus >= 1 },
  { key:'accepted',  label:'Accepted',  icon:CheckCircle, done:order.docstatus >= 1,        lineAfter: order.per_delivered >= 100 },
  { key:'delivered', label:'Delivered', icon:Truck,       done:order.per_delivered >= 100,  lineAfter: order.status === 'Completed' },
  { key:'completed', label:'Completed', icon:CheckCircle, done:order.status === 'Completed', lineAfter: false },
]
</script>

<template>
  <div class="p-6 space-y-5 max-w-7xl mx-auto">

    <!-- ─── HEADER ─── -->
    <div class="flex justify-between items-center bg-white p-5 rounded-2xl border border-gray-100 shadow-sm">
      <div class="flex items-center gap-4">
        <div class="p-3 bg-blue-600 rounded-xl text-white shadow-lg">
          <ShoppingCart class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-lg font-bold text-gray-900">Customer Portal</h2>
          <p class="text-xs text-gray-400">
            {{ filters.seller ? filters.seller : 'Select a seller to browse products' }}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <div
          v-if="activeTab === 'shop' && filters.seller"
          class="hidden sm:flex items-center gap-1.5 bg-blue-50 border border-blue-100 rounded-lg px-3 py-1.5"
        >
          <Calendar class="w-3.5 h-3.5 text-blue-500" />
          <span class="text-xs font-semibold text-blue-700">{{ todayName }} Rates</span>
        </div>

        <Button
          v-if="activeTab === 'shop' && items.data"
          variant="outline" size="sm" :loading="items.loading"
          @click="items.fetch({ seller: filters.seller, category: filters.category || null })"
        >
          <template #prefix><RefreshCcw class="w-3.5 h-3.5" /></template>
        </Button>

        <Button
          v-if="activeTab === 'orders'"
          variant="outline" size="sm" :loading="ordersResource.loading"
          @click="ordersResource.reload()"
        >
          <template #prefix><RefreshCcw class="w-3.5 h-3.5" /></template>
        </Button>

        <Button
          v-if="totalCartItems > 0 && activeTab === 'shop'"
          variant="solid" theme="blue" @click="openCheckout"
        >
          <template #prefix><ShoppingBag class="w-4 h-4" /></template>
          {{ totalCartItems }} items · {{ formatCurrency(cartTotal) }}
        </Button>
      </div>
    </div>

    <!-- ─── TABS ─── -->
    <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
      <button
        @click="activeTab = 'shop'"
        :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all',
          activeTab === 'shop' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']"
      >
        <Store class="w-4 h-4" /> Shop
      </button>
      <button
        @click="activeTab = 'orders'"
        :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all',
          activeTab === 'orders' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']"
      >
        <ClipboardList class="w-4 h-4" /> My Orders
        <Badge v-if="orders.length > 0" :label="String(orders.length)" theme="blue" size="sm" />
      </button>
    </div>

    <!-- ─── ORDER PLACED SUCCESS ─── -->
    <div
      v-if="orderPlaced"
      class="bg-green-50 border border-green-200 rounded-2xl p-4 space-y-2"
    >
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
        <Button variant="ghost" size="sm" @click="orderPlaced = false; skippedItems = []">✕</Button>
      </div>

      <!-- Skipped items warning (items jo price nahi thi) -->
      <div
        v-if="skippedItems.length > 0"
        class="flex items-start gap-2 bg-orange-50 border border-orange-200 rounded-xl px-3 py-2 ml-8"
      >
        <AlertCircle class="w-3.5 h-3.5 text-orange-500 mt-0.5 flex-shrink-0" />
        <p class="text-xs text-orange-700">
          <span class="font-semibold">{{ skippedItems.length }} item(s) skipped</span>
          — seller has not set price for today:
          <span class="font-semibold">{{ skippedItems.join(', ') }}</span>
        </p>
      </div>
    </div>

    <!-- ════════════════════════════════════════ -->
    <!-- SHOP TAB                                 -->
    <!-- ════════════════════════════════════════ -->
    <template v-if="activeTab === 'shop'">

      <div
        v-if="!filters.seller"
        class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-28 text-center"
      >
        <Store class="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 class="text-base font-bold text-gray-700">Ready to Shop?</h3>
        <p class="text-sm text-gray-400 mt-1">Select a Seller from the sidebar.</p>
      </div>

      <div v-else-if="items.loading" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        <div v-for="i in 8" :key="i" class="h-60 bg-gray-100 rounded-2xl animate-pulse" />
      </div>

      <template v-else-if="allItems.length > 0">

        <!-- Daily price info banner -->
        <div class="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-xl px-4 py-2.5 mb-4">
          <TrendingUp class="w-4 h-4 text-blue-500 flex-shrink-0" />
          <p class="text-xs text-blue-700">
            Prices shown are <span class="font-semibold">{{ todayName }}'s rates</span>
            from Daily Item Price schedule.
            <span v-if="unavailableItems.length > 0" class="text-orange-600 font-semibold ml-1">
              · {{ unavailableItems.length }} item(s) unavailable today.
            </span>
          </p>
        </div>

        <!-- ── AVAILABLE ITEMS ── -->
        <div v-if="availableItems.length > 0" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5 mb-6">
          <div
            v-for="item in availableItems" :key="item.name"
            class="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-lg transition-all flex flex-col group"
          >
            <div class="aspect-square bg-gray-50 relative overflow-hidden">
              <img
                v-if="item.image" :src="item.image"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              />
              <div v-else class="w-full h-full flex items-center justify-center">
                <Package class="w-10 h-10 text-gray-200" />
              </div>

              <!-- Cart badge -->
              <div v-if="cart[item.name]" class="absolute top-2 right-2">
                <Badge :label="`${cart[item.name]} Added`" theme="blue" />
              </div>

              <!-- Daily price badge -->
              <div v-if="hasDailyPrice(item)" class="absolute top-2 left-2">
                <div class="bg-emerald-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full flex items-center gap-0.5 shadow">
                  <TrendingUp class="w-2.5 h-2.5" />
                  {{ todayShort }}
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
                  <!-- Daily Item Price ka aaj ka rate -->
                  <span class="text-base font-black text-gray-900">{{ item.formatted_price }}</span>
                  <span class="text-[10px] text-gray-400">/ {{ item.stock_uom }}</span>
                </div>

                <!-- Standard rate strikethrough agar daily price alag hai -->
                <div v-if="hasDailyPrice(item)" class="flex items-center gap-1 mb-2">
                  <span class="text-[10px] text-gray-400 line-through">
                    {{ formatCurrency(item.standard_rate) }}
                  </span>
                  <span class="text-[9px] text-emerald-600 font-semibold">Daily Rate</span>
                </div>

                <!-- Qty control -->
                <Button
                  v-if="!cart[item.name]"
                  variant="outline" class="w-full" size="sm"
                  @click="updateCart(item.name, 1)"
                >
                  Add to Cart
                </Button>
                <div
                  v-else
                  class="flex items-center justify-between bg-gray-50 rounded-lg p-0.5 border"
                >
                  <Button variant="ghost" size="sm" @click="updateCart(item.name, -1)">
                    <template #icon><Minus class="w-3 h-3" /></template>
                  </Button>
                  <span class="font-bold text-sm text-blue-600">{{ cart[item.name] }}</span>
                  <Button variant="ghost" size="sm" @click="updateCart(item.name, 1)">
                    <template #icon><Plus class="w-3 h-3" /></template>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── UNAVAILABLE ITEMS SECTION ── -->
        <!-- Seller ne aaj ke liye price set nahi ki ya end_date expire ho gayi -->
        <div v-if="unavailableItems.length > 0" class="space-y-3">

          <!-- Section header -->
          <div class="flex items-center gap-2">
            <div class="flex-1 h-px bg-gray-100" />
            <div class="flex items-center gap-1.5 text-xs text-gray-400 font-semibold px-2">
              <AlertCircle class="w-3.5 h-3.5 text-orange-400" />
              Not Available Today
            </div>
            <div class="flex-1 h-px bg-gray-100" />
          </div>

          <!-- Info note - seller ne price set nahi ki -->
          <div class="flex items-start gap-2 bg-orange-50 border border-orange-100 rounded-xl px-4 py-3">
            <Info class="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
            <p class="text-xs text-orange-700">
              The following items are <span class="font-semibold">not available for {{ todayName }}</span>.
              Seller has not set a price for today — please check back tomorrow or contact the seller.
            </p>
          </div>

          <!-- Unavailable items - grayed out cards -->
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            <div
              v-for="item in unavailableItems" :key="item.name"
              class="bg-gray-50 rounded-2xl border border-gray-100 overflow-hidden flex flex-col opacity-60"
            >
              <div class="aspect-square bg-gray-100 relative overflow-hidden">
                <img
                  v-if="item.image" :src="item.image"
                  class="w-full h-full object-cover grayscale"
                />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <Package class="w-10 h-10 text-gray-300" />
                </div>

                <!-- Unavailable overlay badge -->
                <div class="absolute inset-0 flex items-center justify-center">
                  <div class="bg-white/90 border border-orange-200 rounded-lg px-2 py-1 flex items-center gap-1 shadow-sm">
                    <AlertCircle class="w-3 h-3 text-orange-500" />
                    <span class="text-[10px] font-bold text-orange-600">Not Available</span>
                  </div>
                </div>
              </div>

              <div class="p-3 flex-1 flex flex-col justify-between">
                <div>
                  <h4 class="font-bold text-gray-500 line-clamp-2 text-sm">{{ item.item_name }}</h4>
                  <p class="text-[10px] text-gray-400 mt-0.5 uppercase tracking-tight">{{ item.item_group }}</p>
                </div>

                <div class="mt-3">
                  <!-- Price reason (from api) -->
                  <p class="text-[10px] text-orange-500 font-semibold mb-2">
                    {{ item.price_reason || `No price set for ${todayName}` }}
                  </p>
                  <!-- Disabled button -->
                  <button
                    disabled
                    class="w-full py-1.5 px-3 rounded-lg border border-gray-200 text-xs font-semibold text-gray-400 bg-gray-100 cursor-not-allowed"
                  >
                    Unavailable Today
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- No available items at all -->
        <div
          v-if="availableItems.length === 0 && unavailableItems.length === 0"
          class="text-center py-20"
        >
          <Package class="w-10 h-10 text-gray-300 mx-auto mb-2" />
          <p class="text-gray-500 text-sm font-medium">No products found.</p>
        </div>

      </template>

      <div v-else class="text-center py-20">
        <Package class="w-10 h-10 text-gray-300 mx-auto mb-2" />
        <p class="text-gray-500 text-sm font-medium">No products found.</p>
      </div>

    </template>

    <!-- ════════════════════════════════════════ -->
    <!-- MY ORDERS TAB                            -->
    <!-- ════════════════════════════════════════ -->
    <template v-if="activeTab === 'orders'">

      <div v-if="ordersResource.loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-20 bg-gray-100 rounded-2xl animate-pulse" />
      </div>

      <div
        v-else-if="orders.length === 0"
        class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-28 text-center"
      >
        <ClipboardList class="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 class="text-base font-bold text-gray-700">No Orders Yet</h3>
        <p class="text-sm text-gray-400 mt-1">Your placed orders will appear here.</p>
        <Button variant="outline" class="mt-4" @click="activeTab = 'shop'">
          <template #prefix><Store class="w-4 h-4" /></template>
          Start Shopping
        </Button>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="order in orders" :key="order.name"
          class="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
        >
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
                </div>
                <p class="text-xs text-gray-400 mt-0.5">
                  {{ order.formatted_date }}
                  <span v-if="order.seller"> · {{ order.seller }}</span>
                </p>
              </div>
            </div>

            <div class="flex items-center gap-2 flex-shrink-0">
              <span class="font-black text-gray-900 text-sm">{{ order.formatted_total }}</span>
              <Button
                v-if="order.can_cancel"
                variant="subtle" theme="red" size="sm"
                @click="confirmCancel(order.name)"
              >Cancel</Button>
              <Button variant="ghost" size="sm" @click="toggleExpand(order.name)">
                <template #icon>
                  <ChevronUp v-if="expandedOrder === order.name" class="w-4 h-4" />
                  <ChevronDown v-else class="w-4 h-4" />
                </template>
              </Button>
            </div>
          </div>

          <div v-if="expandedOrder === order.name" class="border-t border-gray-50 px-4 pb-5 pt-4 space-y-4">
            <div class="flex items-center gap-1">
              <template v-for="(step, idx) in timelineSteps(order)" :key="step.key">
                <div class="flex flex-col items-center gap-1">
                  <div :class="['w-7 h-7 rounded-full flex items-center justify-center transition-colors',
                    step.done ? (step.key === 'completed' ? 'bg-green-500' : 'bg-blue-500') : 'bg-gray-100']">
                    <component :is="step.icon"
                      :class="['w-3.5 h-3.5', step.done ? 'text-white' : 'text-gray-300']" />
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
              <div class="text-xs text-gray-500">
                Expected delivery:
                <span class="font-semibold text-gray-700">{{ order.delivery_date || 'To be confirmed' }}</span>
              </div>
            </div>

            <div v-if="order.docstatus === 0"
              class="flex items-start gap-2 bg-orange-50 border border-orange-100 rounded-xl px-3 py-2.5">
              <Clock class="w-3.5 h-3.5 text-orange-400 mt-0.5 flex-shrink-0" />
              <p class="text-xs text-orange-700">
                <span class="font-semibold">Waiting for seller to accept</span>
                — your order is pending review.
              </p>
            </div>
          </div>
        </div>
      </div>

    </template>

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

          <!-- Today's rate note -->
          <div class="flex items-center gap-2 bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-2">
            <Calendar class="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
            <p class="text-xs text-emerald-700">
              Prices reflect <span class="font-semibold">{{ todayName }}'s Daily Item Price</span> rates.
            </p>
          </div>

          <!-- Cart items -->
          <div class="space-y-2 max-h-72 overflow-y-auto pr-1">
            <div
              v-for="item in cartItemsWithDetails" :key="item.name"
              class="flex items-center gap-3 bg-gray-50 rounded-xl p-3 border border-gray-100"
            >
              <div class="w-11 h-11 rounded-lg overflow-hidden bg-white border border-gray-100 flex-shrink-0 flex items-center justify-center">
                <img v-if="item.image" :src="item.image" class="w-full h-full object-cover" />
                <Package v-else class="w-5 h-5 text-gray-200" />
              </div>

              <div class="flex-1 min-w-0">
                <p class="font-semibold text-gray-800 text-sm line-clamp-1">{{ item.item_name }}</p>
                <p class="text-xs text-gray-400">{{ item.formatted_price }} / {{ item.stock_uom }}</p>
                <div class="flex items-center gap-1 mt-1.5 bg-white rounded-lg border border-gray-200 w-fit p-0.5">
                  <Button variant="ghost" size="sm" @click="updateCart(item.name, -1)">
                    <template #icon><Minus class="w-3 h-3" /></template>
                  </Button>
                  <span class="font-bold text-sm text-blue-600 w-5 text-center">{{ item.qty }}</span>
                  <Button variant="ghost" size="sm" @click="updateCart(item.name, 1)">
                    <template #icon><Plus class="w-3 h-3" /></template>
                  </Button>
                </div>
              </div>

              <div class="flex flex-col items-end gap-2 flex-shrink-0">
                <span class="font-bold text-sm text-gray-900">{{ formatCurrency(item.subtotal) }}</span>
                <Button variant="ghost" size="sm" theme="red" @click="removeFromCart(item.name)">
                  <template #icon><Trash2 class="w-3 h-3" /></template>
                </Button>
              </div>
            </div>
          </div>

          <!-- Totals -->
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

          <div v-if="placeOrderError"
            class="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl px-4 py-3">
            {{ placeOrderError }}
          </div>
        </div>
      </template>

      <template #actions>
        <div class="flex gap-2 w-full">
          <Button variant="outline" class="flex-1" @click="checkoutOpen = false">Cancel</Button>
          <Button
            variant="solid" theme="blue" class="flex-1"
            :loading="isPlacingOrder"
            :disabled="isPlacingOrder || cartItemsWithDetails.length === 0"
            @click="handlePlaceOrder"
          >
            <template #prefix>
              <CheckCircle v-if="!isPlacingOrder" class="w-4 h-4" />
            </template>
            {{ isPlacingOrder ? 'Placing Order...' : 'Place Order' }}
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- ─── CANCEL CONFIRM ─── -->
    <Dialog
      v-model="cancelConfirmOpen"
      :options="{
        title: 'Cancel Order',
        message: `Are you sure you want to cancel order ${cancelTargetOrder}? This action cannot be undone.`,
        size: 'sm',
      }"
    >
      <template #actions>
        <div class="flex gap-2 w-full">
          <Button variant="outline" class="flex-1" @click="cancelConfirmOpen = false">Keep Order</Button>
          <Button
            variant="solid" theme="red" class="flex-1"
            :loading="cancelOrderResource.loading"
            @click="executeCancel"
          >Yes, Cancel</Button>
        </div>
      </template>
    </Dialog>

  </div>
</template>
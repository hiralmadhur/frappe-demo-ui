<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { createResource, Badge, Button } from 'frappe-ui'
import {
  ShoppingCart, ShoppingBag, RefreshCcw, Store,
  ClipboardList, Newspaper, AlertCircle, CheckCircle,
  X, Hourglass
} from 'lucide-vue-next'

import CustomerShopTab           from '@/components/Customer/CustomerShopTab.vue'
import CustomerOrdersTab         from '@/components/Customer/CustomerOrdersTab.vue'
import CustomerSubscriptionsTab  from '@/components/Customer/CustomerSubscriptionsTab.vue'
import CustomerSubscriptionModal from '@/components/Customer/CustomerSubscriptionModal.vue'
import CustomerCheckoutDialog    from '@/components/Customer/CustomerCheckoutDialog.vue'

// ─── PROPS ───
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

// ─── CART STATE ───
const cart             = ref<Record<string, number>>({})
const checkoutOpen     = ref(false)
const isPlacingOrder   = ref(false)
const placeOrderError  = ref('')
const orderPlaced      = ref(false)
const placedOrderId    = ref('')
const placedOrderTotal = ref('')
const skippedItems     = ref<string[]>([])

// ─── SUBSCRIPTION MODAL STATE ───
const subscriptionModalOpen    = ref(false)
const selectedSubscriptionItem = ref<any>(null)
const isCreatingSubscription   = ref(false)
const subscriptionError        = ref('')
const subscriptionSuccess      = ref(false)
const subscriptionSuccessMsg   = ref('')

// ─── SUBSCRIPTION STATUS MAPS ───
const activeSubsMap  = ref<Record<string, string>>({})
const pendingSubsMap = ref<Record<string, string>>({})
const scheduleMap    = ref<Record<string, Record<string, number>>>({})

// ─── TODAY ───
const todayName = computed(() => {
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
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

const activeSubsResource = createResource({
  url: 'my_frappe_app.api.get_customer_subscription_status',
  onSuccess(data: any) {
    activeSubsMap.value  = data?.active   || {}
    pendingSubsMap.value = data?.pending  || {}
    scheduleMap.value    = data?.schedule || {}
  }
})

const cancelOrderResource = createResource({
  url: 'my_frappe_app.api.cancel_order',
  onSuccess(data: any) {
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
      if (props.filters.customer)
        ordersResource.fetch({ customer: props.filters.customer })
    } else {
      placeOrderError.value = data.message || 'Something went wrong.'
    }
  },
  onError(err: any) {
    isPlacingOrder.value  = false
    placeOrderError.value = err?.message || 'Failed to place order.'
  },
})

const createSubscriptionResource = createResource({
  url: 'my_frappe_app.api.create_subscription',
  onSuccess(data: any) {
    isCreatingSubscription.value = false
    if (data.status === 'success') {
      subscriptionModalOpen.value   = false
      subscriptionSuccess.value     = true
      subscriptionSuccessMsg.value  = data.message || 'Subscription request sent!'
      subscriptionError.value       = ''
      if (props.filters.customer && props.filters.seller) {
        activeSubsResource.fetch({ customer: props.filters.customer, seller: props.filters.seller })
        ordersResource.fetch({ customer: props.filters.customer })
      }
    } else {
      subscriptionError.value = data.message || 'Failed to create subscription'
    }
  },
  onError(err: any) {
    isCreatingSubscription.value = false
    subscriptionError.value      = err?.message || 'Failed to create subscription'
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
    if (f?.customer)              ordersResource.fetch({ customer: f.customer })
    if (f?.customer && f?.seller) activeSubsResource.fetch({ customer: f.customer, seller: f.seller })
  },
  { deep: true, immediate: true }
)

watch(activeTab, (tab) => {
  if (tab === 'orders' && props.filters.customer)
    ordersResource.fetch({ customer: props.filters.customer })
})

// ─── COMPUTED ───
const allItems          = computed(() => (items.data as any[]) || [])
const subscriptionItems = computed(() => allItems.value.filter((i: any) => i.is_subscription_item))

const allOrders        = computed(() => (ordersResource.data as any)?.orders        || [])
const allSubscriptions = computed(() => (ordersResource.data as any)?.subscriptions || [])

const cartItemsWithDetails = computed(() => {
  if (!items.data) return []
  return Object.entries(cart.value)
    .map(([name, qty]) => {
      const item = allItems.value.find((i: any) => i.name === name)
      return item ? { ...item, qty, subtotal: item.price * qty } : null
    })
    .filter(Boolean)
})

const totalCartItems = computed(() =>
  Object.values(cart.value).reduce((a, b) => a + b, 0)
)

const cartTotal = computed(() =>
  cartItemsWithDetails.value.reduce((sum: number, item: any) => sum + item.subtotal, 0)
)

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val)

// ─── CART ACTIONS ───
const updateCart = (itemName: string, delta: number) => {
  const next    = (cart.value[itemName] || 0) + delta
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

// ─── PLACE ORDER ───
const handlePlaceOrder = () => {
  if (!props.filters.seller || !props.filters.customer) {
    placeOrderError.value = 'Seller or customer info missing.'
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

// ─── SUBSCRIPTION ACTIONS ───
const openSubscriptionModal = (item: any) => {
  selectedSubscriptionItem.value = item
  subscriptionError.value        = ''
  subscriptionModalOpen.value    = true
}

const handleCreateSubscription = (payload: any) => {
  if (!props.filters.customer || !props.filters.seller) {
    subscriptionError.value = 'Customer or seller information missing'
    return
  }
  subscriptionError.value      = ''
  isCreatingSubscription.value = true
  createSubscriptionResource.fetch({
    customer:       props.filters.customer,
    seller:         props.filters.seller,
    schedule_items: payload.schedule_items,
    start_date:     payload.start_date,
    months:         payload.months
  })
}

// ─── CANCEL ORDER ───
const handleCancelOrder = (orderId: string) => {
  cancelOrderResource.fetch({ order_id: orderId })
}

// ─── REFRESH ───
const refreshShop = () => {
  if (props.filters.seller && props.filters.category)
    items.fetch({ seller: props.filters.seller, category: props.filters.category })
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
        <Button v-if="activeTab === 'shop' && filters.seller && filters.category"
          variant="outline" size="sm" :loading="items.loading" @click="refreshShop">
          <template #prefix><RefreshCcw class="w-3.5 h-3.5" /></template>
        </Button>
        <Button v-if="activeTab === 'orders'" variant="outline" size="sm"
          :loading="ordersResource.loading" @click="ordersResource.reload()">
          <template #prefix><RefreshCcw class="w-3.5 h-3.5" /></template>
        </Button>
        <Button v-if="totalCartItems > 0 && activeTab === 'shop'"
          variant="solid" theme="blue" @click="checkoutOpen = true">
          <template #prefix><ShoppingBag class="w-4 h-4" /></template>
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

    <!-- ─── SHOP TAB ─── -->
    <CustomerShopTab
      v-if="activeTab === 'shop'"
      :filters="filters"
      :items="allItems"
      :loading="items.loading"
      :cart="cart"
      :active-subs-map="activeSubsMap"
      :pending-subs-map="pendingSubsMap"
      :schedule-map="scheduleMap"
      :today-name="todayName"
      :today-short="todayShort"
      @update-cart="updateCart"
      @open-subscription-modal="openSubscriptionModal"
    />

    <!-- ─── ORDERS TAB ─── -->
    <CustomerOrdersTab
      v-if="activeTab === 'orders'"
      :orders="allOrders"
      :loading="ordersResource.loading"
      :cancel-loading="cancelOrderResource.loading"
      @cancel-order="handleCancelOrder"
      @go-shop="activeTab = 'shop'"
    />

    <!-- ─── SUBSCRIPTIONS TAB ─── -->
    <CustomerSubscriptionsTab
      v-if="activeTab === 'subscriptions'"
      :subscriptions="allSubscriptions"
      :loading="ordersResource.loading"
      @go-shop="activeTab = 'shop'"
    />

    <!-- ─── SUBSCRIPTION MODAL ─── -->
    <CustomerSubscriptionModal
      v-model="subscriptionModalOpen"
      :item="selectedSubscriptionItem"
      :all-items="allItems"
      :subscription-items="subscriptionItems"
      :loading="isCreatingSubscription"
      :error="subscriptionError"
      @submit="handleCreateSubscription"
    />

    <!-- ─── CHECKOUT DIALOG ─── -->
    <CustomerCheckoutDialog
      v-model="checkoutOpen"
      :cart-items="cartItemsWithDetails"
      :cart-total="cartTotal"
      :total-cart-items="totalCartItems"
      :filters="filters"
      :loading="isPlacingOrder"
      :error="placeOrderError"
      @update-cart="updateCart"
      @remove-from-cart="removeFromCart"
      @place-order="handlePlaceOrder"
    />

  </div>
</template>
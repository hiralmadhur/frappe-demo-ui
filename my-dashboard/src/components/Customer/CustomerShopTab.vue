<script setup lang="ts">
import { computed } from 'vue'
import { Button, Badge } from 'frappe-ui'
import {
  ShoppingCart, Package, RefreshCcw, Store, Plus, Minus,
  AlertCircle, Newspaper, TrendingUp, Calendar, CheckCircle,
  Clock, Layers, Hourglass
} from 'lucide-vue-next'

const props = defineProps<{
  filters: { category?: string; seller?: string }
  items: any[]
  loading: boolean
  cart: Record<string, number>
  activeSubsMap: Record<string, string>
  pendingSubsMap: Record<string, string>
  scheduleMap: Record<string, Record<string, number>>
  todayName: string
  todayShort: string
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'update-cart', itemName: string, delta: number): void
  (e: 'open-subscription-modal', item: any): void
}>()

const ALL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_SHORT: Record<string, string> = {
  Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed',
  Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun'
}

const availableItems    = computed(() => props.items.filter((i: any) => i.price_available))
const unavailableItems  = computed(() => props.items.filter((i: any) => !i.price_available))
const subscriptionItems = computed(() => availableItems.value.filter((i: any) => i.is_subscription_item))
const regularItems      = computed(() => availableItems.value.filter((i: any) => !i.is_subscription_item))

const isActiveSubscribed = (itemCode: string) => {
  if (!props.activeSubsMap[itemCode]) return false
  const sched = props.scheduleMap[itemCode]
  return sched ? (sched[props.todayName] ?? 0) > 0 : true
}
const isPendingSubscribed = (itemCode: string) => {
  if (!props.pendingSubsMap[itemCode]) return false
  const sched = props.scheduleMap[itemCode]
  return sched ? (sched[props.todayName] ?? 0) > 0 : true
}
const isNormalOrderBlocked = (itemCode: string) => {
  if (!isActiveSubscribed(itemCode)) return false
  const sched = props.scheduleMap[itemCode]
  return sched ? (sched[props.todayName] ?? 0) > 0 : true
}
const getSubName = (itemCode: string) =>
  props.activeSubsMap[itemCode] || props.pendingSubsMap[itemCode] || ''

const hasDailyPrice = (item: any) =>
  item.price_available && item.standard_rate != null &&
  Math.abs(item.price - item.standard_rate) > 0.01
</script>

<template>
  <!-- No category selected -->
  <div v-if="!filters.category"
    class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-24 text-center">
    <Layers class="w-10 h-10 text-gray-300 mx-auto mb-3" />
    <h3 class="text-base font-bold text-gray-700">Select a Category</h3>
    <p class="text-sm text-gray-400 mt-1">Sidebar → Pincode → Category → Seller</p>
  </div>

  <!-- No seller selected -->
  <div v-else-if="!filters.seller"
    class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-24 text-center">
    <Store class="w-10 h-10 text-gray-300 mx-auto mb-3" />
    <h3 class="text-base font-bold text-gray-700">Select a Seller</h3>
    <p class="text-sm text-gray-400 mt-1">Category selected! Now pick a seller from the sidebar.</p>
  </div>

  <!-- Loading skeleton -->
  <div v-else-if="loading" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
    <div v-for="i in 8" :key="i" class="h-60 bg-gray-100 rounded-2xl animate-pulse" />
  </div>

  <!-- Items loaded -->
  <template v-else-if="items.length > 0">

    <!-- Day info banner -->
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
        <div
          v-for="item in subscriptionItems" :key="item.name"
          class="bg-gradient-to-br from-blue-50 to-white rounded-2xl border-2 border-blue-100 overflow-hidden hover:shadow-lg transition-all flex flex-col group"
        >
          <div class="aspect-square bg-white relative overflow-hidden">
            <img v-if="item.image" :src="item.image"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
            <div v-else class="w-full h-full flex items-center justify-center bg-blue-50">
              <Newspaper class="w-12 h-12 text-blue-200" />
            </div>

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
              <p class="text-[10px] text-blue-600 mt-0.5 uppercase tracking-tight font-semibold">{{ item.item_group }}</p>
              <p v-if="getSubName(item.item_code)" class="text-[10px] font-semibold mt-0.5 truncate"
                :class="isPendingSubscribed(item.item_code) ? 'text-amber-600' : 'text-green-600'">
                {{ getSubName(item.item_code) }}
              </p>

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
                @click="emit('open-subscription-modal', item)">
                <template #prefix><Calendar class="w-3 h-3" /></template>
                Subscribe
              </Button>

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
                  @click="emit('update-cart', item.name, 1)">
                  Buy Today
                </Button>
                <div v-else class="flex items-center justify-between bg-gray-50 rounded-lg p-0.5 border">
                  <Button variant="ghost" size="sm" @click="emit('update-cart', item.name, -1)">
                    <template #icon><Minus class="w-3 h-3" /></template>
                  </Button>
                  <span class="font-bold text-sm text-blue-600">{{ cart[item.name] }}</span>
                  <Button variant="ghost" size="sm" @click="emit('update-cart', item.name, 1)">
                    <template #icon><Plus class="w-3 h-3" /></template>
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
        <div
          v-for="item in regularItems" :key="item.name"
          class="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-lg transition-all flex flex-col group"
        >
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
              <div class="bg-emerald-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full flex items-center gap-0.5 shadow">
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
                @click="emit('update-cart', item.name, 1)">
                Add to Cart
              </Button>
              <div v-else class="flex items-center justify-between bg-gray-50 rounded-lg p-0.5 border">
                <Button variant="ghost" size="sm" @click="emit('update-cart', item.name, -1)">
                  <template #icon><Minus class="w-3 h-3" /></template>
                </Button>
                <span class="font-bold text-sm text-blue-600">{{ cart[item.name] }}</span>
                <Button variant="ghost" size="sm" @click="emit('update-cart', item.name, 1)">
                  <template #icon><Plus class="w-3 h-3" /></template>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Unavailable items -->
    <div v-if="unavailableItems.length > 0" class="space-y-3">
      <div class="flex items-center gap-2">
        <div class="flex-1 h-px bg-gray-100" />
        <div class="flex items-center gap-1.5 text-xs text-gray-400 font-semibold px-2">
          <AlertCircle class="w-3.5 h-3.5 text-orange-400" /> Not Available Today
        </div>
        <div class="flex-1 h-px bg-gray-100" />
      </div>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        <div
          v-for="item in unavailableItems" :key="item.name"
          class="bg-gray-50 rounded-2xl border border-gray-100 overflow-hidden flex flex-col opacity-60"
        >
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
            <p class="text-[10px] text-orange-500 font-semibold mt-1">
              {{ item.price_reason || `No price for ${todayName}` }}
            </p>
          </div>
        </div>
      </div>
    </div>

  </template>

  <!-- Empty state -->
  <div v-else-if="!loading && filters.seller && filters.category" class="text-center py-20">
    <Package class="w-10 h-10 text-gray-300 mx-auto mb-2" />
    <p class="text-gray-500 text-sm">No products found.</p>
  </div>
</template>
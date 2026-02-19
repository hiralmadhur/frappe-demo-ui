<script setup lang="ts">
import { ref, computed } from 'vue'
import { createResource, LoadingIndicator, Button } from 'frappe-ui'
import {
  Users, Search, RefreshCcw, MapPin, Newspaper,
  ShoppingBag, ChevronDown, ChevronUp, CheckCircle,
  Clock, Phone, Mail
} from 'lucide-vue-next'
import { onMounted } from 'vue'

const props = defineProps<{ seller: string }>()

// ─── STATE ───
const searchQuery      = ref('')
const expandedCustomer = ref<string | null>(null)
const selectedPincode  = ref<string>('')

// ─── RESOURCE ───
const customersData = createResource({
  url: 'my_frappe_app.api.get_seller_customers',
  onSuccess() {},
})

onMounted(() => {
  if (props.seller) customersData.fetch({ seller: props.seller })
})

// ─── COMPUTED ───
const allCustomers = computed(() => (customersData.data as any)?.customers || [])
const pincodeList  = computed(() => (customersData.data as any)?.pincodes || [])

const filteredCustomers = computed(() => {
  let list = allCustomers.value
  if (selectedPincode.value)
    list = list.filter((c: any) => c.pincode === selectedPincode.value)
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter((c: any) =>
      c.customer_name?.toLowerCase().includes(q) ||
      c.name?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.mobile?.toLowerCase().includes(q)
    )
  }
  return list
})

const totalStats = computed(() => {
  const customers = allCustomers.value
  return {
    total:         customers.length,
    withActiveSub: customers.filter((c: any) => c.active_subs > 0).length,
    totalOrders:   customers.reduce((s: number, c: any) => s + (c.total_orders || 0), 0),
    totalRevenue:  customers.reduce((s: number, c: any) => s + (c.total_revenue || 0), 0),
  }
})

// ─── HELPERS ───
const toggleExpand = (id: string) => {
  expandedCustomer.value = expandedCustomer.value === id ? null : id
}

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val)

const subStatusColor: Record<string, string> = {
  'Active':         'bg-green-100 text-green-700 border-green-200',
  'Accept Pending': 'bg-amber-100 text-amber-700 border-amber-200',
  'Expired':        'bg-gray-100 text-gray-500 border-gray-200',
  'Cancelled':      'bg-red-100 text-red-600 border-red-200',
}

const ALL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_SHORT: Record<string, string> = {
  Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed',
  Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun'
}
const DAY_QTY_FIELD: Record<string, string> = {
  Monday: 'monday_qty', Tuesday: 'tuesday_qty', Wednesday: 'wednesday_qty',
  Thursday: 'thursday_qty', Friday: 'friday_qty', Saturday: 'saturday_qty', Sunday: 'sunday_qty'
}
</script>

<template>
  <div class="space-y-4 sm:space-y-5">

    <!-- ── SUMMARY STATS ── -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3 md:gap-4">
      <div class="bg-white p-3 sm:p-4 rounded-xl sm:rounded-2xl border border-gray-100 shadow-sm">
        <p class="text-[9px] sm:text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Total Customers</p>
        <p class="text-2xl sm:text-3xl font-black text-gray-900">{{ totalStats.total }}</p>
      </div>
      <div class="bg-white p-3 sm:p-4 rounded-xl sm:rounded-2xl border border-green-100 shadow-sm">
        <p class="text-[9px] sm:text-[10px] font-bold text-green-500 uppercase tracking-widest mb-1">With Active Plan</p>
        <p class="text-2xl sm:text-3xl font-black text-gray-900">{{ totalStats.withActiveSub }}</p>
      </div>
      <div class="bg-white p-3 sm:p-4 rounded-xl sm:rounded-2xl border border-blue-100 shadow-sm">
        <p class="text-[9px] sm:text-[10px] font-bold text-blue-500 uppercase tracking-widest mb-1">Total Orders</p>
        <p class="text-2xl sm:text-3xl font-black text-gray-900">{{ totalStats.totalOrders }}</p>
      </div>
      <div class="bg-blue-600 p-3 sm:p-4 rounded-xl sm:rounded-2xl shadow-sm">
        <p class="text-[9px] sm:text-[10px] font-bold text-blue-200 uppercase tracking-widest mb-1">Total Revenue</p>
        <p class="text-xl sm:text-2xl font-black text-white">{{ formatCurrency(totalStats.totalRevenue) }}</p>
      </div>
    </div>

    <!-- ── FILTERS BAR ── -->
    <div class="flex flex-col sm:flex-row gap-2 sm:gap-3">
      <!-- Search -->
      <div class="relative flex-1">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name, email, mobile..."
          class="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm
                 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div class="flex gap-2 sm:gap-3">
        <!-- Pincode filter -->
        <select
          v-model="selectedPincode"
          class="flex-1 sm:flex-none border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                 focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
        >
          <option value="">All Pincodes</option>
          <option v-for="pin in pincodeList" :key="pin" :value="pin">{{ pin }}</option>
        </select>

        <!-- Refresh -->
        <Button
          variant="outline"
          :loading="customersData.loading"
          class="text-xs sm:text-sm flex-shrink-0"
          @click="customersData.fetch({ seller: props.seller })"
        >
          <template #prefix><RefreshCcw class="w-3.5 h-3.5 sm:w-4 sm:h-4" /></template>
          <span class="hidden sm:inline">Refresh</span>
        </Button>
      </div>
    </div>

    <!-- ── LOADING ── -->
    <div v-if="customersData.loading" class="flex justify-center py-16 sm:py-20">
      <LoadingIndicator class="w-7 h-7 sm:w-8 sm:h-8 text-blue-600" />
    </div>

    <!-- ── EMPTY ── -->
    <div
      v-else-if="filteredCustomers.length === 0"
      class="bg-gray-50 rounded-2xl sm:rounded-3xl border-2 border-dashed border-gray-200 py-16 sm:py-24 text-center px-4"
    >
      <Users class="w-9 h-9 sm:w-10 sm:h-10 text-gray-300 mx-auto mb-3" />
      <h3 class="text-sm sm:text-base font-bold text-gray-700">No Customers Found</h3>
      <p class="text-xs sm:text-sm text-gray-400 mt-1">
        {{ searchQuery || selectedPincode ? 'Try different filters' : 'No customers in your area yet' }}
      </p>
    </div>

    <!-- ── CUSTOMER LIST ── -->
    <div v-else class="space-y-2 sm:space-y-3">
      <div
        v-for="customer in filteredCustomers"
        :key="customer.name"
        class="bg-white rounded-xl sm:rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
      >
        <!-- Customer row header -->
        <div
          class="flex items-center justify-between p-3 sm:p-4 gap-2 sm:gap-3 cursor-pointer"
          @click="toggleExpand(customer.name)"
        >
          <!-- Left: Avatar + info -->
          <div class="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
            <div
              class="h-9 w-9 sm:h-11 sm:w-11 rounded-lg sm:rounded-xl bg-gradient-to-br from-blue-500 to-blue-700
                     text-white flex items-center justify-center font-black text-base sm:text-lg flex-shrink-0 shadow-sm"
            >
              {{ customer.customer_name?.[0]?.toUpperCase() || '?' }}
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                <span class="font-bold text-gray-900 text-xs sm:text-sm">{{ customer.customer_name }}</span>
                <span class="font-mono text-[9px] sm:text-[10px] text-gray-400 hidden xs:inline">{{ customer.name }}</span>

                <span
                  v-if="customer.active_subs > 0"
                  class="inline-flex items-center gap-1 bg-green-100 text-green-700 text-[8px] sm:text-[9px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full border border-green-200"
                >
                  <CheckCircle class="w-2 h-2 sm:w-2.5 sm:h-2.5" />
                  {{ customer.active_subs }} Active
                </span>
                <span
                  v-else-if="customer.pending_subs > 0"
                  class="inline-flex items-center gap-1 bg-amber-100 text-amber-700 text-[8px] sm:text-[9px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full border border-amber-200"
                >
                  <Clock class="w-2 h-2 sm:w-2.5 sm:h-2.5" />
                  {{ customer.pending_subs }} Pending
                </span>
              </div>

              <div class="flex items-center gap-2 sm:gap-3 mt-0.5 flex-wrap">
                <span v-if="customer.email" class="flex items-center gap-1 text-[9px] sm:text-[10px] text-gray-400">
                  <Mail class="w-3 h-3 flex-shrink-0" />
                  <span class="truncate max-w-[110px] sm:max-w-none">{{ customer.email }}</span>
                </span>
                <span v-if="customer.mobile" class="flex items-center gap-1 text-[9px] sm:text-[10px] text-gray-400">
                  <Phone class="w-3 h-3 flex-shrink-0" /> {{ customer.mobile }}
                </span>
                <span v-if="customer.pincode" class="flex items-center gap-1 text-[9px] sm:text-[10px] text-gray-400">
                  <MapPin class="w-3 h-3 flex-shrink-0" /> {{ customer.pincode }}
                </span>
              </div>
            </div>
          </div>

          <!-- Right: stats + expand -->
          <div class="flex items-center gap-3 sm:gap-4 flex-shrink-0">
            <div class="text-right hidden md:block">
              <p class="text-xs text-gray-400 font-medium">Orders</p>
              <p class="font-black text-gray-900">{{ customer.total_orders || 0 }}</p>
            </div>
            <div class="text-right hidden md:block">
              <p class="text-xs text-gray-400 font-medium">Revenue</p>
              <p class="font-black text-gray-900 text-sm">{{ formatCurrency(customer.total_revenue || 0) }}</p>
            </div>
            <ChevronUp v-if="expandedCustomer === customer.name" class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 flex-shrink-0" />
            <ChevronDown v-else class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 flex-shrink-0" />
          </div>
        </div>

        <!-- Expanded: subscriptions + recent orders -->
        <div
          v-if="expandedCustomer === customer.name"
          class="border-t border-gray-100 px-3 sm:px-4 pb-4 sm:pb-5 pt-3 sm:pt-4 space-y-3 sm:space-y-4 bg-gray-50/30"
        >
          <!-- Mobile stats -->
          <div class="flex gap-3 md:hidden">
            <div class="bg-white rounded-lg sm:rounded-xl p-2.5 sm:p-3 border border-gray-100 flex-1 text-center">
              <p class="text-[9px] sm:text-[10px] text-gray-400">Orders</p>
              <p class="font-black text-gray-900 text-sm sm:text-base">{{ customer.total_orders || 0 }}</p>
            </div>
            <div class="bg-white rounded-lg sm:rounded-xl p-2.5 sm:p-3 border border-gray-100 flex-1 text-center">
              <p class="text-[9px] sm:text-[10px] text-gray-400">Revenue</p>
              <p class="font-black text-gray-900 text-xs sm:text-sm">{{ formatCurrency(customer.total_revenue || 0) }}</p>
            </div>
          </div>

          <!-- Subscriptions -->
          <div v-if="customer.subscriptions?.length > 0">
            <h4 class="text-[10px] sm:text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <Newspaper class="w-3 h-3 sm:w-3.5 sm:h-3.5" /> Subscription Plans
            </h4>
            <div class="space-y-2">
              <div
                v-for="sub in customer.subscriptions"
                :key="sub.name"
                class="bg-white rounded-lg sm:rounded-xl border border-gray-100 p-2.5 sm:p-3"
              >
                <div class="flex flex-col xs:flex-row xs:items-center justify-between gap-1 mb-2">
                  <div class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                    <span class="font-mono text-[10px] sm:text-xs font-bold text-gray-700">{{ sub.name }}</span>
                    <span :class="['text-[8px] sm:text-[9px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full border',
                      subStatusColor[sub.status] || 'bg-gray-100 text-gray-500 border-gray-200']">
                      {{ sub.status }}
                    </span>
                  </div>
                  <span class="text-[9px] sm:text-[10px] text-gray-400 whitespace-nowrap">
                    {{ sub.formatted_start }} → {{ sub.formatted_end }}
                  </span>
                </div>

                <div v-for="si in sub.schedule_items" :key="si.item_code" class="mt-2">
                  <p class="text-[9px] sm:text-[10px] text-gray-500 font-semibold mb-1">{{ si.item_name }}</p>
                  <div class="flex gap-1 flex-wrap">
                    <template v-for="day in ALL_DAYS" :key="day">
                      <div :class="[
                        'flex flex-col items-center px-1.5 sm:px-2 py-1 rounded-lg text-[8px] sm:text-[9px] font-bold min-w-[28px] sm:min-w-[32px] text-center',
                        (si[DAY_QTY_FIELD[day]] || 0) > 0 ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'
                      ]">
                        <span>{{ DAY_SHORT[day] }}</span>
                        <span v-if="(si[DAY_QTY_FIELD[day]] || 0) > 0" class="opacity-80 text-[7px] sm:text-[8px]">
                          ×{{ si[DAY_QTY_FIELD[day]] }}
                        </span>
                      </div>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div
            v-else
            class="text-center py-3 sm:py-4 text-[10px] sm:text-xs text-gray-400 bg-white rounded-lg sm:rounded-xl border border-dashed border-gray-200"
          >
            <Newspaper class="w-5 h-5 sm:w-6 sm:h-6 text-gray-200 mx-auto mb-1" />
            No subscription plans yet
          </div>

          <!-- Recent orders -->
          <div v-if="customer.recent_orders?.length > 0">
            <h4 class="text-[10px] sm:text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <ShoppingBag class="w-3 h-3 sm:w-3.5 sm:h-3.5" /> Recent Orders (last 5)
            </h4>
            <div class="bg-white rounded-lg sm:rounded-xl border border-gray-100 overflow-hidden">
              <!-- Scrollable on mobile -->
              <div class="overflow-x-auto">
                <table class="w-full text-xs min-w-[360px]">
                  <thead class="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th class="px-2.5 sm:px-3 py-2 text-left font-bold text-gray-500 uppercase text-[9px] sm:text-xs">Order</th>
                      <th class="px-2.5 sm:px-3 py-2 text-left font-bold text-gray-500 uppercase text-[9px] sm:text-xs">Date</th>
                      <th class="px-2.5 sm:px-3 py-2 text-left font-bold text-gray-500 uppercase text-[9px] sm:text-xs">Status</th>
                      <th class="px-2.5 sm:px-3 py-2 text-right font-bold text-gray-500 uppercase text-[9px] sm:text-xs">Amount</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-50">
                    <tr v-for="order in customer.recent_orders" :key="order.name">
                      <td class="px-2.5 sm:px-3 py-2 font-mono font-bold text-gray-700 text-[10px] sm:text-xs">
                        {{ order.name }}
                        <span
                          v-if="order.custom_subscription_refereance"
                          class="ml-1 text-[8px] bg-blue-100 text-blue-600 px-1 py-0.5 rounded font-bold"
                        >SUB</span>
                      </td>
                      <td class="px-2.5 sm:px-3 py-2 text-gray-500 text-[10px] sm:text-xs">{{ order.transaction_date }}</td>
                      <td class="px-2.5 sm:px-3 py-2">
                        <span :class="[
                          'text-[8px] sm:text-[9px] font-bold px-1.5 py-0.5 rounded-full',
                          order.docstatus === 2 ? 'bg-red-100 text-red-600'
                            : order.status === 'Completed' ? 'bg-green-100 text-green-700'
                            : 'bg-blue-100 text-blue-700'
                        ]">{{ order.status }}</span>
                      </td>
                      <td class="px-2.5 sm:px-3 py-2 text-right font-bold text-gray-800 text-[10px] sm:text-xs tabular-nums">
                        {{ formatCurrency(order.grand_total) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

  </div>
</template>
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Button, Dialog, createResource } from 'frappe-ui'
import { Receipt, Calendar, ChevronRight, AlertCircle, Filter, X, User, Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: boolean
  eligibleOrders: any[]
  seller: string
  formatCurrency: (amount: number, currency?: string) => string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'invoice-created', invoiceName: string): void
}>()

const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const ALL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_SHORT: Record<string, string> = {
  Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed',
  Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun'
}

const today            = new Date().toISOString().split('T')[0]
const fromDate         = ref('')
const toDate           = ref(today)
const selectedOrders   = ref<Set<string>>(new Set())
const errorMsg         = ref('')
const selectedCustomer = ref('')
const orderItemsCache  = ref<Record<string, any[]>>({})
const fetchingItems    = ref(false)
const fetchError       = ref('')

const soItemsResource = createResource({
  url: 'my_frappe_app.api.get_sales_order_items',
  onError(err: any) {
    console.error('[InvoiceDialog] soItemsResource error:', err)
  },
})

const customerOptions = computed(() => {
  const map = new Map<string, string>()
  props.eligibleOrders.forEach((o: any) => {
    const id   = o.customer   || o.customer_name
    const name = o.customer_name || o.customer
    if (id && name) map.set(id, name)
  })
  return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
})

const filteredOrders = computed(() =>
  props.eligibleOrders.filter((o: any) => {
    const d = o.transaction_date
    if (fromDate.value && d < fromDate.value) return false
    if (toDate.value   && d > toDate.value)   return false
    if (selectedCustomer.value) {
      const match = o.customer === selectedCustomer.value || o.customer_name === selectedCustomer.value
      if (!match) return false
    }
    return true
  })
)

// Sirf dialog open hone par (initial) sab select karo
// Filter change karne par orders manually toggle karo
let initialLoad = true
watch(filteredOrders, (rows) => {
  if (initialLoad) {
    selectedOrders.value = new Set(rows.map((o: any) => o.name))
    initialLoad = false
  }
}, { immediate: true })

// Clear filters function — sab unselect rehein
const clearFilters = () => {
  fromDate.value = ''
  toDate.value = today
  selectedCustomer.value = ''
  selectedOrders.value = new Set()   // unselect all
  errorMsg.value = ''
}

const hasActiveFilters = computed(() =>
  !!fromDate.value || !!selectedCustomer.value || toDate.value !== today
)

const allSelected = computed(() =>
  filteredOrders.value.length > 0 &&
  filteredOrders.value.every((o: any) => selectedOrders.value.has(o.name))
)
const someSelected = computed(() =>
  filteredOrders.value.some((o: any) => selectedOrders.value.has(o.name)) && !allSelected.value
)

const toggleAll = () => {
  const s = new Set(selectedOrders.value)
  allSelected.value
    ? filteredOrders.value.forEach((o: any) => s.delete(o.name))
    : filteredOrders.value.forEach((o: any) => s.add(o.name))
  selectedOrders.value = s
}

const toggleOrder = (name: string) => {
  const s = new Set(selectedOrders.value)
  s.has(name) ? s.delete(name) : s.add(name)
  selectedOrders.value = s
  errorMsg.value = ''
}

const selectedOrdersList = computed(() =>
  props.eligibleOrders.filter((o: any) => selectedOrders.value.has(o.name))
)
const totalAmount = computed(() =>
  selectedOrdersList.value.reduce((sum: number, o: any) => sum + (o.grand_total || 0), 0)
)

async function fetchItemsForOrders(orderNames: string[]) {
  const toFetch = orderNames.filter(n => !orderItemsCache.value[n])
  if (!toFetch.length) return

  fetchingItems.value = true
  fetchError.value    = ''

  try {
    const rows: any[] = await soItemsResource.submit({
      order_names: JSON.stringify(toFetch),
    })

    if (!Array.isArray(rows)) {
      throw new Error(`Unexpected response format. Got: ${JSON.stringify(rows)}`)
    }

    const grouped: Record<string, any[]> = {}
    for (const row of rows) {
      if (!grouped[row.parent]) grouped[row.parent] = []
      grouped[row.parent].push(row)
    }

    for (const name of toFetch) {
      orderItemsCache.value[name] = grouped[name] || []
    }

  } catch (e: any) {
    const msg = e?.message || e?.exception || e?.exc_type || String(e)
    fetchError.value = msg
    for (const name of toFetch) {
      if (!orderItemsCache.value[name]) orderItemsCache.value[name] = []
    }
  } finally {
    fetchingItems.value = false
  }
}

watch(selectedOrders, async (s) => {
  if (s.size > 0) await fetchItemsForOrders([...s])
}, { deep: true })

const itemDaySummary = computed(() => {
  const map = new Map<string, {
    item_name: string
    days: Record<string, { qty: number; price: number }>
    total_qty: number
    total_amt: number
  }>()

  for (const order of selectedOrdersList.value) {
    const date = order.transaction_date
    if (!date) continue

    const dayName = new Date(date + 'T00:00:00')
      .toLocaleDateString('en-US', { weekday: 'long' })

    const orderItems: any[] = orderItemsCache.value[order.name] || []

    for (const item of orderItems) {
      const code = item.item_code
      if (!code) continue

      if (!map.has(code)) {
        map.set(code, { item_name: item.item_name || code, days: {}, total_qty: 0, total_amt: 0 })
      }
      const entry = map.get(code)!
      const qty   = Number(item.qty)  || 0
      const price = Number(item.rate) || 0

      if (!entry.days[dayName]) entry.days[dayName] = { qty: 0, price: 0 }
      entry.days[dayName].qty += qty
      if (price > 0 && entry.days[dayName].price === 0) entry.days[dayName].price = price
      entry.total_qty += qty
      entry.total_amt += qty * price
    }
  }

  return Array.from(map.entries()).map(([item_code, v]) => ({ item_code, ...v }))
})

function fmtCell(qty: number, price: number): string {
  const q = String(qty).padStart(3, '0')
  const p = Number.isInteger(price) ? String(price) : price.toFixed(2)
  return `${q}(${p})`
}

const invoiceResource = createResource({
  url: 'my_frappe_app.api.create_invoice_from_sales_orders',
  onSuccess(data: any) {
    errorMsg.value = ''
    open.value = false
    emit('invoice-created', data.invoice_name)
    resetDialog()
  },
  onError(err: any) {
    const raw = (err?.exception || err?.message || '').toLowerCase()
    if (raw.includes('already been billed') || raw.includes('billed amount'))
      errorMsg.value = 'This order has already been billed. Please select a different order.'
    else if (raw.includes('not submitted') || raw.includes('draft'))
      errorMsg.value = 'Order has not been submitted yet. Please submit the order first.'
    else if (raw.includes('permission') || raw.includes('not permitted'))
      errorMsg.value = 'You do not have permission to create this invoice.'
    else if (raw.includes('no orders') || raw.includes('select at least'))
      errorMsg.value = 'Please select at least one order.'
    else if (raw.includes('delivery') && raw.includes('not'))
      errorMsg.value = 'Delivery has not been completed yet. Please confirm delivery first.'
    else if (raw.includes('customer') && raw.includes('match'))
      errorMsg.value = 'All selected orders must belong to the same customer.'
    else if (raw.includes('internal server error') || raw.includes('operationalerror') || raw.includes('traceback'))
      errorMsg.value = 'A server error occurred. Please try again later or contact the admin.'
    else {
      const cleaned = (err?.exception || err?.message || '')
        .replace(/<[^>]+>/g, '').replace(/^[\w.]+Error:\s*/i, '').replace(/Traceback[\s\S]*/i, '').trim()
      errorMsg.value = cleaned || 'An error occurred while creating the invoice. Please try again.'
    }
  },
})

const creating = computed(() => invoiceResource.loading)

const createInvoice = () => {
  if (selectedOrders.value.size === 0) return
  errorMsg.value = ''
  invoiceResource.submit({ sales_orders: [...selectedOrders.value] })
}

const resetDialog = () => {
  fromDate.value         = ''
  toDate.value           = today
  selectedOrders.value   = new Set()
  errorMsg.value         = ''
  selectedCustomer.value = ''
  orderItemsCache.value  = {}
  fetchError.value       = ''
  initialLoad            = true   // next open will auto-select all again
}

watch(open, (v) => { if (!v) resetDialog() })
</script>

<template>
  <Dialog v-model="open" :options="{ size: '5xl' }">
    <template #body-title>
      <div class="flex items-center gap-2 sm:gap-3">
        <div class="p-2 sm:p-2.5 bg-emerald-600 rounded-lg sm:rounded-xl text-white shadow-md flex-shrink-0">
          <Receipt class="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
        <div>
          <h3 class="text-base sm:text-xl font-black leading-none text-gray-900">Create Invoice</h3>
          <p class="text-[10px] sm:text-sm text-gray-400 font-medium mt-0.5">
            Select delivered orders to generate a combined invoice
          </p>
        </div>
      </div>
    </template>

    <template #body-content>
      <div class="space-y-3">

        <!-- ══ ERROR BANNERS ══ -->
        <div v-if="errorMsg"
          class="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3 shadow-sm"
        >
          <div class="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <AlertCircle class="w-4 h-4 text-red-500" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm text-red-800 font-bold">Invoice Could Not Be Created</p>
            <p class="text-xs text-red-600 mt-0.5 leading-relaxed">{{ errorMsg }}</p>
          </div>
          <button @click="errorMsg = ''" class="text-red-300 hover:text-red-500 transition-colors mt-0.5">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div v-if="fetchError"
          class="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 shadow-sm"
        >
          <div class="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <AlertCircle class="w-4 h-4 text-amber-500" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs text-amber-800 font-bold">Could not load item details</p>
            <p class="text-[10px] text-amber-600 mt-0.5 font-mono break-all">{{ fetchError }}</p>
          </div>
          <button @click="fetchError = ''" class="text-amber-300 hover:text-amber-500 transition-colors">
            <X class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- ══ FILTERS ══ -->
        <div class="filter-card">
          <div class="filter-header">
            <div class="filter-title-group">
              <div class="filter-icon-wrap">
                <Filter class="w-3.5 h-3.5 text-indigo-600" />
              </div>
              <span class="filter-title">Filters</span>
              <span v-if="hasActiveFilters" class="filter-active-badge">
                {{ (fromDate ? 1 : 0) + (selectedCustomer ? 1 : 0) + (toDate !== today ? 1 : 0) }} active
              </span>
            </div>
            <button
              @click="clearFilters"
              :disabled="!hasActiveFilters"
              :class="['clear-btn', hasActiveFilters ? 'clear-btn-active' : 'clear-btn-disabled']"
            >
              <X class="w-3 h-3" />
              <span>Clear Filters</span>
            </button>
          </div>

          <!-- Filter inputs -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3 mt-3">
            <!-- From Date -->
            <div class="filter-field">
              <label class="filter-label">From Date</label>
              <div class="filter-input-wrap" :class="fromDate ? 'input-active' : ''">
                <Calendar class="filter-input-icon" />
                <input type="date" v-model="fromDate" :max="toDate || today" class="filter-input" />
                <button v-if="fromDate" @click.stop="fromDate = ''" class="input-clear-btn">
                  <X class="w-3 h-3" />
                </button>
              </div>
            </div>
            <!-- To Date -->
            <div class="filter-field">
              <label class="filter-label">To Date</label>
              <div class="filter-input-wrap" :class="toDate !== today ? 'input-active' : ''">
                <Calendar class="filter-input-icon" />
                <input type="date" v-model="toDate" :min="fromDate" :max="today" class="filter-input" />
                <button v-if="toDate !== today" @click.stop="toDate = today" class="input-clear-btn">
                  <X class="w-3 h-3" />
                </button>
              </div>
            </div>
            <!-- Customer -->
            <div class="filter-field">
              <label class="filter-label">Customer</label>
              <div class="filter-input-wrap" :class="selectedCustomer ? 'input-active' : ''">
                <User class="filter-input-icon" style="z-index:2" />
                <select v-model="selectedCustomer" class="filter-input filter-select">
                  <option value="">All Customers ({{ customerOptions.length }})</option>
                  <option v-for="c in customerOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
                </select>
                <svg class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/>
                </svg>
              </div>
            </div>
          </div>

          <!-- Active filter pills + result count -->
          <div class="filter-pills-row">
            <div class="pill pill-date">
              <span class="pill-dot" :class="hasActiveFilters ? 'pill-dot-active' : 'pill-dot-idle'"></span>
              <span class="pill-text">{{ fromDate || 'Any' }}</span>
              <ChevronRight class="w-3 h-3 opacity-40" />
              <span class="pill-text">{{ toDate || today }}</span>
            </div>
            <div v-if="selectedCustomer" class="pill pill-customer">
              <User class="w-2.5 h-2.5" />
              <span class="pill-text truncate max-w-[110px]">{{ customerOptions.find(c => c.value === selectedCustomer)?.label }}</span>
              <button @click="selectedCustomer = ''; selectedOrders = new Set()" class="pill-remove"><X class="w-2.5 h-2.5" /></button>
            </div>
            <div class="pill pill-count ml-auto">
              <span class="pill-count-num">{{ filteredOrders.length }}</span>
              <span class="pill-count-label">orders found</span>
            </div>
          </div>
        </div>

        <!-- ══ DAY-WISE ITEM SUMMARY ══ -->
        <div class="summary-table-wrapper border border-gray-200 rounded-2xl overflow-hidden shadow-sm">

          <!-- Fixed Header Bar -->
          <div class="flex items-center gap-3 px-4 py-3.5 bg-gradient-to-r from-emerald-700 to-emerald-600 flex-shrink-0">
            <div class="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0 shadow-inner">
              <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-black text-white leading-tight tracking-tight">Day-wise Item Summary</p>
              <p class="text-[11px] text-emerald-200 mt-0.5 font-semibold">qty(₹rate) — e.g. 002(35)</p>
            </div>
            <Loader2 v-if="fetchingItems" class="w-4 h-4 text-white/80 animate-spin flex-shrink-0" />
            <div v-else class="flex items-center gap-1.5 bg-white/20 border border-white/20 rounded-full px-3 py-1 flex-shrink-0">
              <span class="text-[11px] font-black text-white">{{ itemDaySummary.length }}</span>
              <span class="text-[11px] text-emerald-200 font-semibold">items</span>
            </div>
          </div>

          <!-- Loading state -->
          <div v-if="fetchingItems && itemDaySummary.length === 0"
               class="flex flex-col items-center justify-center gap-2 py-10 bg-white">
            <div class="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
              <Loader2 class="w-5 h-5 text-emerald-500 animate-spin" />
            </div>
            <p class="text-xs font-semibold text-gray-400">Fetching item details...</p>
          </div>

          <!-- Empty: no orders selected -->
          <div v-else-if="selectedOrders.size === 0"
               class="flex flex-col items-center justify-center gap-2 py-8 bg-white">
            <div class="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <p class="text-xs font-semibold text-gray-400">Select orders below to see item summary</p>
          </div>

          <!-- No items found -->
          <div v-else-if="!fetchingItems && itemDaySummary.length === 0"
               class="flex flex-col items-center justify-center gap-2 py-8 bg-white">
            <div class="w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center">
              <AlertCircle class="w-5 h-5 text-amber-400" />
            </div>
            <p class="text-xs font-semibold text-gray-400">No item data found for selected orders</p>
            <p class="text-[10px] text-gray-300">Check browser console (F12) for details</p>
          </div>

          <!-- ── THE TABLE ── -->
          <div v-else class="summary-scroll-area">
            <table class="summary-table">
              <!-- ── THEAD: sticky top ── -->
              <thead>
                <tr>
                  <th class="col-item th-item">
                    <span class="th-label">Item</span>
                  </th>
                  <th v-for="day in ALL_DAYS" :key="day"
                      :class="['col-day th-day', (day==='Saturday'||day==='Sunday') ? 'th-weekend' : '']">
                    {{ DAY_SHORT[day] }}
                  </th>
                  <th class="col-total th-total">
                    <span class="th-label">Total</span>
                  </th>
                </tr>
              </thead>

              <!-- ── TBODY ── -->
              <tbody>
                <tr v-for="(row, idx) in itemDaySummary" :key="row.item_code"
                    :class="['data-row', idx % 2 === 1 ? 'row-alt' : 'row-base']">

                  <td :class="['col-item td-item', idx % 2 === 1 ? 'td-item-alt' : 'td-item-base']">
                    <div class="item-name" :title="row.item_name">{{ row.item_name }}</div>
                    <div class="item-code" :title="row.item_code">{{ row.item_code }}</div>
                  </td>

                  <td v-for="day in ALL_DAYS" :key="day"
                      :class="['col-day td-day', (day==='Saturday'||day==='Sunday') ? 'td-weekend' : '']">
                    <span v-if="row.days[day] && row.days[day].qty > 0" class="cell-value">
                      {{ fmtCell(row.days[day].qty, row.days[day].price) }}
                    </span>
                    <span v-else class="cell-empty">·</span>
                  </td>

                  <td class="col-total td-total-cell">
                    <div class="total-amt">{{ formatCurrency(row.total_amt) }}</div>
                    <div class="total-qty">qty: {{ row.total_qty }}</div>
                  </td>
                </tr>
              </tbody>

              <!-- ── TFOOT: sticky bottom ── -->
              <tfoot>
                <tr class="footer-row">
                  <td class="col-item td-foot-label">Grand Total</td>
                  <td v-for="day in ALL_DAYS" :key="day"
                      :class="['col-day td-foot-day', (day==='Saturday'||day==='Sunday') ? 'td-foot-weekend' : '']">
                  </td>
                  <td class="col-total td-foot-amount">
                    {{ formatCurrency(totalAmount) }}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <!-- ══ ORDERS TABLE ══ -->
        <div class="border border-gray-200 rounded-2xl overflow-hidden shadow-sm">

          <div class="flex items-center gap-2.5 px-4 py-3 bg-gradient-to-r from-gray-700 to-gray-600">
            <div class="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center flex-shrink-0">
              <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div class="flex-1">
              <p class="text-sm font-black text-white leading-none">Select Orders</p>
              <p class="text-[10px] text-gray-300 mt-0.5">Click to select/deselect orders for invoicing</p>
            </div>
            <button @click="toggleAll"
              class="flex items-center gap-1.5 bg-white/15 hover:bg-white/25 transition-colors rounded-lg px-2.5 py-1.5 flex-shrink-0">
              <div :class="['checkbox-circle-sm', allSelected ? 'checkbox-sm-selected' : someSelected ? 'checkbox-sm-indeterminate' : 'checkbox-sm-unselected']">
                <svg v-if="allSelected" class="w-2.5 h-2.5 text-white" viewBox="0 0 12 12" fill="none">
                  <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <div v-else-if="someSelected" class="w-2 h-0.5 bg-white rounded-full"></div>
              </div>
              <span class="text-[10px] font-bold text-white whitespace-nowrap">
                {{ allSelected ? 'Deselect All' : 'Select All' }}
              </span>
            </button>
          </div>

          <!-- Desktop Column Headers -->
          <div class="hidden sm:grid items-center gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-100"
               style="grid-template-columns: 24px 24px 1fr 1fr 72px 72px 90px">
            <span></span>
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest">#</span>
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Sales Order</span>
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Delivery Note</span>
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest text-right">Delivered</span>
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest text-right">Billed</span>
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest text-right">Amount</span>
          </div>

          <div v-if="filteredOrders.length === 0"
               class="flex flex-col items-center justify-center py-10 text-center bg-white px-4">
            <div class="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center mb-3">
              <AlertCircle class="w-6 h-6 text-gray-300" />
            </div>
            <p class="text-sm font-bold text-gray-400">No eligible orders found</p>
            <p class="text-xs text-gray-300 mt-1">Try adjusting the date range or customer filter</p>
          </div>

          <div v-else class="divide-y divide-gray-50 max-h-52 overflow-y-auto bg-white orders-scroll">
            <div
              v-for="(order, idx) in filteredOrders" :key="order.name"
              @click="toggleOrder(order.name)"
              :class="['order-row cursor-pointer select-none transition-all duration-100',
                       selectedOrders.has(order.name) ? 'order-row-selected' : 'order-row-unselected']"
            >
              <!-- Desktop Row -->
              <div class="hidden sm:grid items-center gap-2 px-4 py-3"
                   style="grid-template-columns: 24px 24px 1fr 1fr 72px 72px 90px">
                <div :class="['checkbox-circle', selectedOrders.has(order.name) ? 'checkbox-selected' : 'checkbox-unselected']">
                  <svg v-if="selectedOrders.has(order.name)" class="w-3 h-3 text-white check-icon" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <span class="text-[10px] text-gray-400 font-mono font-bold">{{ idx + 1 }}</span>
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="font-bold font-mono text-[11px] text-gray-800 truncate">{{ order.name }}</span>
                    <span v-if="order.custom_subscription_refereance"
                      class="text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded-full font-bold">Sub</span>
                  </div>
                  <p class="text-[10px] text-gray-400 mt-0.5 truncate">{{ order.customer_name }}</p>
                </div>
                <div class="min-w-0">
                  <span class="font-mono text-[10px] text-gray-500 truncate block">{{ order.delivery_note || '—' }}</span>
                </div>
                <div class="text-right">
                  <span class="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded-lg border border-emerald-100">
                    {{ order.per_delivered }}%
                  </span>
                </div>
                <div class="text-right">
                  <span class="text-[10px] font-bold text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded-lg border border-orange-100">
                    {{ order.per_billed }}%
                  </span>
                </div>
                <span class="font-black text-gray-800 font-mono text-xs text-right tabular-nums block">
                  {{ formatCurrency(order.grand_total, order.currency) }}
                </span>
              </div>

              <!-- Mobile Row -->
              <div class="flex sm:hidden items-center gap-3 px-4 py-3">
                <div :class="['checkbox-circle', selectedOrders.has(order.name) ? 'checkbox-selected' : 'checkbox-unselected']">
                  <svg v-if="selectedOrders.has(order.name)" class="w-3 h-3 text-white check-icon" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-1">
                    <span class="font-bold font-mono text-[10px] text-gray-800 truncate">{{ order.name }}</span>
                    <span v-if="order.custom_subscription_refereance"
                      class="text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded-full font-bold flex-shrink-0">Sub</span>
                  </div>
                  <div class="flex items-center gap-2 mt-0.5">
                    <p class="text-[9px] text-gray-400 truncate flex-1">{{ order.customer_name }}</p>
                    <span class="text-[9px] font-bold text-emerald-700 bg-emerald-50 px-1 py-0.5 rounded flex-shrink-0">{{ order.per_delivered }}%</span>
                  </div>
                </div>
                <span class="font-black text-gray-800 font-mono text-[11px] text-right tabular-nums flex-shrink-0">
                  {{ formatCurrency(order.grand_total, order.currency) }}
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </template>

    <!-- Footer -->
    <template #actions>
      <div class="flex flex-col xs:flex-row items-start xs:items-center w-full gap-3">
        <div class="flex items-center gap-2 sm:gap-3 min-w-0">
          <template v-if="selectedOrders.size > 0">
            <span class="text-[10px] sm:text-xs text-gray-500 font-semibold whitespace-nowrap">
              {{ selectedOrders.size }} orders
            </span>
            <div class="h-4 w-px bg-gray-200 flex-shrink-0"></div>
            <span class="font-black text-gray-900 text-sm sm:text-base">{{ formatCurrency(totalAmount) }}</span>
          </template>
        </div>
        <div class="flex items-center gap-2 sm:gap-3 ml-auto flex-shrink-0">
          <Button variant="outline" class="text-xs sm:text-sm" @click="open = false">Cancel</Button>
          <Button
            variant="solid" theme="green"
            :loading="creating"
            :disabled="selectedOrders.size === 0"
            class="text-xs sm:text-sm"
            @click="createInvoice"
          >
            <template #prefix><Receipt class="w-3.5 h-3.5 sm:w-4 sm:h-4" /></template>
            Create Invoice
          </Button>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
/* ══════════════════════════════════════════════
   SUMMARY TABLE — Full Responsive with
   Sticky Header, Sticky Footer, Sticky Columns
   ══════════════════════════════════════════════ */

/* Outer wrapper: flex-column so header/footer stay fixed */
.summary-table-wrapper {
  display: flex;
  flex-direction: column;
  /* no fixed height here — table decides */
}

/* Scroll area: only the tbody scrolls */
.summary-scroll-area {
  overflow: auto;
  max-height: 260px;           /* adjust as needed */
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: #d1d5db transparent;
  /* Important: relative context for sticky inside */
  position: relative;
}
.summary-scroll-area::-webkit-scrollbar { width: 4px; height: 4px; }
.summary-scroll-area::-webkit-scrollbar-track { background: transparent; }
.summary-scroll-area::-webkit-scrollbar-thumb { background: #e5e7eb; border-radius: 99px; }
.summary-scroll-area::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

/* Table itself */
.summary-table {
  width: 100%;
  border-collapse: separate;   /* MUST be separate for sticky borders to work */
  border-spacing: 0;
  table-layout: fixed;         /* prevents column blow-out */
  /* min-width keeps table from collapsing on narrow screens */
  min-width: 560px;
}

/* ── Column widths ── */
.col-item  { width: 160px; min-width: 140px; max-width: 180px; }
.col-day   { width: 82px;  min-width: 74px; }
.col-total { width: 110px; min-width: 96px; }

/* ══ THEAD ══ */
thead tr {
  position: sticky;
  top: 0;
  z-index: 30;
}

/* ══ THEAD ══ */
.th-item,
.th-day,
.th-total {
  padding: 11px 10px;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  white-space: nowrap;
  border-bottom: 2px solid #d1d5db;
  background: #f3f4f6;
}

.th-item {
  text-align: left;
  padding-left: 14px;
  color: #374151;
  border-right: 2px solid #d1d5db;
  position: sticky;
  left: 0;
  z-index: 40;
  background: #f3f4f6;
  box-shadow: 2px 0 4px rgba(0,0,0,.04);
}

.th-day {
  text-align: center;
  color: #4b5563;
  border-right: 1px solid #e5e7eb;
  background: #f3f4f6;
}
.th-weekend {
  color: #7c3aed;
  background: #ede9fe;
}

.th-total {
  text-align: right;
  padding-right: 14px;
  color: #065f46;
  border-left: 2px solid #d1d5db;
  background: #d1fae5;
  position: sticky;
  right: 0;
  z-index: 40;
  box-shadow: -2px 0 4px rgba(0,0,0,.04);
}

.th-label { display: inline-block; }

/* ══ TBODY ══ */
.data-row { transition: background 0.08s ease; }
.row-base { background: #ffffff; }
.row-alt  { background: #f8fafc; }

.data-row:hover td { background: #f0fdf4 !important; }

/* Body cells */
.td-item,
.td-day,
.td-total-cell {
  padding: 11px 10px;
  font-size: 12px;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: middle;
}

/* Sticky item column */
.td-item {
  padding-left: 14px;
  padding-right: 10px;
  border-right: 2px solid #d1d5db;
  position: sticky;
  left: 0;
  z-index: 20;
  box-shadow: 2px 0 4px rgba(0,0,0,.04);
}
.td-item-base { background: #ffffff; }
.td-item-alt  { background: #f8fafc; }

.item-name {
  font-weight: 800;
  color: #111827;
  font-size: 12px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-code {
  font-family: ui-monospace, 'Cascadia Code', monospace;
  font-size: 10px;
  color: #6b7280;
  font-weight: 500;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Day cells */
.td-day {
  text-align: center;
  border-right: 1px solid #e5e7eb;
  background: transparent;
}
.td-weekend { background: rgba(237,233,254,0.35) !important; }

.cell-value {
  display: inline-block;
  font-family: ui-monospace, 'Cascadia Code', monospace;
  font-weight: 800;
  font-size: 12px;
  color: #1e293b;
  letter-spacing: 0;
  line-height: 1;
  white-space: nowrap;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 5px;
  padding: 2px 5px;
}
.cell-empty {
  color: #d1d5db;
  font-size: 12px;
  user-select: none;
  font-weight: 300;
}

/* Sticky total column */
.td-total-cell {
  text-align: right;
  padding-right: 14px;
  border-left: 2px solid #d1d5db;
  background: #f0fdf4;
  position: sticky;
  right: 0;
  z-index: 20;
  box-shadow: -2px 0 4px rgba(0,0,0,.04);
}
.total-amt {
  font-weight: 900;
  color: #065f46;
  font-size: 13px;
  font-family: ui-monospace, monospace;
  line-height: 1;
}
.total-qty {
  font-size: 10px;
  color: #6b7280;
  font-weight: 600;
  margin-top: 3px;
}

/* ══ TFOOT ══ */
tfoot tr {
  position: sticky;
  bottom: 0;
  z-index: 30;
}

.footer-row td {
  border-top: 2px solid #6ee7b7;
  padding: 12px 10px;
}

.td-foot-label {
  padding-left: 14px;
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #064e3b;
  background: #a7f3d0;
  border-right: 2px solid #6ee7b7;
  white-space: nowrap;
  position: sticky;
  left: 0;
  z-index: 40;
  box-shadow: 2px 0 4px rgba(0,0,0,.05);
}

.td-foot-day {
  background: #a7f3d0;
  border-right: 1px solid #6ee7b7;
}
.td-foot-weekend { background: #c4b5fd; }

.td-foot-amount {
  text-align: right;
  padding-right: 14px;
  background: #a7f3d0;
  border-left: 2px solid #6ee7b7;
  font-weight: 900;
  font-size: 15px;
  color: #064e3b;
  font-family: ui-monospace, monospace;
  white-space: nowrap;
  position: sticky;
  right: 0;
  z-index: 40;
  box-shadow: -2px 0 4px rgba(0,0,0,.05);
  letter-spacing: -0.02em;
}

/* ══════════════════════════════════════════════
   CHECKBOXES
   ══════════════════════════════════════════════ */
.checkbox-circle {
  width: 20px; height: 20px; border-radius: 50%; border: 2px solid;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  transition: background 0.2s, border-color 0.2s, box-shadow 0.2s, transform 0.15s cubic-bezier(0.34,1.56,0.64,1);
}
.checkbox-unselected    { background:#fff; border-color:#d1d5db; }
.checkbox-indeterminate { background:#d1fae5; border-color:#10b981; }
.checkbox-selected      { background:#059669; border-color:#059669; box-shadow:0 0 0 3px rgba(5,150,105,.2); transform:scale(1.08); }

.checkbox-circle-sm {
  width: 16px; height: 16px; border-radius: 50%; border: 2px solid;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  transition: all 0.15s ease;
}
.checkbox-sm-unselected    { background:rgba(255,255,255,0.2); border-color:rgba(255,255,255,0.5); }
.checkbox-sm-indeterminate { background:rgba(255,255,255,0.3); border-color:rgba(255,255,255,0.8); }
.checkbox-sm-selected      { background:white; border-color:white; }

.check-icon { animation: pop-check 0.22s cubic-bezier(0.34,1.56,0.64,1) forwards; }
@keyframes pop-check {
  0%   { opacity:0; transform:scale(0.3) rotate(-15deg); }
  60%  { transform:scale(1.2) rotate(3deg); }
  100% { opacity:1; transform:scale(1) rotate(0deg); }
}

/* ══ ORDER ROWS ══ */
.order-row { transition: background 0.1s ease; }
.order-row-selected         { background:#f0fdf4; }
.order-row-selected:hover   { background:#dcfce7; }
.order-row-unselected       { background:#fff; }
.order-row-unselected:hover { background:#f9fafb; }
.order-row:hover .checkbox-unselected {
  border-color:#10b981; background:#f0fdf4; transform:scale(1.05);
}

/* ══ ORDERS SCROLL ══ */
.orders-scroll {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db transparent;
}
.orders-scroll::-webkit-scrollbar { width: 4px; }
.orders-scroll::-webkit-scrollbar-track { background: transparent; }
.orders-scroll::-webkit-scrollbar-thumb { background: #e5e7eb; border-radius: 99px; }
.orders-scroll::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

/* ══ MOBILE: tighten day columns ══ */
@media (max-width: 480px) {
  .col-item  { width: 110px; min-width: 100px; }
  .col-day   { width: 60px;  min-width: 56px; }
  .col-total { width: 80px;  min-width: 72px; }
  .cell-value { font-size: 10px; }
  .item-name  { font-size: 10px; }
  .td-foot-amount { font-size: 11px; }
  .summary-scroll-area { max-height: 200px; }
}

/* ══════════════════════════════════════════════
   MODERN FILTER CARD
   ══════════════════════════════════════════════ */
.filter-card {
  background: linear-gradient(135deg, #fafbff 0%, #f5f7ff 50%, #fafffe 100%);
  border: 1.5px solid #e8eaf6;
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(99,102,241,.06), 0 1px 2px rgba(0,0,0,.04);
}

/* Header row */
.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.filter-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-icon-wrap {
  width: 26px; height: 26px;
  border-radius: 8px;
  background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(99,102,241,.2);
}
.filter-title {
  font-size: 13px;
  font-weight: 800;
  color: #1e1b4b;
  letter-spacing: -0.01em;
}
.filter-active-badge {
  font-size: 9px;
  font-weight: 800;
  color: #4f46e5;
  background: #e0e7ff;
  border: 1px solid #c7d2fe;
  padding: 2px 7px;
  border-radius: 99px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

/* Clear button */
.clear-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 8px;
  transition: all 0.15s ease;
  white-space: nowrap;
  flex-shrink: 0;
  border: 1.5px solid;
  cursor: pointer;
}
.clear-btn-active {
  color: #dc2626;
  background: #fff1f2;
  border-color: #fecaca;
  box-shadow: 0 1px 2px rgba(220,38,38,.08);
}
.clear-btn-active:hover {
  color: #b91c1c;
  background: #fee2e2;
  border-color: #fca5a5;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(220,38,38,.15);
}
.clear-btn-disabled {
  color: #c4c7d4;
  background: #f8f9fc;
  border-color: #e8eaf0;
  cursor: not-allowed;
}

/* Filter field */
.filter-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.filter-label {
  font-size: 9px;
  font-weight: 900;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding-left: 2px;
}

/* Input wrapper */
.filter-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
  transition: all 0.15s ease;
}
.filter-input-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px; height: 14px;
  color: #9ca3af;
  pointer-events: none;
  transition: color 0.15s;
}
.filter-input-wrap:focus-within .filter-input-icon { color: #6366f1; }
.input-active .filter-input-icon { color: #4f46e5; }

.filter-input {
  width: 100%;
  padding: 9px 28px 9px 32px;
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  color: #374151;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}
.filter-input:hover { border-color: #c7d2fe; }
.filter-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,.12);
  background: #fafbff;
}
.input-active .filter-input {
  border-color: #a5b4fc;
  background: #fafbff;
}
.filter-select {
  appearance: none;
  cursor: pointer;
  padding-right: 28px;
}

/* Per-field inline clear X */
.input-clear-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px; height: 16px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  color: #9ca3af;
  background: #f3f4f6;
  border: none;
  cursor: pointer;
  transition: all 0.12s ease;
  z-index: 3;
}
.input-clear-btn:hover { color: #ef4444; background: #fee2e2; }

/* Pills row */
.filter-pills-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 10px;
  font-weight: 700;
  border: 1px solid;
}

.pill-date {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #15803d;
}
.pill-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pill-dot-active  { background: #22c55e; animation: pulse 1.5s infinite; }
.pill-dot-idle    { background: #6b7280; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.pill-text { font-size: 10px; font-weight: 700; }

.pill-customer {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}
.pill-remove {
  display: flex; align-items: center; justify-content: center;
  margin-left: 2px;
  border: none; background: none;
  cursor: pointer;
  color: #93c5fd;
  transition: color 0.1s;
  padding: 0;
}
.pill-remove:hover { color: #3b82f6; }

.pill-count {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #475569;
}
.pill-count-num {
  font-weight: 900;
  font-size: 11px;
  color: #1e293b;
}
.pill-count-label {
  font-weight: 500;
  font-size: 10px;
  color: #94a3b8;
}
</style>
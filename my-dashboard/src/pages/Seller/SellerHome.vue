<script setup lang="ts">
import { ref, watch, computed, inject } from 'vue'
import {
  createListResource,
  createResource,
  Badge,
  Button,
  Dialog,
  LoadingIndicator
} from 'frappe-ui'
import {
  Truck,
  FileText,
  LayoutDashboard,
  RefreshCcw,
  Package,
  ShoppingBag,
  Calendar,
  User,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Clock,
  CheckCircle,
  XCircle,
  Newspaper,
  Star,
  Zap
} from 'lucide-vue-next'

declare const frappe: any

const props = defineProps<{ filters: { customer?: string; seller?: string } }>()
const showToast = inject('showToast') as (msg: string, type?: 'success' | 'error') => void

const ALL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_SHORT: Record<string, string> = {
  Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed',
  Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun'
}
const DAY_QTY_FIELD: Record<string, string> = {
  Monday: 'monday_qty', Tuesday: 'tuesday_qty', Wednesday: 'wednesday_qty',
  Thursday: 'thursday_qty', Friday: 'friday_qty', Saturday: 'saturday_qty', Sunday: 'sunday_qty'
}

// ─── RESOURCES ───
const orders = createListResource({
  doctype: 'Sales Order',
  fields: [
    'name', 'customer_name', 'status', 'grand_total', 'currency',
    'docstatus', 'per_delivered', 'per_billed', 'transaction_date',
    'custom_subscription_refereance'
  ],
  filters: {},
  orderBy: 'creation desc',
  pageLength: 100,
  auto: true,
})

const orderDetails = createResource({
  url: 'frappe.client.get',
  makeParams(values: { name: string }) {
    return { doctype: 'Sales Order', name: values.name }
  },
})

const orderWorkflow = createResource({
  url: 'my_frappe_app.api.process_order_workflow',
  auto: false
})

const subsResource = createResource({
  url: 'my_frappe_app.api.get_seller_subscriptions',
})

const processSubResource = createResource({
  url: 'my_frappe_app.api.process_subscription',
  onSuccess(data: any) {
    processingSubId.value = ''
    if (data.status === 'success') {
      showToast(data.message, 'success')
      subsResource.fetch({ seller: sellerName.value })
    } else {
      showToast(data.message || 'Operation failed', 'error')
    }
  },
  onError(err: any) {
    processingSubId.value = ''
    showToast(err?.message || 'Error', 'error')
  }
})

// ─── STATE ───
const showDetail = ref(false)
const processingId = ref('')
const processingSubId = ref('')
const expandedSubId = ref<string | null>(null)

// Filter tabs: 'all' | 'subscription_pending' | 'daily' | 'normal'
const activeFilter = ref<'all' | 'subscription_pending' | 'daily' | 'normal'>('all')

const sellerName = computed(() => props.filters.seller || '')

// ─── SUBSCRIPTIONS ───
const subscriptions = computed(() => (subsResource.data as any)?.subscriptions || [])

// ─── COMBINED ROWS ───
// Subscriptions (pending/active) + Sales Orders merged into one list
const combinedRows = computed(() => {
  const rows: any[] = []

  // Add subscriptions (only when filter allows)
  if (activeFilter.value === 'all' || activeFilter.value === 'subscription_pending') {
    for (const sub of subscriptions.value) {
      if (activeFilter.value === 'subscription_pending' && sub.status !== 'Accept Pending') continue
      rows.push({ row_type: 'subscription', ...sub })
    }
  }

  // Add Sales Orders
  if (activeFilter.value !== 'subscription_pending') {
    for (const o of (orders.data || []) as any[]) {
      const isSubOrder = !!o.custom_subscription_refereance
      if (activeFilter.value === 'daily' && !isSubOrder) continue
      if (activeFilter.value === 'normal' && isSubOrder) continue
      rows.push({ row_type: 'order', ...o })
    }
  }

  return rows
})

// ─── STATS ───
const stats = computed(() => {
  const subs = subscriptions.value
  const orderData = (orders.data || []) as any[]
  return {
    subPending: subs.filter((s: any) => s.status === 'Accept Pending').length,
    subActive: subs.filter((s: any) => s.status === 'Active').length,
    orderPending: orderData.filter((o: any) => o.docstatus === 0 && !o.custom_subscription_refereance).length,
    toDeliver: orderData.filter((o: any) => o.docstatus === 1 && o.per_delivered < 100).length,
    completed: orderData.filter((o: any) => o.per_delivered >= 100).length,
  }
})

// ─── WATCHERS ───
watch(
  () => [props.filters.customer, props.filters.seller],
  ([customer, seller]) => {
    if (customer) {
      orders.update({ filters: { customer } })
      orders.reload()
    }
    if (seller) {
      subsResource.fetch({ seller })
    }
  },
  { immediate: true }
)

// ─── ACTIONS ───
const openOrder = (row: any) => {
  showDetail.value = true
  orderDetails.fetch({ name: row.name })
}

const runOrderAction = async (id: string, action: string) => {
  processingId.value = id
  try {
    const res = await orderWorkflow.submit({ order_id: id, action })
    if (res?.status === 'success') {
      showToast(res.message, 'success')
      await orders.reload()
      if (showDetail.value) await orderDetails.fetch({ name: id })
    } else {
      showToast(res?.message || 'Operation Failed', 'error')
    }
  } catch (error: any) {
    showToast(error?.message || "System Error", 'error')
  } finally {
    processingId.value = ''
  }
}

const runSubAction = (subName: string, action: 'accept' | 'reject') => {
  processingSubId.value = subName
  processSubResource.fetch({ sub_name: subName, action })
}

const toggleSubExpand = (id: string) => {
  expandedSubId.value = expandedSubId.value === id ? null : id
}

// ─── HELPERS ───
type BadgeTheme = "gray" | "blue" | "green" | "red" | "orange"
const getStatusTheme = (status: string): BadgeTheme => {
  if (['Completed', 'To Bill', 'To Deliver'].includes(status)) return 'green'
  if (status === 'Draft') return 'red'
  if (status === 'Cancelled') return 'gray'
  return 'orange'
}

const formatCurrency = (amount: number, currency = 'INR') =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount)
</script>

<template>
  <div class="space-y-6 max-w-7xl mx-auto pb-10 font-sans text-gray-900">

    <!-- ── STATS CARDS (clickable filters) ── -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">

      <!-- Sub Pending -->
      <button @click="activeFilter = activeFilter === 'subscription_pending' ? 'all' : 'subscription_pending'" :class="[
        'p-4 rounded-3xl border shadow-sm flex items-center justify-between transition-all text-left',
        activeFilter === 'subscription_pending'
          ? 'bg-amber-500 border-amber-500'
          : 'bg-white border-amber-100 hover:border-amber-300'
      ]">
        <div>
          <p :class="['text-[10px] font-bold uppercase tracking-widest mb-1',
            activeFilter === 'subscription_pending' ? 'text-amber-100' : 'text-amber-400']">Sub Pending</p>
          <p :class="['text-3xl font-black',
            activeFilter === 'subscription_pending' ? 'text-white' : 'text-gray-900']">{{ stats.subPending }}</p>
        </div>
        <div
          :class="['h-11 w-11 rounded-2xl flex items-center justify-center transition-colors',
            activeFilter === 'subscription_pending' ? 'bg-amber-400 text-white' : 'bg-amber-50 text-amber-500 hover:bg-amber-500 hover:text-white']">
          <Newspaper class="w-5 h-5" />
        </div>
      </button>

      <!-- Sub Active -->
      <div class="bg-white p-4 rounded-3xl border border-green-100 shadow-sm flex items-center justify-between">
        <div>
          <p class="text-[10px] font-bold text-green-500 uppercase tracking-widest mb-1">Sub Active</p>
          <p class="text-3xl font-black text-gray-900">{{ stats.subActive }}</p>
        </div>
        <div class="h-11 w-11 rounded-2xl bg-green-50 flex items-center justify-center text-green-600">
          <CheckCircle class="w-5 h-5" />
        </div>
      </div>

      <!-- Normal Orders Pending -->
      <button @click="activeFilter = activeFilter === 'normal' ? 'all' : 'normal'" :class="[
        'p-4 rounded-3xl border shadow-sm flex items-center justify-between transition-all text-left',
        activeFilter === 'normal' ? 'bg-orange-500 border-orange-500' : 'bg-white border-orange-100 hover:border-orange-300'
      ]">
        <div>
          <p :class="['text-[10px] font-bold uppercase tracking-widest mb-1',
            activeFilter === 'normal' ? 'text-orange-100' : 'text-orange-400']">To Accept</p>
          <p :class="['text-3xl font-black', activeFilter === 'normal' ? 'text-white' : 'text-gray-900']">{{
            stats.orderPending }}</p>
        </div>
        <div
          :class="['h-11 w-11 rounded-2xl flex items-center justify-center transition-colors',
            activeFilter === 'normal' ? 'bg-orange-400 text-white' : 'bg-orange-50 text-orange-500 hover:bg-orange-500 hover:text-white']">
          <Clock class="w-5 h-5" />
        </div>
      </button>

      <!-- Daily Orders -->
      <button @click="activeFilter = activeFilter === 'daily' ? 'all' : 'daily'" :class="[
        'p-4 rounded-3xl border shadow-sm flex items-center justify-between transition-all text-left',
        activeFilter === 'daily' ? 'bg-blue-600 border-blue-600' : 'bg-white border-blue-100 hover:border-blue-300'
      ]">
        <div>
          <p :class="['text-[10px] font-bold uppercase tracking-widest mb-1',
            activeFilter === 'daily' ? 'text-blue-200' : 'text-blue-400']">Daily Orders</p>
          <p :class="['text-3xl font-black', activeFilter === 'daily' ? 'text-white' : 'text-gray-900']">{{
            stats.toDeliver }}</p>
        </div>
        <div
          :class="['h-11 w-11 rounded-2xl flex items-center justify-center transition-colors',
            activeFilter === 'daily' ? 'bg-blue-500 text-white' : 'bg-blue-50 text-blue-500 hover:bg-blue-600 hover:text-white']">
          <Truck class="w-5 h-5" />
        </div>
      </button>

      <!-- Completed -->
      <div class="bg-white p-4 rounded-3xl border border-emerald-100 shadow-sm flex items-center justify-between">
        <div>
          <p class="text-[10px] font-bold text-emerald-500 uppercase tracking-widest mb-1">Completed</p>
          <p class="text-3xl font-black text-gray-900">{{ stats.completed }}</p>
        </div>
        <div class="h-11 w-11 rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600">
          <CheckCircle class="w-5 h-5" />
        </div>
      </div>
    </div>

    <!-- ── HEADER ── -->
    <div class="flex justify-between items-center bg-white p-5 rounded-3xl border border-gray-100 shadow-sm">
      <div class="flex items-center gap-4">
        <div class="p-3 bg-gray-900 rounded-2xl text-white shadow-lg ring-4 ring-gray-50">
          <LayoutDashboard class="w-6 h-6" />
        </div>
        <div>
          <h2 class="text-2xl font-black tracking-tight">Seller Operations</h2>
          <p class="text-sm text-gray-500 font-medium">
            <span v-if="activeFilter === 'all'">All — Subscriptions & Orders</span>
            <span v-else-if="activeFilter === 'subscription_pending'">Showing: Subscription Requests</span>
            <span v-else-if="activeFilter === 'daily'">Showing: Daily Auto-Orders</span>
            <span v-else-if="activeFilter === 'normal'">Showing: Normal Orders</span>
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button v-if="activeFilter !== 'all'" @click="activeFilter = 'all'"
          class="flex items-center gap-1.5 bg-gray-100 hover:bg-gray-200 text-gray-600 text-xs font-semibold px-3 py-1.5 rounded-xl transition-all">
          <XCircle class="w-3.5 h-3.5" /> Clear Filter
        </button>
        <Button variant="outline" @click="() => { subsResource.fetch({ seller: sellerName }); orders.reload() }"
          :loading="subsResource.loading || orders.loading">
          <template #prefix>
            <RefreshCcw class="w-4 h-4" />
          </template> Refresh
        </Button>
      </div>
    </div>

    <!-- ── LEGEND ── -->
    <div class="flex flex-wrap gap-2 px-1">
      <div class="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-1.5">
        <div class="w-2.5 h-2.5 rounded-full bg-amber-400 flex-shrink-0"></div>
        <span class="text-xs font-semibold text-amber-700">Subscription Request — Accept to start daily delivery from
          next
          day</span>
      </div>
      <div class="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-xl px-3 py-1.5">
        <div class="w-2.5 h-2.5 rounded-full bg-blue-400 flex-shrink-0"></div>
        <span class="text-xs font-semibold text-blue-700">Daily Auto-Order — System generated, DN auto-created</span>
      </div>
      <div class="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5">
        <div class="w-2.5 h-2.5 rounded-full bg-gray-300 flex-shrink-0"></div>
        <span class="text-xs font-semibold text-gray-500">Normal Order</span>
      </div>
    </div>

    <!-- ── COMBINED LIST ── -->
    <div class="bg-white rounded-[2rem] border border-gray-100 shadow-xl overflow-hidden min-h-[500px]">

      <div v-if="subsResource.loading || orders.loading" class="flex flex-col items-center justify-center py-40">
        <LoadingIndicator class="w-8 h-8 mb-4 text-blue-600" />
        <p class="text-gray-400 font-medium animate-pulse">Loading...</p>
      </div>

      <div v-else-if="combinedRows.length === 0" class="flex flex-col items-center justify-center py-40">
        <Package class="w-12 h-12 text-gray-200 mb-4" />
        <p class="text-gray-400 font-medium">Nothing to show</p>
        <button v-if="activeFilter !== 'all'" @click="activeFilter = 'all'"
          class="mt-3 text-sm text-blue-600 hover:underline">Show all</button>
      </div>

      <div v-else class="divide-y divide-gray-50">
        <template v-for="row in combinedRows" :key="row.row_type + '-' + row.name">

          <!-- ════════════════════════════════ -->
          <!-- SUBSCRIPTION REQUEST ROW         -->
          <!-- ════════════════════════════════ -->
          <div v-if="row.row_type === 'subscription'" :class="[
            'border-l-4 transition-all',
            row.status === 'Accept Pending'
              ? 'border-l-amber-400 bg-amber-50/50'
              : 'border-l-green-400 bg-green-50/20'
          ]">
            <!-- Row header -->
            <div class="flex items-center justify-between px-6 py-4 gap-3">
              <!-- Left: icon + info -->
              <div class="flex items-center gap-3 min-w-0">
                <div :class="[
                  'p-2.5 rounded-xl flex-shrink-0',
                  row.status === 'Accept Pending' ? 'bg-amber-100 text-amber-600' : 'bg-green-100 text-green-600'
                ]">
                  <Newspaper class="w-5 h-5" />
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-black text-gray-900 font-mono text-sm">{{ row.name }}</span>
                    <!-- Type pill -->
                    <span
                      class="inline-flex items-center gap-1 bg-amber-100 text-amber-700 text-[9px] font-bold px-2 py-0.5 rounded-full border border-amber-200">
                      <Star class="w-2.5 h-2.5" /> Subscription Request
                    </span>
                    <!-- Status pill -->
                    <span :class="[
                      'text-[9px] font-bold px-2 py-0.5 rounded-full border',
                      row.status === 'Accept Pending' ? 'bg-amber-50 text-amber-600 border-amber-200'
                        : row.status === 'Active' ? 'bg-green-50 text-green-600 border-green-200'
                          : 'bg-gray-50 text-gray-500 border-gray-200'
                    ]">{{ row.status }}</span>
                  </div>
                  <p class="text-xs text-gray-500 mt-0.5">
                    Customer: <span class="font-semibold text-gray-700">{{ row.customer_name }}</span>
                    <span class="mx-1">·</span>{{ row.formatted_start }} → {{ row.formatted_end }}
                  </p>
                  <p class="text-[10px] text-gray-400 mt-0.5">
                    Primary item: <span class="font-semibold text-gray-600">{{ row.primary_item_name }}</span>
                  </p>
                </div>
              </div>

              <!-- Right: actions + expand -->
              <div class="flex items-center gap-2 flex-shrink-0">
                <template v-if="row.status === 'Accept Pending'">
                  <Button variant="solid" class="!bg-green-600 hover:!bg-green-700 !text-white" size="sm"
                    :loading="processingSubId === row.name" @click.stop="runSubAction(row.name, 'accept')">
                    <template #prefix>
                      <CheckCircle class="w-3.5 h-3.5" />
                    </template>
                    Accept Plan
                  </Button>
                  <Button variant="subtle" theme="red" size="sm" :loading="processingSubId === row.name"
                    @click.stop="runSubAction(row.name, 'reject')">Reject</Button>
                </template>
                <template v-else-if="row.status === 'Active'">
                  <div class="flex items-center gap-1.5 bg-green-100 border border-green-200 rounded-lg px-2.5 py-1.5">
                    <Zap class="w-3 h-3 text-green-600" />
                    <span class="text-[10px] font-bold text-green-700">Auto-running</span>
                  </div>
                  <Button variant="subtle" theme="red" size="sm" :loading="processingSubId === row.name"
                    @click.stop="runSubAction(row.name, 'reject')">Cancel Plan</Button>
                </template>

                <button @click="toggleSubExpand(row.name)"
                  class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all">
                  <ChevronUp v-if="expandedSubId === row.name" class="w-4 h-4" />
                  <ChevronDown v-else class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- Expanded schedule -->
            <div v-if="expandedSubId === row.name"
              class="px-6 pb-5 pt-0 border-t border-amber-100/80 bg-white/50 space-y-3">

              <div v-if="row.status === 'Accept Pending'"
                class="mt-3 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2.5">
                <Star class="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                <p class="text-xs text-amber-800">
                  <span class="font-bold">Accept this plan</span> to activate daily delivery.
                  From <strong>next day</strong>, system auto-generates Sales Orders + Delivery Notes per below
                  schedule.
                  You only handle <strong>invoicing</strong>.
                </p>
              </div>

              <div v-for="si in row.schedule_items" :key="si.item_code"
                class="bg-gray-50 rounded-xl border border-gray-100 overflow-hidden">
                <div class="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-100">
                  <span class="text-xs font-bold text-gray-800">{{ si.item_name }}</span>
                  <span v-if="si.is_primary_item"
                    class="text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-bold">Primary</span>
                </div>
                <div class="p-3 flex gap-2 flex-wrap">
                  <template v-for="day in ALL_DAYS" :key="day">
                    <div :class="[
                      'flex flex-col items-center px-3 py-2 rounded-xl font-bold min-w-[44px] text-center',
                      (si[DAY_QTY_FIELD[day]] || 0) > 0
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'bg-gray-100 text-gray-400'
                    ]">
                      <span class="text-[9px] uppercase tracking-wide">{{ DAY_SHORT[day] }}</span>
                      <span v-if="(si[DAY_QTY_FIELD[day]] || 0) > 0" class="text-sm font-black leading-tight mt-0.5">
                        {{ si[DAY_QTY_FIELD[day]] }}
                      </span>
                      <span v-else class="text-[10px] opacity-30 mt-0.5">—</span>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- ════════════════════════════════ -->
          <!-- SALES ORDER ROW                  -->
          <!-- ════════════════════════════════ -->
          <div v-else :class="[
            'flex items-center justify-between px-6 py-4 gap-3 cursor-pointer group transition-all border-l-4',
            row.custom_subscription_refereance
              ? 'border-l-blue-300 bg-blue-50/20 hover:bg-blue-50/50'
              : 'border-l-transparent hover:bg-gray-50/70'
          ]" @click="openOrder(row)">
            <!-- Left: info -->
            <div class="flex items-center gap-3 min-w-0">
              <div :class="[
                'p-2.5 rounded-xl flex-shrink-0 transition-colors',
                row.custom_subscription_refereance
                  ? 'bg-blue-100 text-blue-600 group-hover:bg-blue-500 group-hover:text-white'
                  : 'bg-gray-100 text-gray-500 group-hover:bg-blue-100 group-hover:text-blue-600'
              ]">
                <Newspaper v-if="row.custom_subscription_refereance" class="w-5 h-5" />
                <ShoppingBag v-else class="w-5 h-5" />
              </div>

              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span :class="[
                    'font-bold font-mono text-sm transition-colors',
                    row.custom_subscription_refereance ? 'text-blue-700' : 'text-gray-900 group-hover:text-blue-600'
                  ]">{{ row.name }}</span>

                  <!-- Type pill -->
                  <span v-if="row.custom_subscription_refereance"
                    class="inline-flex items-center gap-1 bg-blue-100 text-blue-700 text-[9px] font-bold px-2 py-0.5 rounded-full border border-blue-200">
                    <Zap class="w-2.5 h-2.5" /> Daily Sub-Auto-Order
                  </span>
                  <span v-else
                    class="inline-flex items-center gap-1 bg-gray-100 text-gray-500 text-[9px] font-bold px-2 py-0.5 rounded-full border border-gray-200">
                    <ShoppingBag class="w-2.5 h-2.5" /> Normal Order
                  </span>

                  <!-- ERPNext status -->
                  <Badge :theme="getStatusTheme(row.status)" variant="subtle" :label="row.status" size="sm" />
                </div>

                <p class="text-xs text-gray-400 mt-0.5 flex items-center gap-1.5">
                  <Calendar class="w-3 h-3" /> {{ row.transaction_date }}
                  <span v-if="row.customer_name">· {{ row.customer_name }}</span>
                </p>
                <p v-if="row.custom_subscription_refereance" class="text-[10px] text-blue-400 font-mono mt-0.5">
                  📋 {{ row.custom_subscription_refereance }}
                </p>
              </div>
            </div>

            <!-- Right: amount + action buttons -->
            <div class="flex items-center gap-2 flex-shrink-0" @click.stop>
              <span class="font-black text-gray-800 font-mono text-sm">
                {{ formatCurrency(row.grand_total, row.currency) }}
              </span>

              <!-- Accept normal order -->
              <Button v-if="row.docstatus === 0" variant="solid" theme="blue" size="sm"
                :loading="processingId === row.name" @click="runOrderAction(row.name, 'accept')">Accept</Button>

              <!-- Deliver (non-subscription only) -->
              <Button v-if="row.docstatus === 1 && row.per_delivered < 100 && !row.custom_subscription_refereance"
                variant="subtle" theme="gray" size="sm" :loading="processingId === row.name"
                @click="runOrderAction(row.name, 'deliver')">
                <template #prefix>
                  <Truck class="w-3.5 h-3.5" />
                </template> Deliver
              </Button>

              <!-- Invoice -->
              <Button v-if="row.per_delivered >= 100 && row.per_billed < 100" variant="subtle" theme="gray" size="sm"
                :loading="processingId === row.name" @click="runOrderAction(row.name, 'invoice')">
                <template #prefix>
                  <FileText class="w-3.5 h-3.5" />
                </template> Invoice
              </Button>

              <!-- Auto-delivered tag for subscription daily orders -->
              <span v-if="row.custom_subscription_refereance && row.docstatus === 1 && row.per_delivered < 100"
                class="text-[10px] text-blue-500 font-semibold bg-blue-50 border border-blue-100 px-2 py-1 rounded-lg whitespace-nowrap">⚡
                Auto-Delivered</span>

              <ChevronRight class="w-4 h-4 text-gray-300 ml-1" />
            </div>
          </div>

        </template>
      </div>
    </div>

    <!-- ── ORDER DETAIL DIALOG ── -->
    <Dialog v-model="showDetail" :options="{ size: '4xl' }">
      <template #body-title>
        <div class="flex items-center justify-between w-full pr-8">
          <div class="flex items-center gap-3">
            <div :class="[
              'h-10 w-10 rounded-full flex items-center justify-center',
              orderDetails.data?.custom_subscription_refereance ? 'bg-blue-50 text-blue-600' : 'bg-gray-50 text-gray-600'
            ]">
              <Newspaper v-if="orderDetails.data?.custom_subscription_refereance" class="w-5 h-5" />
              <Package v-else class="w-5 h-5" />
            </div>
            <div>
              <h3 class="text-xl font-black leading-none">Order Details</h3>
              <p class="text-sm text-gray-500 font-mono mt-1">{{ orderDetails.data?.name }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="orderDetails.data?.custom_subscription_refereance"
              class="inline-flex items-center gap-1 bg-blue-100 text-blue-700 text-xs font-bold px-3 py-1 rounded-full">
              <Newspaper class="w-3 h-3" /> {{ orderDetails.data.custom_subscription_refereance }}
            </span>
            <Badge v-if="orderDetails.data" :theme="getStatusTheme(orderDetails.data.status)" size="lg"
              :label="orderDetails.data.status" />
          </div>
        </div>
      </template>

      <template #body-content>
        <div v-if="orderDetails.loading" class="flex flex-col items-center justify-center h-80">
          <LoadingIndicator class="w-10 h-10 text-blue-500" />
        </div>

        <div v-else-if="orderDetails.data" class="py-6 space-y-8">

          <div v-if="orderDetails.data.custom_subscription_refereance && orderDetails.data.docstatus === 1"
            class="flex items-start gap-3 bg-blue-50 border border-blue-200 rounded-2xl p-4">
            <Zap class="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
            <p class="text-xs text-blue-700">
              <span class="font-bold">Daily Subscription Order.</span>
              Auto-generated by cron. Delivery note created automatically. Only invoice needed manually.
            </p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div class="bg-gray-50 p-5 rounded-2xl border border-gray-100 flex items-start gap-3">
              <div class="bg-white p-2 rounded-lg shadow-sm text-gray-500">
                <User class="w-4 h-4" />
              </div>
              <div>
                <p class="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1">Customer</p>
                <p class="font-bold">{{ orderDetails.data.customer_name }}</p>
              </div>
            </div>
            <div class="bg-gray-50 p-5 rounded-2xl border border-gray-100 flex items-start gap-3">
              <div class="bg-white p-2 rounded-lg shadow-sm text-gray-500">
                <Calendar class="w-4 h-4" />
              </div>
              <div>
                <p class="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1">Date</p>
                <p class="font-bold">{{ orderDetails.data.transaction_date }}</p>
              </div>
            </div>
            <div class="bg-blue-600 p-5 rounded-2xl text-white">
              <p class="text-[11px] font-bold text-blue-200 uppercase tracking-widest mb-1">Grand Total</p>
              <p class="font-black text-2xl">{{ formatCurrency(orderDetails.data.grand_total,
                orderDetails.data.currency) }}</p>
            </div>
          </div>

          <div class="border border-gray-200 rounded-xl overflow-hidden">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 text-[10px] uppercase font-bold text-gray-500">
                <tr>
                  <th class="px-5 py-4 text-left">Item</th>
                  <th class="px-5 py-4 text-right">Qty</th>
                  <th class="px-5 py-4 text-right">Rate</th>
                  <th class="px-5 py-4 text-right">Amount</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="item in orderDetails.data.items" :key="item.name">
                  <td class="px-5 py-4 font-bold text-gray-900">{{ item.item_name }}</td>
                  <td class="px-5 py-4 text-right">{{ item.qty }}</td>
                  <td class="px-5 py-4 text-right">{{ formatCurrency(item.rate, orderDetails.data.currency) }}</td>
                  <td class="px-5 py-4 text-right font-bold">{{ formatCurrency(item.amount, orderDetails.data.currency)
                  }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="flex justify-end gap-3 pt-6 border-t border-gray-100">
            <Button v-if="orderDetails.data.docstatus === 0" variant="solid" theme="blue" size="xl"
              :loading="processingId === orderDetails.data.name"
              @click="runOrderAction(orderDetails.data.name, 'accept')">Accept Order</Button>

            <Button
              v-if="orderDetails.data.docstatus === 1 && orderDetails.data.per_delivered < 100 && !orderDetails.data.custom_subscription_refereance"
              variant="solid" theme="gray" size="xl" :loading="processingId === orderDetails.data.name"
              @click="runOrderAction(orderDetails.data.name, 'deliver')">Generate Delivery Note</Button>

            <Button v-if="orderDetails.data.per_delivered >= 100 && orderDetails.data.per_billed < 100" variant="solid"
              theme="gray" size="xl" :loading="processingId === orderDetails.data.name"
              @click="runOrderAction(orderDetails.data.name, 'invoice')">Generate Invoice</Button>
          </div>
        </div>
      </template>
    </Dialog>

  </div>
</template>
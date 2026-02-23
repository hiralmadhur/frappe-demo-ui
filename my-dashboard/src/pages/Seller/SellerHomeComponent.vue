<script setup lang="ts">
import { ref, watch, computed, inject } from 'vue'
import { createListResource, createResource, Button } from 'frappe-ui'
import {
  LayoutDashboard, Users, RefreshCcw, XCircle, Receipt,
  ShoppingCart, Truck, CreditCard, ClipboardList, BookOpen, Plus,
  UserCheck
} from 'lucide-vue-next'

import SellerStatsCards          from '@/components/Seller/SellerStatsCards.vue'
import SalesOrder                from '@/components/Seller/SalesOrder.vue'
import SellerOrderDetailDialog   from '@/components/Seller/SellerOrderDetailDialog.vue'
import SellerCustomersTab        from '@/components/Seller/SellerCustomersTab.vue'
import SellerCreateInvoiceDialog from '@/components/Seller/SellerCreateInvoiceDialog.vue'
import Deliverynote              from '@/components/Seller/Deliverynote.vue'
import SalesInvoiceList          from '@/components/Seller/SalesInvoiceList.vue'
import PaymentEntryList from '@/components/Seller/PaymentEntryList.vue'

// ─── PROPS / INJECT ───────────────────────────────────────────────────────────
const props = defineProps<{ filters: { customer?: string; seller?: string; category?: string } }>()
const showToast = inject('showToast') as (msg: string, type?: 'success' | 'error') => void

// ─── EMITS — notify parent when any dialog opens/closes (for sidebar z-index) ─
const emit = defineEmits<{ (e: 'dialog-open', v: boolean): void }>()

// ─── MAIN TABS ────────────────────────────────────────────────────────────────
const activeTab = ref<'dashboard' | 'customers'>('dashboard')

const mainTabs = [
  { key: 'dashboard' as const, label: 'Dashboard',    icon: LayoutDashboard },
  { key: 'customers' as const, label: 'My Customers', icon: Users           },
]

// ─── SELLING CYCLE TABS ───────────────────────────────────────────────────────
type CycleTab = 'quotation' | 'salesorder' | 'delivery' | 'invoice' | 'payment' | 'customer_ledger'

const activeCycleTab = ref<CycleTab | null>(null)

const cycleTabs: { key: CycleTab; label: string; shortLabel: string; icon: any }[] = [
  { key: 'quotation',       label: 'Quotation',       shortLabel: 'Quote',    icon: ClipboardList },
  { key: 'salesorder',      label: 'Sales Order',     shortLabel: 'SO',       icon: ShoppingCart  },
  { key: 'delivery',        label: 'Delivery Note',   shortLabel: 'Delivery', icon: Truck         },
  { key: 'invoice',         label: 'Sales Invoice',   shortLabel: 'Invoice',  icon: Receipt       },
  { key: 'payment',         label: 'Payment',         shortLabel: 'Payment',  icon: CreditCard    },
  { key: 'customer_ledger', label: 'Customer Ledger', shortLabel: 'Ledger',   icon: BookOpen      },
]

const currentCycleTab = computed(() =>
  activeCycleTab.value ? cycleTabs.find(t => t.key === activeCycleTab.value) : null
)

// ─── CUSTOMER SELECTED CHECK ──────────────────────────────────────────────────
const isCustomerSelected = computed(() => !!props.filters.customer)

// ─── FILTER STATE ─────────────────────────────────────────────────────────────
const activeFilter  = ref<'all' | 'subscription_pending' | 'daily' | 'normal'>('all')
const soFromDate    = ref<string>('')
const soToDate      = ref<string>('')
const hasDateFilter = computed(() => soFromDate.value !== '' || soToDate.value !== '')

function clearDateFilter() {
  soFromDate.value = ''
  soToDate.value   = ''
}

// ─── DIALOG / PROCESSING STATE ────────────────────────────────────────────────
const showDetail        = ref(false)
const showInvoiceDialog = ref(false)
const processingId      = ref('')
const processingSubId   = ref('')
const expandedSubId     = ref<string | null>(null)
const detailData        = ref<any>(null)

// Notify parent whenever ANY dialog opens/closes — used by SellerSidebar z-index fix
watch([showDetail, showInvoiceDialog], ([d, i]) => {
  emit('dialog-open', d || i)
})

// ─── RESOURCES ────────────────────────────────────────────────────────────────
const orders = createListResource({
  doctype: 'Sales Order',
  fields: [
    'name', 'customer', 'customer_name', 'status', 'grand_total', 'currency',
    'docstatus', 'per_delivered', 'per_billed', 'transaction_date',
    'custom_subscription_refereance'
  ],
  filters: {},
  orderBy: 'transaction_date desc',
  pageLength: 200,
  auto: true,
})

const orderDetails = createResource({
  url: 'frappe.client.get',
  makeParams: (values: { name: string }) => ({ doctype: 'Sales Order', name: values.name }),
  onSuccess(data: any) { detailData.value = data }
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

// ─── COMPUTED ─────────────────────────────────────────────────────────────────
const sellerName   = computed(() => props.filters.seller || '')
const customerName = computed(() => props.filters.customer || '')

const isNewspaperCategory = computed(() => {
  const cat = (props.filters.category || '').toLowerCase()
  return cat.includes('newspaper') || cat.includes('news paper')
})

const subscriptions = computed(() => {
  if (!customerName.value || !isNewspaperCategory.value) return []
  const all = (subsResource.data as any)?.subscriptions || []
  return all.filter((s: any) =>
    s.customer === customerName.value || s.customer_name === customerName.value
  )
})

const dateFilteredOrders = computed<any[]>(() => {
  const all = (orders.data || []) as any[]
  if (!hasDateFilter.value) return all
  return all.filter((o: any) => {
    const d = (o.transaction_date as string) || ''
    if (soFromDate.value && d < soFromDate.value) return false
    if (soToDate.value   && d > soToDate.value)   return false
    return true
  })
})

const combinedRows = computed<any[]>(() => {
  const rows: any[] = []
  const showSubscriptions = isNewspaperCategory.value && !!customerName.value

  if (showSubscriptions && (activeFilter.value === 'all' || activeFilter.value === 'subscription_pending')) {
    for (const sub of subscriptions.value) {
      if (activeFilter.value === 'subscription_pending' && sub.status !== 'Accept Pending') continue
      rows.push({ row_type: 'subscription', ...sub })
    }
  }
  if (activeFilter.value !== 'subscription_pending') {
    for (const o of dateFilteredOrders.value) {
      const isSubOrder = !!(o.custom_subscription_refereance)
      if (isSubOrder && !showSubscriptions) continue
      if (activeFilter.value === 'daily'  && !isSubOrder) continue
      if (activeFilter.value === 'normal' &&  isSubOrder) continue
      rows.push({ row_type: 'order', ...o })
    }
  }
  return rows
})

const filteredOrderCount = computed(() =>
  combinedRows.value.filter(r => r.row_type === 'order').length
)

const stats = computed(() => {
  const subs      = subscriptions.value as any[]
  const orderData = (orders.data || []) as any[]
  return {
    subPending:   subs.filter(s => s.status === 'Accept Pending').length,
    subActive:    subs.filter(s => s.status === 'Active').length,
    orderPending: orderData.filter(o => Number(o.docstatus) === 0 && !o.custom_subscription_refereance).length,
    toDeliver:    orderData.filter(o => Number(o.docstatus) === 1 && Number(o.per_delivered ?? 0) < 100).length,
    completed:    orderData.filter(o => Number(o.per_delivered ?? 0) >= 100).length,
  }
})

// null-safe for Frappe Cloud — per_delivered/per_billed can arrive as null/string
const eligibleForInvoice = computed(() =>
  ((orders.data || []) as any[]).filter(
    o =>
      Number(o.docstatus) === 1 &&
      Number(o.per_delivered ?? 0) > 0 &&
      Number(o.per_billed ?? 100) < 100
  )
)

const isCycleLoading = computed(() =>
  activeCycleTab.value === 'salesorder'
    ? (subsResource.loading || orders.loading)
    : false
)

// ─── WATCHERS ─────────────────────────────────────────────────────────────────
watch(
  () => [props.filters.customer, props.filters.seller] as const,
  ([customer, seller]) => {
    if (customer) { orders.update({ filters: { customer } }); orders.reload() }
    if (seller)   subsResource.fetch({ seller })
  },
  { immediate: true }
)

// ─── HELPERS ──────────────────────────────────────────────────────────────────
type BadgeTheme = 'gray' | 'blue' | 'green' | 'red' | 'orange'
function getStatusTheme(status: string): BadgeTheme {
  if (['Completed', 'To Bill', 'To Deliver'].includes(status)) return 'green'
  if (status === 'Draft')     return 'red'
  if (status === 'Cancelled') return 'gray'
  return 'orange'
}

function formatCurrency(amount: number, currency = 'INR'): string {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount)
}

// ─── ACTIONS ──────────────────────────────────────────────────────────────────
function openOrder(row: any) {
  detailData.value = null
  showDetail.value = true
  orderDetails.fetch({ name: row.name })
}

async function runOrderAction(id: string, action: string) {
  processingId.value = id
  try {
    const res = await orderWorkflow.submit({ order_id: id, action })
    if (res?.status === 'success') {
      showToast(res.message, 'success')
      await orders.reload()
      if (showDetail.value) orderDetails.fetch({ name: id })
    } else {
      showToast(res?.message || 'Operation Failed', 'error')
    }
  } catch (err: any) {
    showToast(err?.message || 'System Error', 'error')
  } finally {
    processingId.value = ''
  }
}

function runSubAction(subName: string, action: 'accept' | 'reject') {
  processingSubId.value = subName
  processSubResource.fetch({ sub_name: subName, action })
}

function toggleSubExpand(id: string) {
  expandedSubId.value = expandedSubId.value === id ? null : id
}

function refreshCycleTab() {
  activeCycleTab.value = null
  subsResource.fetch({ seller: sellerName.value })
  orders.reload()
}

function onInvoiceCreated(invoiceName: string) {
  showToast(`Invoice ${invoiceName} created successfully!`, 'success')
  orders.reload()
}

function createNewSalesOrder() {
  // Navigate / emit as needed by your router
}
</script>

<template>
  <div
    class="w-full min-w-0 max-w-7xl mx-auto font-sans text-gray-900
           px-0 sm:px-4 md:px-6
           pt-[env(safe-area-inset-top,0px)]
           pb-[calc(120px+env(safe-area-inset-bottom,0px))]
           sm:pb-[env(safe-area-inset-bottom,16px)]
           space-y-3 sm:space-y-4 md:space-y-5"
  >

    <!-- ══ TOP BAR — desktop only ══ -->
    <div class="hidden sm:flex items-center justify-between gap-2 pt-1 flex-wrap">
      <div class="flex gap-1 bg-gray-100 p-1 rounded-xl">
        <button
          v-for="tab in mainTabs"
          :key="tab.key"
          @click="activeTab = tab.key"
          :class="[
            'flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-all whitespace-nowrap',
            activeTab === tab.key
              ? 'bg-gray-900 text-white shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          ]"
        >
          <component :is="tab.icon" class="w-4 h-4 flex-shrink-0" />
          {{ tab.label }}
        </button>
      </div>

      <Button
        variant="outline" size="sm"
        :loading="subsResource.loading || orders.loading"
        class="text-sm"
        @click="refreshCycleTab"
      >
        <template #prefix><RefreshCcw class="w-4 h-4" /></template>
        Refresh
      </Button>
    </div>

    <!-- ══ DASHBOARD TAB ══ -->
    <template v-if="activeTab === 'dashboard'">

      <div class="px-2 sm:px-0">
        <SellerStatsCards
          :stats="stats"
          :active-filter="activeFilter"
          @update:active-filter="activeFilter = ($event as any)"
        />
      </div>

      <!-- Selling Cycle card -->
      <div class="bg-white border-y sm:border border-gray-100 sm:rounded-2xl shadow-sm overflow-hidden w-full min-w-0">

        <!-- NO CUSTOMER SELECTED -->
        <div
          v-if="!isCustomerSelected"
          class="flex flex-col items-center justify-center py-16 sm:py-24 text-center px-6"
        >
          <div class="p-4 bg-gray-100 rounded-2xl mb-4">
            <UserCheck class="w-10 h-10 text-gray-300" />
          </div>
          <p class="text-sm font-black text-gray-400">No Customer Selected</p>
          <p class="text-xs text-gray-300 mt-1.5 max-w-xs leading-relaxed">
            Select a customer from the sidebar to view their selling cycle — quotations, orders, deliveries, invoices and more.
          </p>
        </div>

        <!-- CUSTOMER SELECTED -->
        <template v-else>

          <!-- Desktop tab strip -->
          <div class="hidden sm:block border-b border-gray-100 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <div class="flex min-w-max">
              <button
                v-for="ctab in cycleTabs"
                :key="ctab.key"
                @click="activeCycleTab = ctab.key"
                :class="[
                  'relative flex items-center gap-2 px-5 md:px-7 py-3.5 text-sm font-bold transition-all whitespace-nowrap',
                  activeCycleTab === ctab.key
                    ? 'text-gray-900 bg-gray-50/80'
                    : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50/40'
                ]"
              >
                <span
                  v-if="activeCycleTab === ctab.key"
                  class="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gray-900 rounded-t-full"
                />
                <component :is="ctab.icon" class="w-4 h-4 flex-shrink-0" />
                {{ ctab.label }}
              </button>
            </div>
          </div>

          <!-- Mobile: current tab name -->
          <div
            v-if="currentCycleTab"
            class="sm:hidden flex items-center gap-2 px-3 py-2.5 border-b border-gray-100 bg-gray-50/60"
          >
            <component :is="currentCycleTab.icon" class="w-4 h-4 text-gray-700 flex-shrink-0" />
            <span class="text-sm font-black text-gray-800">{{ currentCycleTab.label }}</span>
          </div>

          <!-- No tab selected -->
          <div
            v-if="activeCycleTab === null"
            class="flex flex-col items-center justify-center py-16 sm:py-24 text-center px-6"
          >
            <div class="p-4 bg-gray-100 rounded-2xl mb-4">
              <ShoppingCart class="w-10 h-10 text-gray-300" />
            </div>
            <p class="text-sm font-black text-gray-400">Select a Tab</p>
            <p class="text-xs text-gray-300 mt-1.5">Choose a section above to get started.</p>
          </div>

          <!-- QUOTATION -->
          <template v-else-if="activeCycleTab === 'quotation'">
            <div class="flex flex-col items-center justify-center py-20 sm:py-28 text-center px-4">
              <div class="w-full flex justify-end px-3 pb-4">
                <button @click="refreshCycleTab" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-500 transition-all">
                  <RefreshCcw class="w-3.5 h-3.5" /> Refresh
                </button>
              </div>
              <div class="p-4 bg-gray-100 rounded-2xl mb-4"><ClipboardList class="w-10 h-10 text-gray-300" /></div>
              <p class="text-base font-black text-gray-300">Quotation</p>
              <p class="text-xs text-gray-300 mt-1">Coming soon</p>
            </div>
          </template>

          <!-- ══ SALES ORDER ══ -->
          <template v-else-if="activeCycleTab === 'salesorder'">
            <div class="border-b border-gray-100 bg-gray-50/60">

              <!-- Row A: Title + Buttons -->
              <div class="flex flex-wrap items-center gap-2 px-3 sm:px-5 pt-3 pb-2">
                <div class="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                  <div class="p-1.5 sm:p-2 bg-gray-900 rounded-lg sm:rounded-xl text-white shadow flex-shrink-0">
                    <ShoppingCart class="w-4 h-4 sm:w-5 sm:h-5" />
                  </div>
                  <div class="min-w-0">
                    <h2 class="text-sm sm:text-base font-black tracking-tight leading-tight">Sales Orders</h2>
                    <div class="flex items-center gap-1.5 flex-wrap mt-0.5">
                      <span class="text-[10px] sm:text-xs text-gray-400 font-medium">
                        <span v-if="activeFilter === 'all'">All — Subscriptions &amp; Orders</span>
                        <span v-else-if="activeFilter === 'subscription_pending'">Subscription Requests</span>
                        <span v-else-if="activeFilter === 'daily'">Daily Auto-Orders</span>
                        <span v-else-if="activeFilter === 'normal'">Normal Orders</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-1.5 flex-shrink-0 flex-wrap justify-end">

                  <!-- Create Sales Order -->
                  <button
                    @click="createNewSalesOrder"
                    class="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm transition-colors whitespace-nowrap shadow-sm"
                  >
                    <span class="flex items-center justify-center w-5 h-5 bg-white/20 rounded-md flex-shrink-0">
                      <Plus class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                    </span>
                    <span class="hidden sm:inline">Create Sales Order</span>
                    <span class="sm:hidden">New SO</span>
                  </button>

                  <!--
                    Create Invoice — ALWAYS visible (not v-if).
                    Green + clickable when eligible > 0.
                    Gray + disabled when eligible = 0.
                    Frappe Cloud pe per_delivered/per_billed null aaye toh bhi button dikh-ta rahega.
                  -->
                  <button
                    @click="eligibleForInvoice.length > 0 ? (showInvoiceDialog = true) : undefined"
                    :disabled="eligibleForInvoice.length === 0"
                    :class="[
                      'flex items-center gap-1.5 sm:gap-2 font-bold px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm transition-all whitespace-nowrap shadow-sm',
                      eligibleForInvoice.length > 0
                        ? 'bg-green-600 hover:bg-green-700 active:bg-green-800 text-white cursor-pointer'
                        : 'bg-gray-200 text-gray-400 cursor-not-allowed opacity-60'
                    ]"
                    :title="eligibleForInvoice.length === 0
                      ? 'No eligible orders to invoice'
                      : `${eligibleForInvoice.length} orders eligible`"
                  >
                    <span
                      :class="[
                        'flex items-center justify-center w-5 h-5 rounded-md flex-shrink-0',
                        eligibleForInvoice.length > 0 ? 'bg-white/20' : 'bg-gray-300/50'
                      ]"
                    >
                      <Receipt class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                    </span>
                    <span class="hidden sm:inline">Create Invoice</span>
                    <span class="sm:hidden">Invoice</span>
                    <span
                      :class="[
                        'text-[10px] font-black px-1.5 py-0.5 rounded-full leading-none',
                        eligibleForInvoice.length > 0
                          ? 'bg-white/25 text-white'
                          : 'bg-gray-300 text-gray-500'
                      ]"
                    >
                      {{ eligibleForInvoice.length }}
                    </span>
                  </button>

                  <button
                    v-if="activeFilter !== 'all'"
                    @click="activeFilter = 'all'"
                    class="flex items-center gap-1 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-gray-600 text-xs font-semibold px-2.5 py-2 rounded-lg transition-all whitespace-nowrap"
                  >
                    <XCircle class="w-3.5 h-3.5 flex-shrink-0" />
                    Clear
                  </button>

                  <button
                    @click="refreshCycleTab"
                    :class="[
                      'flex items-center gap-1.5 px-2.5 sm:px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-xs font-semibold text-gray-600 transition-all',
                      isCycleLoading ? 'opacity-60 pointer-events-none' : ''
                    ]"
                  >
                    <RefreshCcw :class="['w-3.5 h-3.5 flex-shrink-0', isCycleLoading ? 'animate-spin' : '']" />
                    <span class="hidden sm:inline">Refresh</span>
                  </button>
                </div>
              </div>

              <!-- Row B: Date filters -->
              <div class="flex flex-wrap items-center gap-2 px-3 sm:px-5 pb-3">
                <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 flex-shrink-0">
                  <span class="text-[9px] sm:text-[10px] font-bold text-gray-400 uppercase tracking-wide whitespace-nowrap select-none">From</span>
                  <input
                    type="date" v-model="soFromDate" :max="soToDate || undefined"
                    class="text-[10px] sm:text-xs font-semibold text-gray-700 bg-transparent outline-none border-none w-[108px] sm:w-[122px] cursor-pointer"
                  />
                  <button v-if="soFromDate" @click.prevent="soFromDate = ''" class="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0 ml-0.5">
                    <XCircle class="w-3 h-3" />
                  </button>
                </div>

                <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 flex-shrink-0">
                  <span class="text-[9px] sm:text-[10px] font-bold text-gray-400 uppercase tracking-wide whitespace-nowrap select-none">To</span>
                  <input
                    type="date" v-model="soToDate" :min="soFromDate || undefined"
                    class="text-[10px] sm:text-xs font-semibold text-gray-700 bg-transparent outline-none border-none w-[108px] sm:w-[122px] cursor-pointer"
                  />
                  <button v-if="soToDate" @click.prevent="soToDate = ''" class="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0 ml-0.5">
                    <XCircle class="w-3 h-3" />
                  </button>
                </div>

                <button
                  v-if="hasDateFilter" @click="clearDateFilter"
                  class="flex items-center gap-1 text-[10px] font-bold text-red-500 bg-red-50 border border-red-100 px-2 py-1.5 rounded-lg hover:bg-red-100 transition-all whitespace-nowrap"
                >
                  <XCircle class="w-3 h-3" /> Clear Dates
                </button>

                <span v-if="hasDateFilter" class="text-[10px] text-gray-400 font-semibold">
                  {{ filteredOrderCount }} orders
                </span>
              </div>
            </div>

            <SalesOrder
              :combined-rows="combinedRows"
              :loading="subsResource.loading || orders.loading"
              :active-filter="activeFilter"
              :expanded-sub-id="expandedSubId"
              :processing-sub-id="processingSubId"
              :processing-id="processingId"
              :format-currency="formatCurrency"
              :get-status-theme="getStatusTheme"
              @toggle-sub-expand="toggleSubExpand"
              @sub-action="runSubAction"
              @open-order-detail="openOrder"
              @order-action="runOrderAction"
              @show-all="activeFilter = 'all'"
            />
          </template>

          <!-- DELIVERY NOTE -->
          <template v-else-if="activeCycleTab === 'delivery'">
            <Deliverynote :customer="customerName" :seller="sellerName" :format-currency="formatCurrency" />
          </template>

          <!-- SALES INVOICE -->
          <template v-else-if="activeCycleTab === 'invoice'">
            <SalesInvoiceList :customer="customerName" :seller="sellerName" :format-currency="formatCurrency" />
          </template>

       <template v-else-if="activeCycleTab === 'payment'">
            <PaymentEntryList
              :customer="customerName"
              :seller="sellerName"
              :format-currency="formatCurrency"
            />
          </template>

          <!-- CUSTOMER LEDGER (coming soon) -->
          <template v-else-if="activeCycleTab === 'customer_ledger'">
            <div class="flex flex-col items-center justify-center py-20 sm:py-28 text-center px-4">
              <div class="w-full flex justify-end px-3 pb-4">
                <button @click="refreshCycleTab" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-500 transition-all">
                  <RefreshCcw class="w-3.5 h-3.5" /> Refresh
                </button>
              </div>
              <div class="p-4 bg-gray-100 rounded-2xl mb-4"><BookOpen class="w-10 h-10 text-gray-300" /></div>
              <p class="text-base font-black text-gray-300">Customer Ledger</p>
              <p class="text-xs text-gray-300 mt-1">Coming soon</p>
            </div>
          </template>

        </template>
      </div>
    </template>

    <!-- ══ CUSTOMERS TAB ══ -->
    <template v-if="activeTab === 'customers'">
      <div class="px-2 sm:px-0">
        <SellerCustomersTab :seller="sellerName" />
      </div>
    </template>

    <!-- ── DIALOGS ── -->
    <SellerOrderDetailDialog
      v-model="showDetail"
      :order-details="detailData"
      :processing-id="processingId"
      :format-currency="formatCurrency"
      :get-status-theme="getStatusTheme"
      @order-action="runOrderAction"
    />

    <SellerCreateInvoiceDialog
      v-model="showInvoiceDialog"
      :eligible-orders="eligibleForInvoice"
      :seller="sellerName"
      :format-currency="formatCurrency"
      @invoice-created="onInvoiceCreated"
    />

  </div>

  <!-- ══ MOBILE BOTTOM NAV ══ -->
  <nav
    class="sm:hidden fixed bottom-0 left-0 right-0 z-50
           bg-white/96 backdrop-blur-xl
           border-t border-gray-200
           pb-[env(safe-area-inset-bottom,0px)]
           shadow-[0_-4px_32px_rgba(0,0,0,0.10)]"
    style="will-change: transform;"
  >
    <div class="flex border-b border-gray-100">
      <button
        v-for="mtab in mainTabs"
        :key="mtab.key"
        @click="activeTab = mtab.key"
        :class="[
          'flex-1 flex flex-col items-center justify-center gap-0.5 py-2 px-1 text-[10px] font-bold transition-all active:scale-95',
          activeTab === mtab.key ? 'text-gray-900' : 'text-gray-400'
        ]"
      >
        <div :class="['p-1.5 rounded-xl transition-all', activeTab === mtab.key ? 'bg-gray-900 text-white' : 'text-gray-400']">
          <component :is="mtab.icon" class="w-4 h-4" />
        </div>
        {{ mtab.label }}
      </button>
    </div>

    <div
      v-if="activeTab === 'dashboard' && isCustomerSelected"
      class="flex overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden overscroll-x-contain"
    >
      <button
        v-for="ctab in cycleTabs"
        :key="ctab.key"
        @click="activeCycleTab = ctab.key"
        :class="[
          'relative flex-shrink-0 flex flex-col items-center justify-center gap-0.5',
          'px-3 py-2 min-w-[58px] text-[9px] font-bold transition-all active:scale-95',
          activeCycleTab === ctab.key ? 'text-gray-900' : 'text-gray-400'
        ]"
      >
        <span
          v-if="activeCycleTab === ctab.key"
          class="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-[2px] bg-gray-900 rounded-b-full"
        />
        <component
          :is="ctab.icon"
          :class="['w-[18px] h-[18px] transition-all', activeCycleTab === ctab.key ? 'text-gray-900' : 'text-gray-400']"
        />
        <span class="leading-tight text-center whitespace-nowrap">{{ ctab.shortLabel }}</span>
      </button>
    </div>

    <div
      v-else-if="activeTab === 'dashboard' && !isCustomerSelected"
      class="flex items-center justify-center py-2 px-4"
    >
      <p class="text-[9px] text-gray-300 font-medium">Select a customer to view selling cycle</p>
    </div>
  </nav>

</template>
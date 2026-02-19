<script setup lang="ts">
import { ref, watch, computed, inject } from 'vue'
import { createListResource, createResource, Button } from 'frappe-ui'
import {
  LayoutDashboard, Users, RefreshCcw, XCircle, Receipt
} from 'lucide-vue-next'

import SellerStatsCards          from '@/components/Seller/SellerStatsCards.vue'
import SellerCombinedList        from '@/components/Seller/SellerCombinedList.vue'
import SellerOrderDetailDialog   from '@/components/Seller/SellerOrderDetailDialog.vue'
import SellerCustomersTab        from '@/components/Seller/SellerCustomersTab.vue'
import SellerCreateInvoiceDialog from '@/components/Seller/SellerCreateInvoiceDialog.vue'

// ─── PROPS / INJECT ───
const props = defineProps<{ filters: { customer?: string; seller?: string } }>()
const showToast = inject('showToast') as (msg: string, type?: 'success' | 'error') => void

// ─── TABS ───
const activeTab = ref<'dashboard' | 'customers'>('dashboard')

// ─── FILTER ───
const activeFilter = ref<'all' | 'subscription_pending' | 'daily' | 'normal'>('all')

// ─── DIALOG / PROCESSING STATE ───
const showDetail        = ref(false)
const showInvoiceDialog = ref(false)
const processingId      = ref('')
const processingSubId   = ref('')
const expandedSubId     = ref<string | null>(null)
const detailData        = ref<any>(null)

// ─── RESOURCES ───
const orders = createListResource({
  doctype: 'Sales Order',
  // orders createListResource mein fields array mein 'customer' add karo
fields: [
  'name', 'customer', 'customer_name', 'status', 'grand_total', 'currency',  // 'customer' ADD KIYA
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

// ─── COMPUTED ───
const sellerName    = computed(() => props.filters.seller || '')
const subscriptions = computed(() => (subsResource.data as any)?.subscriptions || [])

const combinedRows = computed(() => {
  const rows: any[] = []
  if (activeFilter.value === 'all' || activeFilter.value === 'subscription_pending') {
    for (const sub of subscriptions.value) {
      if (activeFilter.value === 'subscription_pending' && sub.status !== 'Accept Pending') continue
      rows.push({ row_type: 'subscription', ...sub })
    }
  }
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

const stats = computed(() => {
  const subs      = subscriptions.value
  const orderData = (orders.data || []) as any[]
  return {
    subPending:   subs.filter((s: any) => s.status === 'Accept Pending').length,
    subActive:    subs.filter((s: any) => s.status === 'Active').length,
    orderPending: orderData.filter((o: any) => o.docstatus === 0 && !o.custom_subscription_refereance).length,
    toDeliver:    orderData.filter((o: any) => o.docstatus === 1 && o.per_delivered < 100).length,
    completed:    orderData.filter((o: any) => o.per_delivered >= 100).length,
  }
})

const eligibleForInvoice = computed(() =>
  ((orders.data || []) as any[]).filter(
    (o: any) => o.docstatus === 1 && o.per_delivered > 0 && o.per_billed < 100
  )
)

// ─── WATCHERS ───
watch(
  () => [props.filters.customer, props.filters.seller],
  ([customer, seller]) => {
    if (customer) { orders.update({ filters: { customer } }); orders.reload() }
    if (seller)   subsResource.fetch({ seller })
  },
  { immediate: true }
)

// ─── HELPERS ───
type BadgeTheme = 'gray' | 'blue' | 'green' | 'red' | 'orange'
const getStatusTheme = (status: string): BadgeTheme => {
  if (['Completed', 'To Bill', 'To Deliver'].includes(status)) return 'green'
  if (status === 'Draft') return 'red'
  if (status === 'Cancelled') return 'gray'
  return 'orange'
}

const formatCurrency = (amount: number, currency = 'INR') =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount)

// ─── ACTIONS ───
const openOrder = (row: any) => {
  detailData.value = null
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

const runSubAction = (subName: string, action: 'accept' | 'reject') => {
  processingSubId.value = subName
  processSubResource.fetch({ sub_name: subName, action })
}

const toggleSubExpand = (id: string) => {
  expandedSubId.value = expandedSubId.value === id ? null : id
}

const refreshAll = () => {
  subsResource.fetch({ seller: sellerName.value })
  orders.reload()
}

const onInvoiceCreated = (invoiceName: string) => {
  showToast(`Invoice ${invoiceName} created successfully!`, 'success')
  orders.reload()
}
</script>

<template>
  <div class="space-y-4 sm:space-y-5 md:space-y-6 max-w-7xl mx-auto px-3 sm:px-4 md:px-6 pb-10 font-sans text-gray-900">

    <!-- ── TABS + ACTIONS ROW ── -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">

      <!-- Tab switcher — full width on mobile -->
      <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-full sm:w-auto">
        <button
          @click="activeTab = 'dashboard'"
          :class="[
            'flex items-center justify-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-bold transition-all flex-1 sm:flex-none',
            activeTab === 'dashboard'
              ? 'bg-gray-900 text-white shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          ]"
        >
          <LayoutDashboard class="w-3.5 h-3.5 sm:w-4 sm:h-4 flex-shrink-0" />
          Dashboard
        </button>
        <button
          @click="activeTab = 'customers'"
          :class="[
            'flex items-center justify-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-bold transition-all flex-1 sm:flex-none',
            activeTab === 'customers'
              ? 'bg-gray-900 text-white shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          ]"
        >
          <Users class="w-3.5 h-3.5 sm:w-4 sm:h-4 flex-shrink-0" />
          My Customers
        </button>
      </div>

      <!-- Right actions -->
      <div class="flex items-center gap-2 sm:gap-3 self-end sm:self-auto flex-shrink-0">
        <transition
          enter-active-class="transition-all duration-200 ease-out"
          enter-from-class="opacity-0 scale-95 translate-y-1"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition-all duration-150 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <Button
            v-if="eligibleForInvoice.length > 0 && activeTab === 'dashboard'"
            variant="solid"
            theme="green"
            size="md"
            class="text-xs sm:text-sm"
            @click="showInvoiceDialog = true"
          >
            <template #prefix>
              <Receipt class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </template>
            <!-- Full label on sm+, short on mobile -->
            <span class="hidden sm:inline">Create Invoice</span>
            <span class="sm:hidden">Invoice</span>
            <span
              class="ml-1.5 sm:ml-2 bg-green-400 text-green-900 text-[10px] sm:text-xs font-black
                     px-1.5 sm:px-2 py-0.5 rounded-full leading-none"
            >
              {{ eligibleForInvoice.length }}
            </span>
          </Button>
        </transition>

        <Button
          variant="outline"
          :loading="subsResource.loading || orders.loading"
          class="text-xs sm:text-sm"
          @click="refreshAll"
        >
          <template #prefix>
            <RefreshCcw class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </template>
          <!-- Icon only on very small, text on sm+ -->
          <span class="hidden sm:inline">Refresh</span>
        </Button>
      </div>
    </div>

    <!-- ════════════════════════════════ -->
    <!-- DASHBOARD TAB                   -->
    <!-- ════════════════════════════════ -->
    <template v-if="activeTab === 'dashboard'">

      <!-- Stats cards -->
      <SellerStatsCards
        :stats="stats"
        :active-filter="activeFilter"
        @update:active-filter="activeFilter = $event as any"
      />

      <!-- Header / sub-filter bar -->
      <div
        class="flex flex-col sm:flex-row sm:items-center justify-between bg-white
               p-3 sm:p-4 md:p-5 rounded-2xl sm:rounded-3xl border border-gray-100 shadow-sm gap-3"
      >
        <!-- Left: icon + title -->
        <div class="flex items-center gap-3 min-w-0">
          <div class="p-2 sm:p-3 bg-gray-900 rounded-xl sm:rounded-2xl text-white shadow-lg ring-4 ring-gray-50 flex-shrink-0">
            <LayoutDashboard class="w-4 h-4 sm:w-6 sm:h-6" />
          </div>
          <div class="min-w-0">
            <h2 class="text-base sm:text-2xl font-black tracking-tight leading-tight">Seller Operations</h2>
            <p class="text-xs sm:text-sm text-gray-500 font-medium truncate">
              <span v-if="activeFilter === 'all'">All — Subscriptions & Orders</span>
              <span v-else-if="activeFilter === 'subscription_pending'">Showing: Subscription Requests</span>
              <span v-else-if="activeFilter === 'daily'">Showing: Daily Auto-Orders</span>
              <span v-else-if="activeFilter === 'normal'">Showing: Normal Orders</span>
            </p>
          </div>
        </div>

        <!-- Right: chips -->
        <div class="flex items-center gap-2 flex-wrap self-start sm:self-auto">
          <div
            v-if="eligibleForInvoice.length > 0"
            class="flex items-center gap-1.5 bg-emerald-50 border border-emerald-100
                   text-emerald-700 text-[10px] sm:text-xs font-semibold
                   px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-lg sm:rounded-xl
                   cursor-pointer hover:bg-emerald-100 transition-all whitespace-nowrap"
            @click="showInvoiceDialog = true"
          >
            <Receipt class="w-3 h-3 sm:w-3.5 sm:h-3.5 flex-shrink-0" />
            {{ eligibleForInvoice.length }} order{{ eligibleForInvoice.length > 1 ? 's' : '' }} ready to invoice
          </div>

          <button
            v-if="activeFilter !== 'all'"
            @click="activeFilter = 'all'"
            class="flex items-center gap-1 sm:gap-1.5 bg-gray-100 hover:bg-gray-200 text-gray-600
                   text-[10px] sm:text-xs font-semibold px-2.5 sm:px-3 py-1.5 rounded-lg sm:rounded-xl
                   transition-all whitespace-nowrap"
          >
            <XCircle class="w-3 h-3 sm:w-3.5 sm:h-3.5 flex-shrink-0" />
            Clear Filter
          </button>
        </div>
      </div>

      <!-- Combined list -->
      <SellerCombinedList
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

    <!-- ════════════════════════════════ -->
    <!-- CUSTOMERS TAB                   -->
    <!-- ════════════════════════════════ -->
    <template v-if="activeTab === 'customers'">
      <SellerCustomersTab :seller="sellerName" />
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
</template>
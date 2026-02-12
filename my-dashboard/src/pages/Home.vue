<script setup lang="ts">
import { ref, watch, computed } from 'vue'
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
  Check,
  ChevronRight,
  Clock,
  CheckCircle,
  AlertCircle
} from 'lucide-vue-next'

// Global Frappe Object
declare const frappe: any;

const props = defineProps<{ filters: { customer?: string } }>()

// --- RESOURCES ---

// 1. List Resource
const orders = createListResource({
  doctype: 'Sales Order',
  fields: ['name', 'customer_name', 'status', 'grand_total', 'currency', 'docstatus', 'per_delivered', 'per_billed', 'transaction_date'],
  orderBy: 'creation desc',
  pageLength: 100, // Fetch more items for better counts
  auto: false,
})

// 2. Single Order Details
const orderDetails = createResource({
  url: 'frappe.client.get',
  makeParams(values: { name: string }) {
    return { doctype: 'Sales Order', name: values.name }
  },
})

// 3. Workflow Action
const workflow = createResource({ url: 'my_frappe_app.api.process_order_workflow' })

// --- STATE ---
const showDetail = ref(false)
const processingId = ref('')

// --- COMPUTED STATS (Counts Logic) ---
const stats = computed(() => {
  const data = orders.data || []
  return {
    pending: data.filter((o: any) => o.docstatus === 0).length,
    toDeliver: data.filter((o: any) => o.docstatus === 1 && o.per_delivered < 100).length,
    completed: data.filter((o: any) => o.per_delivered >= 100).length
  }
})

// Watch Filters
watch(() => props.filters.customer, (val) => {
  if (val) {
    orders.update({ filters: { customer: val } })
    orders.reload()
  }
}, { immediate: true })

// --- ACTIONS ---

const openOrder = (row: any) => {
  showDetail.value = true
  orderDetails.fetch({ name: row.name })
}

const runAction = async (id: string, action: string) => {
  processingId.value = id
  try {
    const res = await workflow.submit({ order_id: id, action })
    if (res?.status === 'success') {
      orders.reload()
      if (showDetail.value) orderDetails.fetch({ name: id })
      frappe.show_alert({ message: res.message, indicator: 'green' })
    } else {
      frappe.show_alert({ message: res?.message || 'Operation Failed', indicator: 'red' })
    }
  } catch (error: any) {
    frappe.show_alert({ message: error?.message || "System Error", indicator: 'red' })
  } finally {
    processingId.value = ''
  }
}

// Helpers
const getStatusTheme = (status: string) => {
  if (['Completed', 'To Bill', 'To Deliver'].includes(status)) return 'green'
  if (status === 'Draft') return 'red'
  if (status === 'Cancelled') return 'gray'
  return 'orange'
}

const formatCurrency = (amount: number, currency: string) => {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: currency }).format(amount)
}
</script>

<template>
  <div class="space-y-6 max-w-7xl mx-auto pb-10 font-sans">
    <div v-if="filters.customer" class="grid grid-cols-1 md:grid-cols-3 gap-6">

      <div
        class="bg-white p-5 rounded-3xl border border-orange-100 shadow-sm flex items-center justify-between group hover:border-orange-300 transition-all">
        <div>
          <p class="text-xs font-bold text-orange-400 uppercase tracking-widest mb-1">To Accept</p>
          <p class="text-3xl font-black text-gray-900">{{ stats.pending }}</p>
        </div>
        <div
          class="h-12 w-12 rounded-2xl bg-orange-50 flex items-center justify-center text-orange-500 group-hover:bg-orange-500 group-hover:text-white transition-colors">
          <Clock class="w-6 h-6" />
        </div>
      </div>

      <div
        class="bg-white p-5 rounded-3xl border border-blue-100 shadow-sm flex items-center justify-between group hover:border-blue-300 transition-all">
        <div>
          <p class="text-xs font-bold text-blue-400 uppercase tracking-widest mb-1">To Deliver</p>
          <p class="text-3xl font-black text-gray-900">{{ stats.toDeliver }}</p>
        </div>
        <div
          class="h-12 w-12 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-500 group-hover:bg-blue-600 group-hover:text-white transition-colors">
          <Truck class="w-6 h-6" />
        </div>
      </div>

      <div
        class="bg-white p-5 rounded-3xl border border-green-100 shadow-sm flex items-center justify-between group hover:border-green-300 transition-all">
        <div>
          <p class="text-xs font-bold text-green-500 uppercase tracking-widest mb-1">Completed</p>
          <p class="text-3xl font-black text-gray-900">{{ stats.completed }}</p>
        </div>
        <div
          class="h-12 w-12 rounded-2xl bg-green-50 flex items-center justify-center text-green-600 group-hover:bg-green-600 group-hover:text-white transition-colors">
          <CheckCircle class="w-6 h-6" />
        </div>
      </div>
    </div>
    <div class="flex justify-between items-center bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
      <div class="flex items-center gap-4">
        <div class="p-3 bg-gray-900 rounded-2xl text-white shadow-lg ring-4 ring-gray-50">
          <LayoutDashboard class="w-6 h-6" />
        </div>
        <div>
          <h2 class="text-2xl font-black text-gray-900 tracking-tight">Seller Operations</h2>
          <p class="text-sm text-gray-500 font-medium">Overview & Management</p>
        </div>
      </div>
      <Button variant="outline" @click="orders.reload()" :loading="orders.loading">
        <template #prefix>
          <RefreshCcw class="w-4 h-4" />
        </template> Refresh
      </Button>
    </div>



    <div
      class="bg-white rounded-[2rem] border border-gray-100 shadow-xl shadow-gray-100/50 overflow-hidden min-h-[500px]">

      <div v-if="!filters.customer" class="flex flex-col items-center justify-center py-40">
        <div class="bg-blue-50 p-6 rounded-full mb-4">
          <User class="w-12 h-12 text-blue-500" />
        </div>
        <h3 class="text-lg font-bold text-gray-900">No Customer Selected</h3>
        <p class="text-gray-400">Please select a customer from the sidebar.</p>
      </div>

      <div v-else-if="orders.loading" class="flex flex-col items-center justify-center py-40">
        <LoadingIndicator class="w-8 h-8 mb-4 text-blue-600" />
        <p class="text-gray-400 font-medium animate-pulse">Fetching Orders...</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead class="bg-gray-50/80 border-b border-gray-100">
            <tr>
              <th class="px-8 py-5 text-xs font-bold text-gray-400 uppercase tracking-wider">Order Info</th>
              <th class="px-6 py-5 text-xs font-bold text-gray-400 uppercase tracking-wider">Status</th>
              <th class="px-6 py-5 text-xs font-bold text-gray-400 uppercase tracking-wider">Amount</th>
              <th class="px-6 py-5 text-xs font-bold text-gray-400 uppercase tracking-wider text-right">Quick Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="row in orders.data" :key="row.name" @click="openOrder(row)"
              class="hover:bg-blue-50/40 cursor-pointer group transition-all duration-200">
              <td class="px-8 py-5">
                <div class="flex items-center gap-3">
                  <div
                    class="p-2 bg-gray-100 rounded-lg text-gray-500 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">
                    <ShoppingBag class="w-5 h-5" />
                  </div>
                  <div>
                    <p class="font-bold text-gray-900 group-hover:text-blue-600 transition-colors">{{ row.name }}</p>
                    <p class="text-xs text-gray-400 font-medium flex items-center gap-1">
                      <Calendar class="w-3 h-3" /> {{ row.transaction_date }}
                    </p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-5">
                <Badge :theme="getStatusTheme(row.status)" variant="subtle" :label="row.status" size="md" />
              </td>
              <td class="px-6 py-5 font-bold text-gray-700 font-mono">
                {{ formatCurrency(row.grand_total, row.currency) }}
              </td>
              <td class="px-6 py-5 text-right" @click.stop>
                <div class="flex items-center justify-end gap-2">
                  <Button v-if="row.docstatus === 0" variant="solid" theme="blue" :loading="processingId === row.name"
                    @click="runAction(row.name, 'accept')">
                    Accept
                  </Button>

                  <Button v-if="row.docstatus === 1 && row.per_delivered < 100" variant="subtle" theme="gray"
                    :loading="processingId === row.name" @click="runAction(row.name, 'deliver')">
                    <template #prefix>
                      <Truck class="w-4 h-4" />
                    </template> Deliver
                  </Button>

                  <Button v-if="row.per_delivered >= 100 && row.per_billed < 100" variant="subtle" theme="gray"
                    :loading="processingId === row.name" @click="runAction(row.name, 'invoice')">
                    <template #prefix>
                      <FileText class="w-4 h-4" />
                    </template> Invoice
                  </Button>

                  <ChevronRight class="w-5 h-5 text-gray-300 ml-2" />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Dialog v-model="showDetail" :options="{ size: '4xl' }">
      <template #body-title>
        <div class="flex items-center justify-between w-full pr-8">
          <div class="flex items-center gap-3">
            <div class="h-10 w-10 bg-blue-50 rounded-full flex items-center justify-center text-blue-600">
              <Package class="w-5 h-5" />
            </div>
            <div>
              <h3 class="text-xl font-black text-gray-900 leading-none">Order Details</h3>
              <p class="text-sm text-gray-500 font-mono mt-1">{{ orderDetails.data?.name }}</p>
            </div>
          </div>
          <Badge v-if="orderDetails.data" :theme="getStatusTheme(orderDetails.data.status)" size="lg"
            :label="orderDetails.data.status" />
        </div>
      </template>

      <template #body-content>
        <div class="min-h-[400px]">
          <div v-if="orderDetails.loading" class="flex flex-col items-center justify-center h-80">
            <LoadingIndicator class="w-10 h-10 text-blue-500" />
            <span class="text-gray-400 font-medium mt-4">Loading order details...</span>
          </div>

          <div v-else-if="orderDetails.data" class="py-6 space-y-8">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div class="bg-gray-50 p-5 rounded-2xl border border-gray-100 flex items-start gap-3">
                <div class="bg-white p-2 rounded-lg text-gray-500 shadow-sm">
                  <User class="w-4 h-4" />
                </div>
                <div>
                  <p class="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1">Customer</p>
                  <p class="font-bold text-gray-900 leading-tight">{{ orderDetails.data.customer_name }}</p>
                </div>
              </div>
              <div class="bg-gray-50 p-5 rounded-2xl border border-gray-100 flex items-start gap-3">
                <div class="bg-white p-2 rounded-lg text-gray-500 shadow-sm">
                  <Calendar class="w-4 h-4" />
                </div>
                <div>
                  <p class="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1">Date</p>
                  <p class="font-bold text-gray-900">{{ orderDetails.data.transaction_date }}</p>
                </div>
              </div>
              <div
                class="bg-blue-600 p-5 rounded-2xl border border-blue-500 text-white shadow-lg shadow-blue-200 flex items-center justify-between">
                <div>
                  <p class="text-[11px] font-bold text-blue-200 uppercase tracking-widest mb-1">Grand Total</p>
                  <p class="font-black text-2xl">{{ formatCurrency(orderDetails.data.grand_total,
                    orderDetails.data.currency) }}</p>
                </div>
                <div class="bg-white/20 p-2 rounded-lg">
                  <ShoppingBag class="w-5 h-5 text-white" />
                </div>
              </div>
            </div>

            <div>
              <h3 class="font-bold text-gray-900 mb-4 text-sm uppercase tracking-wide flex items-center gap-2">
                Items <span class="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs">{{
                  orderDetails.data.items.length }}</span>
              </h3>
              <div class="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                <table class="w-full text-sm">
                  <thead
                    class="bg-gray-50 border-b border-gray-200 text-gray-500 font-semibold uppercase text-[10px] tracking-wider">
                    <tr>
                      <th class="px-5 py-4 text-left">Item Description</th>
                      <th class="px-5 py-4 text-right">Quantity</th>
                      <th class="px-5 py-4 text-right">Rate</th>
                      <th class="px-5 py-4 text-right bg-gray-100/50">Amount</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="item in orderDetails.data.items" :key="item.name"
                      class="hover:bg-blue-50/20 transition-colors">
                      <td class="px-5 py-4">
                        <p class="font-bold text-gray-900 text-sm">{{ item.item_name }}</p>
                        <p class="text-xs text-gray-400 font-mono mt-0.5">{{ item.item_code }}</p>
                      </td>
                      <td class="px-5 py-4 text-right font-medium text-gray-700">{{ item.qty }}</td>
                      <td class="px-5 py-4 text-right text-gray-500 font-mono">{{ formatCurrency(item.rate,
                        orderDetails.data.currency) }}</td>
                      <td class="px-5 py-4 text-right font-bold text-gray-900 bg-gray-50/30 font-mono">{{
                        formatCurrency(item.amount, orderDetails.data.currency) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="flex items-center justify-between pt-6 border-t border-gray-100">
              <Button variant="subtle" @click="showDetail = false">Dismiss</Button>
              <div class="flex gap-3">
                <Button v-if="orderDetails.data.docstatus === 0" variant="solid" theme="blue" size="xl"
                  :loading="processingId === orderDetails.data.name"
                  @click="runAction(orderDetails.data.name, 'accept')">
                  <template #prefix>
                    <Check class="w-4 h-4" />
                  </template> Confirm & Accept Order
                </Button>
                <Button v-if="orderDetails.data.docstatus === 1 && orderDetails.data.per_delivered < 100"
                  variant="solid" theme="gray" size="xl" class="bg-gray-900 text-white hover:bg-gray-800 border-none"
                  :loading="processingId === orderDetails.data.name"
                  @click="runAction(orderDetails.data.name, 'deliver')">
                  <template #prefix>
                    <Truck class="w-4 h-4" />
                  </template> Generate Delivery Note
                </Button>
                <Button v-if="orderDetails.data.per_delivered >= 100 && orderDetails.data.per_billed < 100"
                  variant="solid" theme="gray" size="xl" class="bg-gray-900 text-white hover:bg-gray-800 border-none"
                  :loading="processingId === orderDetails.data.name"
                  @click="runAction(orderDetails.data.name, 'invoice')">
                  <template #prefix>
                    <FileText class="w-4 h-4" />
                  </template> Generate Invoice
                </Button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>
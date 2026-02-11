<script setup>
import { reactive, computed, ref } from 'vue'
import { createResource, Button, Badge, call, Dialog } from 'frappe-ui'
import { RefreshCcw, Check, Truck, FileText, ExternalLink, X } from 'lucide-vue-next'

// Modal State
const showOrderDialog = ref(false)
const selectedOrder = ref(null)

// 1. Data Fetching
const salesOrders = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Sales Order',
    fields: ['name', 'customer', 'status', 'grand_total', 'currency', 'docstatus', 'delivery_status', 'billing_status'],
    order_by: 'creation desc',
    limit: 20
  },
  auto: true,
})

// Fetch single order details
const orderDetails = createResource({
  url: 'frappe.client.get',
  makeParams(values) {
    return {
      doctype: 'Sales Order',
      name: values.name
    }
  }
})

// 2. Open Order Function - Show in modal
const openSalesOrder = async (row) => {
  if (!row || !row.name) return
  selectedOrder.value = row
  showOrderDialog.value = true
  // Fetch full details
  await orderDetails.fetch({ name: row.name })
}

// 3. Actions Logic
const handleAction = async (orderName, action) => {
  console.log('🔥 Action triggered:', action, 'for order:', orderName)
  try {
    if (action === 'submit') {
      console.log('📤 Submitting order...')
      // Submit the Sales Order using frappe.call with submitdoc
      const result = await call('frappe.client.set_value', {
        doctype: 'Sales Order',
        name: orderName,
        fieldname: 'docstatus',
        value: 1
      })
      console.log('✅ Order Submitted:', orderName, result)
      alert(`Order ${orderName} accepted successfully!`)
      salesOrders.reload()
      if (showOrderDialog.value) {
        await orderDetails.fetch({ name: orderName })
      }
    } else if (action === 'cancel') {
      console.log('❌ Cancelling order...')
      // Cancel the Sales Order
      const result = await call('frappe.client.set_value', {
        doctype: 'Sales Order',
        name: orderName,
        fieldname: 'docstatus',
        value: 2
      })
      console.log('✅ Order Cancelled:', orderName, result)
      alert(`Order ${orderName} rejected successfully!`)
      salesOrders.reload()
      if (showOrderDialog.value) {
        showOrderDialog.value = false
      }
    } else if (action === 'make_delivery_note') {
      // Open new Delivery Note from Sales Order
      window.open(`http://uvtech.com:8000/desk/delivery-note/new-delivery-note?source_name=${orderName}`, '_blank')
    } else if (action === 'make_sales_invoice') {
      // Open new Sales Invoice from Sales Order
      window.open(`http://uvtech.com:8000/desk/sales-invoice/new-sales-invoice?source_name=${orderName}`, '_blank')
    }
  } catch (e) {
    console.error('❌ Action Failed:', e)
    const errorMsg = e.messages ? e.messages.join('\n') : (e.message || JSON.stringify(e))
    alert(`Action failed: ${errorMsg}`)
  }
}
// 4. Columns - CRITICAL: Must be reactive for slots to work
const state = reactive({
  columns: [
    { label: 'Order ID', key: 'name', width: '180px' },
    { label: 'Customer', key: 'customer', width: '200px' },
    { label: 'Status', key: 'status', width: '150px' },
    { label: 'Actions', key: 'row_actions', width: '200px' }
  ]
})

const rows = computed(() => {
  if (!salesOrders.data) return []
  return salesOrders.data.map(row => ({
    ...row,
    id: row.name, // Keep id for keys if needed
    row_actions: 'FALLBACK' // Debug: If this appears, slot is IGNORED. If buttons appear or empty, slot is USED.
  }))
})
</script>

<template>
  <div class="p-5 h-screen bg-white flex flex-col overflow-hidden font-sans">

    <div class="flex justify-between items-center mb-6 px-2">
      <h1 class="text-2xl font-bold text-gray-900 leading-tight">Seller Dashboard</h1>
      <Button :loading="salesOrders.loading" @click="salesOrders.reload()">
        <template #icon>
          <RefreshCcw class="w-4 h-4" />
        </template>
        Refresh
      </Button>
    </div>

    <div class="flex-1 border rounded-lg shadow-sm overflow-hidden bg-white">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Order ID</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="row in rows" :key="row.name" class="hover:bg-gray-50 cursor-pointer"
              @click="openSalesOrder(row)">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ row.name }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ row.customer }}</td>
              <td class="px-6 py-4 whitespace-nowrap">
                <Badge variant="subtle" :color="row.status === 'Draft' ? 'red' : 'blue'">
                  {{ row.status }}
                </Badge>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium" @click.stop>
                <div class="flex gap-2 items-center">
                  <!-- Draft: Accept Order -->
                  <Button v-if="row.docstatus === 0" variant="solid" size="sm"
                    @click="handleAction(row.name, 'submit')">
                    Accept Order
                  </Button>

                  <!-- Draft: Reject/Cancel -->
                  <Button v-if="row.docstatus === 0" variant="subtle" theme="gray" size="sm"
                    @click="handleAction(row.name, 'cancel')">
                    Reject
                  </Button>

                  <!-- Submitted: Create Delivery -->
                  <Button v-if="row.docstatus === 1 && row.delivery_status !== 'Fully Delivered'" variant="outline"
                    size="sm" @click="handleAction(row.name, 'make_delivery_note')">
                    Create Delivery
                  </Button>

                  <!-- Submitted: Create Invoice -->
                  <Button v-if="row.docstatus === 1 && row.billing_status !== 'Fully Billed'" variant="outline"
                    size="sm" @click="handleAction(row.name, 'make_sales_invoice')">
                    Create Invoice
                  </Button>

                  <button @click="openSalesOrder(row)" class="p-1 hover:bg-gray-100 rounded transition-colors"
                    title="Open Sales Order">
                    <ExternalLink class="w-4 h-4 text-gray-400" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="4" class="px-6 py-10 text-center text-sm text-gray-500">
                <div class="flex flex-col items-center justify-center">
                  <span class="text-lg font-medium text-gray-900 mb-1">No Orders Found</span>
                  <span>New orders will appear here.</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Sales Order Details Modal -->
    <Dialog v-model="showOrderDialog" :options="{ size: '3xl' }">
      <template #body>
        <div class="p-6">
          <div class="flex justify-between items-start mb-6">
            <div>
              <h2 class="text-2xl font-bold text-gray-900">{{ selectedOrder?.name }}</h2>
              <p class="text-sm text-gray-500 mt-1">Customer: {{ selectedOrder?.customer }}</p>
            </div>
            <Badge variant="subtle" :color="selectedOrder?.status === 'Draft' ? 'red' : 'blue'">
              {{ selectedOrder?.status }}
            </Badge>
          </div>

          <div v-if="orderDetails.loading" class="text-center py-8">
            <p class="text-gray-500">Loading order details...</p>
          </div>

          <div v-else-if="orderDetails.data" class="space-y-6">
            <!-- Order Items -->
            <div>
              <h3 class="text-lg font-semibold mb-3">Items</h3>
              <div class="border rounded-lg overflow-hidden">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Item</th>
                      <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">Qty</th>
                      <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">Rate</th>
                      <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">Amount</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-200">
                    <tr v-for="item in orderDetails.data.items" :key="item.name">
                      <td class="px-4 py-2 text-sm">{{ item.item_name }}</td>
                      <td class="px-4 py-2 text-sm text-right">{{ item.qty }}</td>
                      <td class="px-4 py-2 text-sm text-right">{{ item.rate }}</td>
                      <td class="px-4 py-2 text-sm text-right font-medium">{{ item.amount }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Totals -->
            <div class="bg-gray-50 rounded-lg p-4 space-y-2">
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">Net Total:</span>
                <span class="font-medium">{{ orderDetails.data.currency }} {{ orderDetails.data.net_total }}</span>
              </div>
              <div class="flex justify-between text-lg font-bold border-t pt-2">
                <span>Grand Total:</span>
                <span>{{ orderDetails.data.currency }} {{ orderDetails.data.grand_total }}</span>
              </div>
            </div>

            <!-- Action Buttons in Modal -->
            <div class="flex gap-3 pt-4 border-t">
              <Button v-if="selectedOrder?.docstatus === 0" variant="solid"
                @click="handleAction(selectedOrder.name, 'submit')">
                Accept Order
              </Button>
              <Button v-if="selectedOrder?.docstatus === 0" variant="subtle" theme="gray"
                @click="handleAction(selectedOrder.name, 'cancel')">
                Reject
              </Button>
              <Button v-if="selectedOrder?.docstatus === 1" variant="outline"
                @click="handleAction(selectedOrder.name, 'make_delivery_note')">
                Create Delivery
              </Button>
              <Button v-if="selectedOrder?.docstatus === 1" variant="outline"
                @click="handleAction(selectedOrder.name, 'make_sales_invoice')">
                Create Invoice
              </Button>
              <Button variant="subtle" theme="gray" @click="showOrderDialog = false">
                Close
              </Button>
            </div>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
/* Force row to show pointer and fix visibility */
:deep(.frappe-list-row) {
  cursor: pointer !important;
}

:deep(.frappe-list-row:hover) {
  background-color: #f7fafc !important;
}
</style>
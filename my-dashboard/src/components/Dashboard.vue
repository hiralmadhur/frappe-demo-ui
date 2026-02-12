<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { createResource, Dialog, ListView, Badge, Button, Avatar } from 'frappe-ui'
import { Package, ChevronRight } from 'lucide-vue-next'


interface Customer { name: string; customer_name: string; image?: string }
interface Order { name: string; transaction_date: string; status: string; grand_total: number; currency: string }
interface ItemGroup { name: string; item_group_name: string }

const props = defineProps<{
  filters: { pincode?: string; society?: string }
}>()


const itemGroups = createResource({
  url: 'my_frappe_app.api.get_item_groups',
  auto: true
})

const customers = createResource({
  url: 'my_frappe_app.api.get_customers',
  makeParams(values: any) { return { pincode: values.pincode } }
})

const salesOrders = createResource({
  url: 'my_frappe_app.api.get_orders',
  makeParams(values: any) { return { customer: values.customer } }
})

// --- State ---
const showOrderDialog = ref(false)
const selectedCustomer = ref<Customer | null>(null)

// Watch for pincode changes from sidebar
watch(() => props.filters?.pincode, (newPin) => {
  if (newPin) customers.fetch({ pincode: newPin })
}, { immediate: true })

const orderColumns = [
  { label: 'Date', key: 'transaction_date', width: '120px' },
  { label: 'ID', key: 'name', width: '150px' },
  { label: 'Status', key: 'status', width: '120px' },
  { label: 'Total', key: 'grand_total', width: '120px', align: 'right' }
]

const openOrders = (customer: Customer) => {
  selectedCustomer.value = customer
  salesOrders.fetch({ customer: customer.name })
  showOrderDialog.value = true
}
</script>

<template>
  <div class="p-4 sm:p-6 space-y-8 max-w-7xl mx-auto">
    
    <section>
      <h2 class="text-lg font-bold text-gray-900 mb-4">Categories</h2>
      <div v-if="itemGroups.loading" class="text-sm text-gray-400">Loading...</div>
      <div v-else class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div 
          v-for="group in (itemGroups.data as ItemGroup[])" 
          :key="group.name"
          class="flex flex-col items-center justify-center p-4 bg-white border border-gray-200 rounded-lg hover:shadow-sm cursor-pointer h-24"
        >
          <Package class="w-6 h-6 text-gray-400 mb-2" />
          <span class="text-xs font-medium text-gray-700 text-center truncate w-full">
            {{ group.item_group_name }}
          </span>
        </div>
      </div>
    </section>

    <div class="border-t border-gray-100"></div>

    <section>
      <h2 class="text-lg font-bold text-gray-900 mb-4">
        Customers <span v-if="props.filters?.pincode" class="text-sm font-normal text-gray-500">({{ props.filters.pincode }})</span>
      </h2>

      <div v-if="!props.filters?.pincode" class="p-10 border border-dashed rounded-lg bg-gray-50 text-center text-gray-500">
        Please select a Pincode from the sidebar.
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div 
          v-for="cust in (customers.data as Customer[])" 
          :key="cust.name"
          @click="openOrders(cust)"
          class="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:border-gray-900 transition-colors cursor-pointer"
        >
          <div class="flex items-center gap-3">
            <Avatar :label="cust.customer_name" :image="cust.image" size="lg" />
            <div>
              <div class="font-semibold text-gray-900">{{ cust.customer_name }}</div>
              <div class="text-xs text-gray-400">{{ cust.name }}</div>
            </div>
          </div>
          <ChevronRight class="w-5 h-5 text-gray-300" />
        </div>
      </div>
    </section>

    <Dialog v-model="showOrderDialog" :options="{ size: '3xl' }">
      <template #body-title>
        <div class="text-xl font-bold">Orders - {{ selectedCustomer?.customer_name }}</div>
      </template>

      <template #body-content>
        <div class="min-h-[200px] mt-4">
          <div v-if="salesOrders.loading" class="text-gray-500">Loading...</div>
          <ListView
            v-else-if="salesOrders.data?.length"
            :columns="orderColumns"
            :rows="salesOrders.data"
            row-key="name"
          >
            <template #cell-status="{ row }">
              <Badge 
                :label="(row as Order).status"
                :theme="(row as Order).status === 'Completed' ? 'green' : 'orange'"
              />
            </template>
            <template #cell-grand_total="{ row }">
               {{ (row as Order).currency }} {{ (row as Order).grand_total.toLocaleString() }}
            </template>
          </ListView>
          <div v-else class="text-gray-500 py-10 text-center">No orders found.</div>
        </div>
      </template>
    </Dialog>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Button, Badge, Dialog } from 'frappe-ui'
import {
  ClipboardList, Store, Package, CheckCircle, XCircle,
  Clock, Truck, FileText, Newspaper, ChevronDown, ChevronUp
} from 'lucide-vue-next'

const props = defineProps<{
  orders: any[]
  loading: boolean
  cancelLoading: boolean
}>()

const emit = defineEmits<{
  (e: 'cancel-order', orderId: string): void
  (e: 'go-shop'): void
}>()

const expandedOrder     = ref<string | null>(null)
const cancelConfirmOpen = ref(false)
const cancelTargetOrder = ref<string | null>(null)

type BadgeTheme = 'blue' | 'green' | 'red' | 'orange' | 'gray'
const badgeTheme = (color: string): BadgeTheme =>
  ({ orange: 'orange', blue: 'blue', green: 'green', red: 'red', gray: 'gray' }[color] as BadgeTheme) || 'gray'

const statusIcon = (color: string) =>
  ({ orange: Clock, blue: CheckCircle, green: CheckCircle, red: XCircle, gray: Clock }[color] || Clock)

const statusIconClass = (color: string) =>
  ({ orange: 'text-orange-500', blue: 'text-blue-500', green: 'text-green-500', red: 'text-red-500', gray: 'text-gray-400' }[color] || 'text-gray-400')

const statusBg = (color: string) =>
  ({ orange: 'bg-orange-50', blue: 'bg-blue-50', green: 'bg-green-50', red: 'bg-red-50', gray: 'bg-gray-50' }[color] || 'bg-gray-50')

const toggleExpand = (name: string) => {
  expandedOrder.value = expandedOrder.value === name ? null : name
}

const confirmCancel = (name: string) => {
  cancelTargetOrder.value = name
  cancelConfirmOpen.value = true
}

const executeCancel = () => {
  if (cancelTargetOrder.value) {
    emit('cancel-order', cancelTargetOrder.value)
    cancelConfirmOpen.value = false
    cancelTargetOrder.value = null
  }
}

const timelineSteps = (order: any) => [
  { key: 'placed',    label: 'Placed',     icon: CheckCircle, done: true,                         lineAfter: order.docstatus >= 1 },
  { key: 'accepted',  label: 'Accepted',   icon: CheckCircle, done: order.docstatus >= 1,         lineAfter: order.per_delivered >= 100 },
  { key: 'delivered', label: 'Delivered',  icon: Truck,       done: order.per_delivered >= 100,   lineAfter: order.status === 'Completed' },
  { key: 'completed', label: 'Completed',  icon: CheckCircle, done: order.status === 'Completed', lineAfter: false },
]
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="space-y-3">
    <div v-for="i in 3" :key="i" class="h-20 bg-gray-100 rounded-2xl animate-pulse" />
  </div>

  <!-- Empty -->
  <div v-else-if="orders.length === 0"
    class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-28 text-center">
    <ClipboardList class="w-10 h-10 text-gray-300 mx-auto mb-3" />
    <h3 class="text-base font-bold text-gray-700">No Orders Yet</h3>
    <p class="text-sm text-gray-400 mt-1">Your placed orders will appear here.</p>
    <Button variant="outline" class="mt-4" @click="emit('go-shop')">
      <template #prefix><Store class="w-4 h-4" /></template>
      Start Shopping
    </Button>
  </div>

  <!-- Orders list -->
  <div v-else class="space-y-3">
    <div
      v-for="order in orders" :key="order.name"
      :class="[
        'rounded-2xl border overflow-hidden hover:shadow-md transition-shadow',
        order.is_subscription_order ? 'bg-blue-50/40 border-blue-100' : 'bg-white border-gray-100'
      ]"
    >
      <!-- Row header -->
      <div class="flex items-center justify-between p-4 gap-3">
        <div class="flex items-center gap-3 min-w-0">
          <div :class="['p-2 rounded-xl flex-shrink-0', statusBg(order.status_color)]">
            <component :is="statusIcon(order.status_color)"
              :class="['w-4 h-4', statusIconClass(order.status_color)]" />
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-bold text-gray-900 text-sm font-mono">{{ order.name }}</span>
              <Badge :label="order.display_status" :theme="badgeTheme(order.status_color)" size="sm" />
              <span v-if="order.is_subscription_order"
                class="inline-flex items-center gap-1 bg-blue-100 text-blue-700 text-[9px] font-bold px-2 py-0.5 rounded-full">
                <Newspaper class="w-2.5 h-2.5" /> Subscription Order
              </span>
            </div>
            <p class="text-xs text-gray-400 mt-0.5">
              {{ order.formatted_date }}<span v-if="order.seller"> · {{ order.seller }}</span>
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2 flex-shrink-0">
          <span class="font-black text-gray-900 text-sm">{{ order.formatted_total }}</span>
          <Button v-if="order.can_cancel && !order.is_subscription_order"
            variant="subtle" theme="red" size="sm" @click="confirmCancel(order.name)">Cancel</Button>
          <Button variant="ghost" size="sm" @click="toggleExpand(order.name)">
            <template #icon>
              <ChevronUp v-if="expandedOrder === order.name" class="w-4 h-4" />
              <ChevronDown v-else class="w-4 h-4" />
            </template>
          </Button>
        </div>
      </div>

      <!-- Expanded detail -->
      <div v-if="expandedOrder === order.name" class="border-t border-gray-100/80 px-4 pb-5 pt-4 space-y-4">
        <div v-if="order.is_subscription_order"
          class="flex items-start gap-2 bg-blue-50 border border-blue-100 rounded-xl px-3 py-2.5">
          <Newspaper class="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
          <p class="text-xs text-blue-700">Auto-generated daily delivery order from your subscription plan.</p>
        </div>

        <!-- Timeline -->
        <div class="flex items-center gap-1">
          <template v-for="(step, idx) in timelineSteps(order)" :key="step.key">
            <div class="flex flex-col items-center gap-1">
              <div :class="['w-7 h-7 rounded-full flex items-center justify-center',
                step.done ? (step.key === 'completed' ? 'bg-green-500' : 'bg-blue-500') : 'bg-gray-100']">
                <component :is="step.icon"
                  :class="['w-3.5 h-3.5', step.done ? 'text-white' : 'text-gray-300']" />
              </div>
              <span :class="['text-[10px] font-semibold whitespace-nowrap',
                step.done ? (step.key === 'completed' ? 'text-green-600' : 'text-blue-600') : 'text-gray-400']">
                {{ step.label }}
              </span>
            </div>
            <div v-if="idx < timelineSteps(order).length - 1"
              :class="['flex-1 h-px mb-4', step.lineAfter ? 'bg-blue-200' : 'bg-gray-100']" />
          </template>
        </div>

        <div class="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
          <FileText class="w-4 h-4 text-gray-400 flex-shrink-0" />
          <p class="text-xs text-gray-500">
            Expected delivery:
            <span class="font-semibold text-gray-700">{{ order.delivery_date || 'To be confirmed' }}</span>
          </p>
        </div>
      </div>
    </div>
  </div>

  <!-- Cancel confirm dialog -->
  <Dialog v-model="cancelConfirmOpen"
    :options="{ title: 'Cancel Order', message: `Are you sure you want to cancel ${cancelTargetOrder}?`, size: 'sm' }">
    <template #actions>
      <div class="flex gap-2 w-full">
        <Button variant="outline" class="flex-1" @click="cancelConfirmOpen = false">Keep Order</Button>
        <Button variant="solid" theme="red" class="flex-1" :loading="cancelLoading" @click="executeCancel">
          Yes, Cancel
        </Button>
      </div>
    </template>
  </Dialog>
</template>
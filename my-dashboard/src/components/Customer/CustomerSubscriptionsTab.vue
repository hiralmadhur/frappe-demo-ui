<script setup lang="ts">
import { Button } from 'frappe-ui'
import { Newspaper, Store, Hourglass } from 'lucide-vue-next'

const props = defineProps<{
  subscriptions: any[]
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'go-shop'): void
}>()

const ALL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_SHORT: Record<string, string> = {
  Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed',
  Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun'
}
const DAY_QTY_FIELD: Record<string, string> = {
  Monday: 'monday_qty', Tuesday: 'tuesday_qty', Wednesday: 'wednesday_qty',
  Thursday: 'thursday_qty', Friday: 'friday_qty', Saturday: 'saturday_qty', Sunday: 'sunday_qty'
}

const subStatusColor: Record<string, string> = {
  'Active':         'bg-green-100 text-green-700 border-green-200',
  'Accept Pending': 'bg-amber-100 text-amber-700 border-amber-200',
  'Expired':        'bg-gray-100 text-gray-500 border-gray-200',
  'Cancelled':      'bg-red-100 text-red-600 border-red-200',
}
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="space-y-3">
    <div v-for="i in 3" :key="i" class="h-32 bg-gray-100 rounded-2xl animate-pulse" />
  </div>

  <!-- Empty -->
  <div v-else-if="subscriptions.length === 0"
    class="bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 py-28 text-center">
    <Newspaper class="w-10 h-10 text-gray-300 mx-auto mb-3" />
    <h3 class="text-base font-bold text-gray-700">No Subscription Plans Yet</h3>
    <p class="text-sm text-gray-400 mt-1">Browse newspapers to subscribe for daily delivery.</p>
    <Button variant="outline" class="mt-4" @click="emit('go-shop')">
      <template #prefix><Store class="w-4 h-4" /></template>
      Browse Products
    </Button>
  </div>

  <!-- Subscriptions list -->
  <div v-else class="space-y-4">
    <div
      v-for="sub in subscriptions" :key="sub.name"
      class="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
    >
      <div class="p-4 flex items-start justify-between gap-3">
        <div class="flex items-center gap-3">
          <div class="p-2.5 bg-blue-50 rounded-xl text-blue-600">
            <Newspaper class="w-5 h-5" />
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-bold text-gray-900 text-sm font-mono">{{ sub.name }}</span>
              <span :class="['text-[10px] font-bold px-2 py-0.5 rounded-full border',
                subStatusColor[sub.status] || 'bg-gray-100 text-gray-500 border-gray-200']">
                {{ sub.status }}
              </span>
            </div>
            <p class="text-xs text-gray-400 mt-0.5">
              {{ sub.formatted_start }} → {{ sub.formatted_end }}
              <span v-if="sub.seller" class="ml-2">· {{ sub.seller }}</span>
            </p>
          </div>
        </div>
      </div>

      <!-- Schedule per item -->
      <div class="px-4 pb-4 space-y-3">
        <div
          v-for="si in sub.schedule_items" :key="si.item_code"
          class="bg-gray-50 rounded-xl p-3 border border-gray-100"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-gray-700">{{ si.item_name }}</span>
            <span v-if="si.is_primary_item"
              class="text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-bold">Primary</span>
          </div>
          <div class="flex gap-1.5 flex-wrap">
            <template v-for="day in ALL_DAYS" :key="day">
              <div :class="[
                'flex flex-col items-center px-2 py-1 rounded-lg text-[9px] font-bold',
                (si[DAY_QTY_FIELD[day]] || 0) > 0 ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'
              ]">
                <span>{{ DAY_SHORT[day] }}</span>
                <span v-if="(si[DAY_QTY_FIELD[day]] || 0) > 0" class="text-[8px] opacity-80">
                  ×{{ si[DAY_QTY_FIELD[day]] }}
                </span>
              </div>
            </template>
          </div>
        </div>

        <div v-if="sub.status === 'Accept Pending'"
          class="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
          <Hourglass class="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
          <p class="text-xs text-amber-700">
            Waiting for seller approval. Once accepted, daily delivery starts from next day.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
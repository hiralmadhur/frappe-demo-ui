<script setup lang="ts">
import { Button } from 'frappe-ui'
import { Newspaper, Star, CheckCircle, ChevronDown, ChevronUp, Zap } from 'lucide-vue-next'

const props = defineProps<{
  row: any
  expandedSubId: string | null
  processingSubId: string
}>()

const emit = defineEmits<{
  (e: 'toggle-expand', id: string): void
  (e: 'sub-action', subName: string, action: 'accept' | 'reject'): void
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
</script>

<template>
  <div :class="[
    'border-l-4 transition-all',
    row.status === 'Accept Pending'
      ? 'border-l-amber-400 bg-amber-50/50'
      : 'border-l-green-400 bg-green-50/20'
  ]">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between px-3 sm:px-5 md:px-6 py-3 sm:py-4 gap-2 sm:gap-3">
      <!-- Left: icon + info -->
      <div class="flex items-start sm:items-center gap-2 sm:gap-3 min-w-0 flex-1">
        <div :class="[
          'p-2 sm:p-2.5 rounded-xl flex-shrink-0 mt-0.5 sm:mt-0',
          row.status === 'Accept Pending' ? 'bg-amber-100 text-amber-600' : 'bg-green-100 text-green-600'
        ]">
          <Newspaper class="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
            <span class="font-black text-gray-900 font-mono text-xs sm:text-sm">{{ row.name }}</span>
            <span class="inline-flex items-center gap-1 bg-amber-100 text-amber-700 text-[8px] sm:text-[9px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full border border-amber-200">
              <Star class="w-2 h-2 sm:w-2.5 sm:h-2.5" />
              <span class="hidden xs:inline">Subscription Request</span>
              <span class="xs:hidden">Sub</span>
            </span>
            <span :class="[
              'text-[8px] sm:text-[9px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full border',
              row.status === 'Accept Pending' ? 'bg-amber-50 text-amber-600 border-amber-200'
                : row.status === 'Active' ? 'bg-green-50 text-green-600 border-green-200'
                : 'bg-gray-50 text-gray-500 border-gray-200'
            ]">{{ row.status }}</span>
          </div>
          <p class="text-[10px] sm:text-xs text-gray-500 mt-0.5 flex flex-wrap gap-x-1">
            <span>Customer:</span>
            <span class="font-semibold text-gray-700 truncate max-w-[140px] sm:max-w-none">{{ row.customer_name }}</span>
            <span class="hidden sm:inline">·</span>
            <span class="text-gray-400 text-[9px] sm:text-[10px]">{{ row.formatted_start }} → {{ row.formatted_end }}</span>
          </p>
          <p class="text-[9px] sm:text-[10px] text-gray-400 mt-0.5 truncate">
            Primary: <span class="font-semibold text-gray-600">{{ row.primary_item_name }}</span>
          </p>
        </div>
      </div>

      <!-- Right: actions + expand -->
      <div class="flex items-center gap-1.5 sm:gap-2 flex-shrink-0 pl-8 sm:pl-0 flex-wrap sm:flex-nowrap">
        <template v-if="row.status === 'Accept Pending'">
          <Button
            variant="solid"
            class="!bg-green-600 hover:!bg-green-700 !text-white text-xs"
            size="sm"
            :loading="processingSubId === row.name"
            @click.stop="emit('sub-action', row.name, 'accept')"
          >
            <template #prefix><CheckCircle class="w-3 h-3 sm:w-3.5 sm:h-3.5" /></template>
            <span class="hidden sm:inline">Accept Plan</span>
            <span class="sm:hidden">Accept</span>
          </Button>
          <Button
            variant="subtle" theme="red" size="sm"
            :loading="processingSubId === row.name"
            class="text-xs"
            @click.stop="emit('sub-action', row.name, 'reject')"
          >Reject</Button>
        </template>

        <template v-else-if="row.status === 'Active'">
          <div class="flex items-center gap-1 sm:gap-1.5 bg-green-100 border border-green-200 rounded-lg px-2 sm:px-2.5 py-1 sm:py-1.5">
            <Zap class="w-3 h-3 text-green-600 flex-shrink-0" />
            <span class="text-[9px] sm:text-[10px] font-bold text-green-700 hidden xs:inline">Auto-running</span>
          </div>
          <Button
            variant="subtle" theme="red" size="sm"
            :loading="processingSubId === row.name"
            class="text-xs"
            @click.stop="emit('sub-action', row.name, 'reject')"
          >
            <span class="hidden sm:inline">Cancel Plan</span>
            <span class="sm:hidden">Cancel</span>
          </Button>
        </template>

        <button
          @click="emit('toggle-expand', row.name)"
          class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all flex-shrink-0"
        >
          <ChevronUp v-if="expandedSubId === row.name" class="w-4 h-4" />
          <ChevronDown v-else class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Expanded schedule -->
    <div
      v-if="expandedSubId === row.name"
      class="px-3 sm:px-5 md:px-6 pb-4 sm:pb-5 pt-0 border-t border-amber-100/80 bg-white/50 space-y-3"
    >
      <div
        v-if="row.status === 'Accept Pending'"
        class="mt-3 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2.5"
      >
        <Star class="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
        <p class="text-[10px] sm:text-xs text-amber-800">
          <span class="font-bold">Accept this plan</span> to activate daily delivery.
          From <strong>next day</strong>, system auto-generates Sales Orders + Delivery Notes.
          You only handle <strong>invoicing</strong>.
        </p>
      </div>

      <div
        v-for="si in row.schedule_items"
        :key="si.item_code"
        class="bg-gray-50 rounded-xl border border-gray-100 overflow-hidden"
      >
        <div class="flex items-center justify-between px-3 sm:px-4 py-2 bg-white border-b border-gray-100">
          <span class="text-[11px] sm:text-xs font-bold text-gray-800 truncate mr-2">{{ si.item_name }}</span>
          <span v-if="si.is_primary_item"
            class="text-[8px] sm:text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-bold flex-shrink-0">
            Primary
          </span>
        </div>
        <div class="p-2 sm:p-3 flex gap-1.5 sm:gap-2 flex-wrap">
          <template v-for="day in ALL_DAYS" :key="day">
            <div :class="[
              'flex flex-col items-center px-2 sm:px-3 py-1.5 sm:py-2 rounded-xl font-bold min-w-[36px] sm:min-w-[44px] text-center',
              (si[DAY_QTY_FIELD[day]] || 0) > 0
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-400'
            ]">
              <span class="text-[8px] sm:text-[9px] uppercase tracking-wide">{{ DAY_SHORT[day] }}</span>
              <span v-if="(si[DAY_QTY_FIELD[day]] || 0) > 0"
                class="text-xs sm:text-sm font-black leading-tight mt-0.5">
                {{ si[DAY_QTY_FIELD[day]] }}
              </span>
              <span v-else class="text-[9px] sm:text-[10px] opacity-30 mt-0.5">—</span>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
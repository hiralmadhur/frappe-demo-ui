<script setup lang="ts">
import { Badge, Button, LoadingIndicator } from 'frappe-ui'
import {
  Newspaper, ShoppingBag, Calendar, Truck, FileText,
  ChevronRight, ChevronDown, ChevronUp, Zap, Star,
  CheckCircle, Package
} from 'lucide-vue-next'

// ─── Props ────────────────────────────────────────────────────────────────────
const props = defineProps<{
  combinedRows: any[]
  loading: boolean
  activeFilter: string
  expandedSubId: string | null
  processingSubId: string
  processingId: string
  formatCurrency: (amount: number, currency?: string) => string
  getStatusTheme: (status: string) => string
}>()

// ─── Emits ────────────────────────────────────────────────────────────────────
const emit = defineEmits<{
  (e: 'toggle-sub-expand', id: string): void
  (e: 'sub-action', subName: string, action: 'accept' | 'reject'): void
  (e: 'open-order-detail', row: any): void
  (e: 'order-action', id: string, action: string): void
  (e: 'show-all'): void
}>()

// ─── Constants (subscription schedule grid) ───────────────────────────────────
const ALL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_SHORT: Record<string, string> = {
  Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed',
  Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun'
}
const DAY_QTY_FIELD: Record<string, string> = {
  Monday: 'monday_qty',    Tuesday: 'tuesday_qty',   Wednesday: 'wednesday_qty',
  Thursday: 'thursday_qty', Friday: 'friday_qty',    Saturday: 'saturday_qty',
  Sunday: 'sunday_qty'
}
</script>

<template>
  <!--
    ROOT: w-full, no padding — parent SellerHome controls all spacing.
    This removes the white gap visible on both sides.
  -->
  <div class="w-full min-w-0">

    <!-- ── Legend ── -->
    <div class="flex flex-wrap gap-1.5 px-3 sm:px-5 pt-3 pb-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div class="flex items-center gap-1.5 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1 flex-shrink-0">
        <div class="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0"></div>
        <span class="text-[10px] font-semibold text-amber-700 whitespace-nowrap">Subscription — Accept to start daily delivery</span>
      </div>
      <div class="flex items-center gap-1.5 bg-blue-50 border border-blue-200 rounded-lg px-2.5 py-1 flex-shrink-0">
        <div class="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0"></div>
        <span class="text-[10px] font-semibold text-blue-700 whitespace-nowrap">Daily Auto-Order — DN auto-created</span>
      </div>
      <div class="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1 flex-shrink-0">
        <div class="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0"></div>
        <span class="text-[10px] font-semibold text-gray-500 whitespace-nowrap">Normal Order</span>
      </div>
    </div>

    <!-- ── Main list ── -->
    <div class="min-h-[300px] sm:min-h-[400px]">

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-20 sm:py-32">
        <LoadingIndicator class="w-7 h-7 sm:w-8 sm:h-8 mb-4 text-blue-600" />
        <p class="text-gray-400 font-medium text-sm animate-pulse">Loading...</p>
      </div>

      <!-- Empty -->
      <div v-else-if="combinedRows.length === 0" class="flex flex-col items-center justify-center py-20 sm:py-32 px-4 text-center">
        <Package class="w-10 h-10 sm:w-12 sm:h-12 text-gray-200 mb-4" />
        <p class="text-gray-400 font-medium text-sm">Nothing to show</p>
        <button v-if="activeFilter !== 'all'" @click="emit('show-all')" class="mt-3 text-sm text-blue-600 hover:underline">
          Show all
        </button>
      </div>

      <!-- Rows -->
      <div v-else class="divide-y divide-gray-50">
        <template v-for="row in combinedRows" :key="row.row_type + '-' + row.name">

          <div
            v-if="row.row_type === 'subscription'"
            :class="[
              'border-l-4 transition-all',
              row.status === 'Accept Pending'
                ? 'border-l-amber-400 bg-amber-50/50'
                : 'border-l-green-400 bg-green-50/20'
            ]"
          >
            <!-- Header -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between px-3 sm:px-5 py-3 gap-2">

              <!-- Left: icon + info -->
              <div class="flex items-start sm:items-center gap-2 sm:gap-3 min-w-0 flex-1">
                <div :class="['p-2 sm:p-2.5 rounded-xl flex-shrink-0 mt-0.5 sm:mt-0', row.status === 'Accept Pending' ? 'bg-amber-100 text-amber-600' : 'bg-green-100 text-green-600']">
                  <Newspaper class="w-4 h-4 sm:w-5 sm:h-5" />
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="font-black text-gray-900 font-mono text-xs sm:text-sm">{{ row.name }}</span>
                    <span class="inline-flex items-center gap-1 bg-amber-100 text-amber-700 text-[8px] sm:text-[9px] font-bold px-1.5 py-0.5 rounded-full border border-amber-200">
                      <Star class="w-2 h-2 sm:w-2.5 sm:h-2.5" />
                      Subscription Request
                    </span>
                    <span :class="['text-[8px] sm:text-[9px] font-bold px-1.5 py-0.5 rounded-full border', row.status === 'Accept Pending' ? 'bg-amber-50 text-amber-600 border-amber-200' : row.status === 'Active' ? 'bg-green-50 text-green-600 border-green-200' : 'bg-gray-50 text-gray-500 border-gray-200']">
                      {{ row.status }}
                    </span>
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
              <div class="flex items-center gap-1.5 flex-shrink-0 pl-9 sm:pl-0 flex-wrap sm:flex-nowrap">
                <template v-if="row.status === 'Accept Pending'">
                  <Button variant="solid" class="!bg-green-600 hover:!bg-green-700 !text-white text-xs" size="sm" :loading="processingSubId === row.name" @click.stop="emit('sub-action', row.name, 'accept')">
                    <template #prefix><CheckCircle class="w-3 h-3 sm:w-3.5 sm:h-3.5" /></template>
                    <span class="hidden sm:inline">Accept Plan</span>
                    <span class="sm:hidden">Accept</span>
                  </Button>
                  <Button variant="subtle" theme="red" size="sm" :loading="processingSubId === row.name" class="text-xs" @click.stop="emit('sub-action', row.name, 'reject')">Reject</Button>
                </template>
                <template v-else-if="row.status === 'Active'">
                  <div class="flex items-center gap-1 bg-green-100 border border-green-200 rounded-lg px-2 py-1">
                    <Zap class="w-3 h-3 text-green-600 flex-shrink-0" />
                    <span class="text-[9px] sm:text-[10px] font-bold text-green-700">Auto-running</span>
                  </div>
                  <Button variant="subtle" theme="red" size="sm" :loading="processingSubId === row.name" class="text-xs" @click.stop="emit('sub-action', row.name, 'reject')">
                    <span class="hidden sm:inline">Cancel Plan</span>
                    <span class="sm:hidden">Cancel</span>
                  </Button>
                </template>
                <button @click="emit('toggle-sub-expand', row.name)" class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all flex-shrink-0">
                  <ChevronUp v-if="expandedSubId === row.name" class="w-4 h-4" />
                  <ChevronDown v-else class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- Expanded Schedule -->
            <div v-if="expandedSubId === row.name" class="px-3 sm:px-5 pb-4 pt-0 border-t border-amber-100/80 bg-white/50 space-y-3">
              <div v-if="row.status === 'Accept Pending'" class="mt-3 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2.5">
                <Star class="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                <p class="text-[10px] sm:text-xs text-amber-800">
                  <span class="font-bold">Accept this plan</span> to activate daily delivery.
                  From <strong>next day</strong>, system auto-generates Sales Orders + Delivery Notes.
                  You only handle <strong>invoicing</strong>.
                </p>
              </div>
              <div v-for="si in row.schedule_items" :key="si.item_code" class="bg-gray-50 rounded-xl border border-gray-100 overflow-hidden">
                <div class="flex items-center justify-between px-3 sm:px-4 py-2 bg-white border-b border-gray-100">
                  <span class="text-[11px] sm:text-xs font-bold text-gray-800 truncate mr-2">{{ si.item_name }}</span>
                  <span v-if="si.is_primary_item" class="text-[8px] sm:text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-bold flex-shrink-0">Primary</span>
                </div>
                <div class="p-2 sm:p-3 flex gap-1.5 flex-wrap">
                  <template v-for="day in ALL_DAYS" :key="day">
                    <div :class="['flex flex-col items-center px-2 sm:px-3 py-1.5 rounded-xl font-bold min-w-[34px] sm:min-w-[44px] text-center', (si[DAY_QTY_FIELD[day]] || 0) > 0 ? 'bg-blue-600 text-white shadow-sm' : 'bg-gray-100 text-gray-400']">
                      <span class="text-[8px] sm:text-[9px] uppercase tracking-wide">{{ DAY_SHORT[day] }}</span>
                      <span v-if="(si[DAY_QTY_FIELD[day]] || 0) > 0" class="text-xs sm:text-sm font-black leading-tight mt-0.5">{{ si[DAY_QTY_FIELD[day]] }}</span>
                      <span v-else class="text-[9px] opacity-30 mt-0.5">—</span>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <div
            v-else
            :class="[
              'flex flex-col sm:flex-row sm:items-center justify-between px-3 sm:px-5 py-3 gap-2 cursor-pointer group transition-all border-l-4',
              row.custom_subscription_refereance
                ? 'border-l-blue-300 bg-blue-50/20 hover:bg-blue-50/50 active:bg-blue-50/70'
                : 'border-l-transparent hover:bg-gray-50/70 active:bg-gray-100/50'
            ]"
            @click="emit('open-order-detail', row)"
          >
            <!-- Left: info -->
            <div class="flex items-start sm:items-center gap-2 sm:gap-3 min-w-0 flex-1">
              <div :class="['p-2 sm:p-2.5 rounded-xl flex-shrink-0 transition-colors mt-0.5 sm:mt-0', row.custom_subscription_refereance ? 'bg-blue-100 text-blue-600 group-hover:bg-blue-500 group-hover:text-white' : 'bg-gray-100 text-gray-500 group-hover:bg-blue-100 group-hover:text-blue-600']">
                <Newspaper v-if="row.custom_subscription_refereance" class="w-4 h-4 sm:w-5 sm:h-5" />
                <ShoppingBag v-else class="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span :class="['font-bold font-mono text-xs sm:text-sm transition-colors', row.custom_subscription_refereance ? 'text-blue-700' : 'text-gray-900 group-hover:text-blue-600']">{{ row.name }}</span>
                  <span v-if="row.custom_subscription_refereance" class="inline-flex items-center gap-1 bg-blue-100 text-blue-700 text-[8px] sm:text-[9px] font-bold px-1.5 py-0.5 rounded-full border border-blue-200">
                    <Zap class="w-2 h-2 sm:w-2.5 sm:h-2.5" />
                    <span class="hidden xs:inline">Daily Sub-Auto-Order</span>
                    <span class="xs:hidden">Sub</span>
                  </span>
                  <span v-else class="inline-flex items-center gap-1 bg-gray-100 text-gray-500 text-[8px] sm:text-[9px] font-bold px-1.5 py-0.5 rounded-full border border-gray-200">
                    <ShoppingBag class="w-2 h-2 sm:w-2.5 sm:h-2.5" />
                    <span class="hidden xs:inline">Normal Order</span>
                    <span class="xs:hidden">Normal</span>
                  </span>
                  <Badge :theme="(getStatusTheme(row.status) as any)" variant="subtle" :label="row.status" size="sm" />
                </div>
                <p class="text-[10px] sm:text-xs text-gray-400 mt-0.5 flex items-center gap-1 flex-wrap">
                  <Calendar class="w-3 h-3 flex-shrink-0" />
                  <span>{{ row.transaction_date }}</span>
                  <span v-if="row.customer_name" class="truncate max-w-[120px] sm:max-w-none">· {{ row.customer_name }}</span>
                </p>
                <p v-if="row.custom_subscription_refereance" class="text-[9px] sm:text-[10px] text-blue-400 font-mono mt-0.5 truncate">
                  📋 {{ row.custom_subscription_refereance }}
                </p>
              </div>
            </div>

            <!-- Right: amount + buttons -->
            <div class="flex items-center gap-1.5 flex-shrink-0 pl-9 sm:pl-0 flex-wrap sm:flex-nowrap" @click.stop>
              <span class="font-black text-gray-800 font-mono text-xs sm:text-sm whitespace-nowrap">
                {{ formatCurrency(row.grand_total, row.currency) }}
              </span>

              <!-- Accept draft -->
              <Button v-if="row.docstatus === 0" variant="solid" theme="blue" size="sm" :loading="processingId === row.name" @click="emit('order-action', row.name, 'accept')" class="text-xs">Accept</Button>

              <!-- Deliver -->
              <Button v-if="row.docstatus === 1 && row.per_delivered < 100 && !row.custom_subscription_refereance" variant="subtle" theme="gray" size="sm" :loading="processingId === row.name" @click="emit('order-action', row.name, 'deliver')" class="text-xs">
                <template #prefix><Truck class="w-3 h-3 sm:w-3.5 sm:h-3.5" /></template>
                <span class="hidden sm:inline">Deliver</span>
              </Button>

              <!-- Invoice -->
              <Button v-if="row.per_delivered >= 100 && row.per_billed < 100" variant="subtle" theme="gray" size="sm" :loading="processingId === row.name" @click="emit('order-action', row.name, 'invoice')" class="text-xs">
                <template #prefix><FileText class="w-3 h-3 sm:w-3.5 sm:h-3.5" /></template>
                <span class="hidden sm:inline">Invoice</span>
              </Button>

              <!-- Auto-delivered badge -->
              <span v-if="row.custom_subscription_refereance && row.docstatus === 1 && row.per_delivered < 100" class="text-[9px] sm:text-[10px] text-blue-500 font-semibold bg-blue-50 border border-blue-100 px-1.5 py-1 rounded-lg whitespace-nowrap">
                ⚡ Auto-Delivered
              </span>

              <ChevronRight class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-300 ml-1 flex-shrink-0" />
            </div>
          </div>

        </template>
      </div>
      <!-- end rows -->

    </div>
  </div>
</template>
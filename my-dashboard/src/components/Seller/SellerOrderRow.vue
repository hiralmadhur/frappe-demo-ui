<script setup lang="ts">
import { Badge, Button } from 'frappe-ui'
import { Newspaper, ShoppingBag, Calendar, Truck, FileText, ChevronRight, Zap } from 'lucide-vue-next'

const props = defineProps<{
  row: any
  processingId: string
  formatCurrency: (amount: number, currency?: string) => string
  getStatusTheme: (status: string) => string
}>()

const emit = defineEmits<{
  (e: 'open-detail', row: any): void
  (e: 'order-action', id: string, action: string): void
}>()
</script>

<template>
  <div
    :class="[
      'flex flex-col sm:flex-row sm:items-center justify-between px-3 sm:px-5 md:px-6 py-3 sm:py-4 gap-2 sm:gap-3 cursor-pointer group transition-all border-l-4',
      row.custom_subscription_refereance
        ? 'border-l-blue-300 bg-blue-50/20 hover:bg-blue-50/50'
        : 'border-l-transparent hover:bg-gray-50/70'
    ]"
    @click="emit('open-detail', row)"
  >
    <!-- Left: info -->
    <div class="flex items-start sm:items-center gap-2 sm:gap-3 min-w-0 flex-1">
      <div :class="[
        'p-2 sm:p-2.5 rounded-xl flex-shrink-0 transition-colors mt-0.5 sm:mt-0',
        row.custom_subscription_refereance
          ? 'bg-blue-100 text-blue-600 group-hover:bg-blue-500 group-hover:text-white'
          : 'bg-gray-100 text-gray-500 group-hover:bg-blue-100 group-hover:text-blue-600'
      ]">
        <Newspaper v-if="row.custom_subscription_refereance" class="w-4 h-4 sm:w-5 sm:h-5" />
        <ShoppingBag v-else class="w-4 h-4 sm:w-5 sm:h-5" />
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
          <span :class="[
            'font-bold font-mono text-xs sm:text-sm transition-colors',
            row.custom_subscription_refereance ? 'text-blue-700' : 'text-gray-900 group-hover:text-blue-600'
          ]">{{ row.name }}</span>

          <span v-if="row.custom_subscription_refereance"
            class="inline-flex items-center gap-1 bg-blue-100 text-blue-700 text-[8px] sm:text-[9px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full border border-blue-200">
            <Zap class="w-2 h-2 sm:w-2.5 sm:h-2.5" />
            <span class="hidden xs:inline">Daily Sub-Auto-Order</span>
            <span class="xs:hidden">Sub</span>
          </span>
          <span v-else
            class="inline-flex items-center gap-1 bg-gray-100 text-gray-500 text-[8px] sm:text-[9px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full border border-gray-200">
            <ShoppingBag class="w-2 h-2 sm:w-2.5 sm:h-2.5" />
            <span class="hidden xs:inline">Normal Order</span>
            <span class="xs:hidden">Normal</span>
          </span>

          <Badge :theme="(getStatusTheme(row.status) as any)" variant="subtle" :label="row.status" size="sm" />
        </div>

        <p class="text-[10px] sm:text-xs text-gray-400 mt-0.5 flex items-center gap-1 sm:gap-1.5 flex-wrap">
          <Calendar class="w-3 h-3 flex-shrink-0" />
          <span>{{ row.transaction_date }}</span>
          <span v-if="row.customer_name" class="truncate max-w-[120px] sm:max-w-none">
            · {{ row.customer_name }}
          </span>
        </p>
        <p v-if="row.custom_subscription_refereance"
          class="text-[9px] sm:text-[10px] text-blue-400 font-mono mt-0.5 truncate">
          📋 {{ row.custom_subscription_refereance }}
        </p>
      </div>
    </div>

    <!-- Right: amount + actions -->
    <div
      class="flex items-center gap-1.5 sm:gap-2 flex-shrink-0 pl-8 sm:pl-0 flex-wrap sm:flex-nowrap"
      @click.stop
    >
      <span class="font-black text-gray-800 font-mono text-xs sm:text-sm whitespace-nowrap">
        {{ formatCurrency(row.grand_total, row.currency) }}
      </span>

      <Button
        v-if="row.docstatus === 0"
        variant="solid" theme="blue" size="sm"
        :loading="processingId === row.name"
        @click="emit('order-action', row.name, 'accept')"
        class="text-xs"
      >Accept</Button>

      <Button
        v-if="row.docstatus === 1 && row.per_delivered < 100 && !row.custom_subscription_refereance"
        variant="subtle" theme="gray" size="sm"
        :loading="processingId === row.name"
        @click="emit('order-action', row.name, 'deliver')"
        class="text-xs"
      >
        <template #prefix><Truck class="w-3 h-3 sm:w-3.5 sm:h-3.5" /></template>
        <span class="hidden sm:inline">Deliver</span>
      </Button>

      <Button
        v-if="row.per_delivered >= 100 && row.per_billed < 100"
        variant="subtle" theme="gray" size="sm"
        :loading="processingId === row.name"
        @click="emit('order-action', row.name, 'invoice')"
        class="text-xs"
      >
        <template #prefix><FileText class="w-3 h-3 sm:w-3.5 sm:h-3.5" /></template>
        <span class="hidden sm:inline">Invoice</span>
      </Button>

      <span
        v-if="row.custom_subscription_refereance && row.docstatus === 1 && row.per_delivered < 100"
        class="text-[9px] sm:text-[10px] text-blue-500 font-semibold bg-blue-50 border border-blue-100 px-1.5 sm:px-2 py-1 rounded-lg whitespace-nowrap"
      >⚡ Auto-Delivered</span>

      <ChevronRight class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-300 ml-1 flex-shrink-0" />
    </div>
  </div>
</template>
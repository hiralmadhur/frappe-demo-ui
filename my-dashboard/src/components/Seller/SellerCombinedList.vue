<script setup lang="ts">
import { LoadingIndicator } from 'frappe-ui'
import { Package } from 'lucide-vue-next'
import SellerSubscriptionRow from '@/components/Seller/SellerSubscriptionRow.vue'
import SellerOrderRow        from '@/components/Seller/SellerOrderRow.vue'

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

const emit = defineEmits<{
  (e: 'toggle-sub-expand', id: string): void
  (e: 'sub-action', subName: string, action: 'accept' | 'reject'): void
  (e: 'open-order-detail', row: any): void
  (e: 'order-action', id: string, action: string): void
  (e: 'show-all'): void
}>()
</script>

<template>
  <!-- Legend - scrollable on small screens -->
  <div class="flex flex-wrap sm:flex-wrap gap-1.5 sm:gap-2 px-0.5 sm:px-1 overflow-x-auto pb-1">
    <div class="flex items-center gap-1.5 sm:gap-2 bg-amber-50 border border-amber-200 rounded-lg sm:rounded-xl px-2.5 sm:px-3 py-1 sm:py-1.5 flex-shrink-0">
      <div class="w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full bg-amber-400 flex-shrink-0"></div>
      <span class="text-[10px] sm:text-xs font-semibold text-amber-700 whitespace-nowrap">
        Subscription — Accept to start daily delivery
      </span>
    </div>
    <div class="flex items-center gap-1.5 sm:gap-2 bg-blue-50 border border-blue-200 rounded-lg sm:rounded-xl px-2.5 sm:px-3 py-1 sm:py-1.5 flex-shrink-0">
      <div class="w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full bg-blue-400 flex-shrink-0"></div>
      <span class="text-[10px] sm:text-xs font-semibold text-blue-700 whitespace-nowrap">
        Daily Auto-Order — DN auto-created
      </span>
    </div>
    <div class="flex items-center gap-1.5 sm:gap-2 bg-gray-50 border border-gray-200 rounded-lg sm:rounded-xl px-2.5 sm:px-3 py-1 sm:py-1.5 flex-shrink-0">
      <div class="w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full bg-gray-300 flex-shrink-0"></div>
      <span class="text-[10px] sm:text-xs font-semibold text-gray-500 whitespace-nowrap">Normal Order</span>
    </div>
  </div>

  <!-- Main list container -->
  <div class="bg-white rounded-2xl sm:rounded-[2rem] border border-gray-100 shadow-lg sm:shadow-xl overflow-hidden min-h-[400px] sm:min-h-[500px]">

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-24 sm:py-40">
      <LoadingIndicator class="w-7 h-7 sm:w-8 sm:h-8 mb-4 text-blue-600" />
      <p class="text-gray-400 font-medium text-sm animate-pulse">Loading...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="combinedRows.length === 0"
      class="flex flex-col items-center justify-center py-24 sm:py-40 px-4 text-center">
      <Package class="w-10 h-10 sm:w-12 sm:h-12 text-gray-200 mb-4" />
      <p class="text-gray-400 font-medium text-sm">Nothing to show</p>
      <button
        v-if="activeFilter !== 'all'"
        @click="emit('show-all')"
        class="mt-3 text-sm text-blue-600 hover:underline"
      >Show all</button>
    </div>

    <!-- Rows -->
    <div v-else class="divide-y divide-gray-50">
      <template v-for="row in combinedRows" :key="row.row_type + '-' + row.name">
        <SellerSubscriptionRow
          v-if="row.row_type === 'subscription'"
          :row="row"
          :expanded-sub-id="expandedSubId"
          :processing-sub-id="processingSubId"
          @toggle-expand="emit('toggle-sub-expand', $event)"
          @sub-action="(name, action) => emit('sub-action', name, action)"
        />
        <SellerOrderRow
          v-else
          :row="row"
          :processing-id="processingId"
          :format-currency="formatCurrency"
          :get-status-theme="getStatusTheme"
          @open-detail="emit('open-order-detail', $event)"
          @order-action="(id, action) => emit('order-action', id, action)"
        />
      </template>
    </div>
  </div>
</template>
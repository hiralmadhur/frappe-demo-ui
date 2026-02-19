<script setup lang="ts">
import { Newspaper, CheckCircle, Clock, Truck } from 'lucide-vue-next'

const props = defineProps<{
  stats: {
    subPending: number
    subActive: number
    orderPending: number
    toDeliver: number
    completed: number
  }
  activeFilter: string
}>()

const emit = defineEmits<{
  (e: 'update:activeFilter', val: string): void
}>()

const toggle = (val: string) => {
  emit('update:activeFilter', props.activeFilter === val ? 'all' : val)
}
</script>

<template>
  <!-- 2 cols on mobile, 3 on sm, 5 on md+ -->
  <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 sm:gap-3 md:gap-4">

    <!-- Sub Pending -->
    <button
      @click="toggle('subscription_pending')"
      :class="[
        'p-3 sm:p-4 rounded-2xl sm:rounded-3xl border shadow-sm flex items-center justify-between transition-all text-left',
        activeFilter === 'subscription_pending'
          ? 'bg-amber-500 border-amber-500'
          : 'bg-white border-amber-100 hover:border-amber-300'
      ]"
    >
      <div class="min-w-0">
        <p :class="['text-[9px] sm:text-[10px] font-bold uppercase tracking-widest mb-1 truncate',
          activeFilter === 'subscription_pending' ? 'text-amber-100' : 'text-amber-400']">
          Sub Pending
        </p>
        <p :class="['text-2xl sm:text-3xl font-black',
          activeFilter === 'subscription_pending' ? 'text-white' : 'text-gray-900']">
          {{ stats.subPending }}
        </p>
      </div>
      <div :class="['h-9 w-9 sm:h-11 sm:w-11 rounded-xl sm:rounded-2xl flex items-center justify-center transition-colors flex-shrink-0 ml-2',
        activeFilter === 'subscription_pending'
          ? 'bg-amber-400 text-white'
          : 'bg-amber-50 text-amber-500 hover:bg-amber-500 hover:text-white']">
        <Newspaper class="w-4 h-4 sm:w-5 sm:h-5" />
      </div>
    </button>

    <!-- Sub Active (non-clickable) -->
    <div class="bg-white p-3 sm:p-4 rounded-2xl sm:rounded-3xl border border-green-100 shadow-sm flex items-center justify-between">
      <div class="min-w-0">
        <p class="text-[9px] sm:text-[10px] font-bold text-green-500 uppercase tracking-widest mb-1 truncate">
          Sub Active
        </p>
        <p class="text-2xl sm:text-3xl font-black text-gray-900">{{ stats.subActive }}</p>
      </div>
      <div class="h-9 w-9 sm:h-11 sm:w-11 rounded-xl sm:rounded-2xl bg-green-50 flex items-center justify-center text-green-600 flex-shrink-0 ml-2">
        <CheckCircle class="w-4 h-4 sm:w-5 sm:h-5" />
      </div>
    </div>

    <!-- To Accept (Normal Orders) -->
    <button
      @click="toggle('normal')"
      :class="[
        'p-3 sm:p-4 rounded-2xl sm:rounded-3xl border shadow-sm flex items-center justify-between transition-all text-left',
        activeFilter === 'normal'
          ? 'bg-orange-500 border-orange-500'
          : 'bg-white border-orange-100 hover:border-orange-300'
      ]"
    >
      <div class="min-w-0">
        <p :class="['text-[9px] sm:text-[10px] font-bold uppercase tracking-widest mb-1 truncate',
          activeFilter === 'normal' ? 'text-orange-100' : 'text-orange-400']">
          To Accept
        </p>
        <p :class="['text-2xl sm:text-3xl font-black',
          activeFilter === 'normal' ? 'text-white' : 'text-gray-900']">
          {{ stats.orderPending }}
        </p>
      </div>
      <div :class="['h-9 w-9 sm:h-11 sm:w-11 rounded-xl sm:rounded-2xl flex items-center justify-center transition-colors flex-shrink-0 ml-2',
        activeFilter === 'normal'
          ? 'bg-orange-400 text-white'
          : 'bg-orange-50 text-orange-500 hover:bg-orange-500 hover:text-white']">
        <Clock class="w-4 h-4 sm:w-5 sm:h-5" />
      </div>
    </button>

    <!-- Daily Orders -->
    <button
      @click="toggle('daily')"
      :class="[
        'p-3 sm:p-4 rounded-2xl sm:rounded-3xl border shadow-sm flex items-center justify-between transition-all text-left',
        activeFilter === 'daily'
          ? 'bg-blue-600 border-blue-600'
          : 'bg-white border-blue-100 hover:border-blue-300'
      ]"
    >
      <div class="min-w-0">
        <p :class="['text-[9px] sm:text-[10px] font-bold uppercase tracking-widest mb-1 truncate',
          activeFilter === 'daily' ? 'text-blue-200' : 'text-blue-400']">
          Daily Orders
        </p>
        <p :class="['text-2xl sm:text-3xl font-black',
          activeFilter === 'daily' ? 'text-white' : 'text-gray-900']">
          {{ stats.toDeliver }}
        </p>
      </div>
      <div :class="['h-9 w-9 sm:h-11 sm:w-11 rounded-xl sm:rounded-2xl flex items-center justify-center transition-colors flex-shrink-0 ml-2',
        activeFilter === 'daily'
          ? 'bg-blue-500 text-white'
          : 'bg-blue-50 text-blue-500 hover:bg-blue-600 hover:text-white']">
        <Truck class="w-4 h-4 sm:w-5 sm:h-5" />
      </div>
    </button>

    <!-- Completed (non-clickable) -->
    <div class="bg-white p-3 sm:p-4 rounded-2xl sm:rounded-3xl border border-emerald-100 shadow-sm flex items-center justify-between
      col-span-2 sm:col-span-1">
      <div class="min-w-0">
        <p class="text-[9px] sm:text-[10px] font-bold text-emerald-500 uppercase tracking-widest mb-1 truncate">
          Completed
        </p>
        <p class="text-2xl sm:text-3xl font-black text-gray-900">{{ stats.completed }}</p>
      </div>
      <div class="h-9 w-9 sm:h-11 sm:w-11 rounded-xl sm:rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600 flex-shrink-0 ml-2">
        <CheckCircle class="w-4 h-4 sm:w-5 sm:h-5" />
      </div>
    </div>
  </div>
</template>
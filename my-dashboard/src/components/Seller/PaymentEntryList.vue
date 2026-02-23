<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { createListResource, createResource } from 'frappe-ui'
import {
  CreditCard, RefreshCcw, XCircle, ChevronDown, ChevronRight,
  Calendar, CheckCircle2, Clock, Ban, Search,
  IndianRupee, Smartphone, FileText, Banknote, Building2,
  Wallet, ArrowDownCircle, ArrowUpCircle, Info, Trash2,
  X, AlertTriangle
} from 'lucide-vue-next'

// ─── PROPS ────────────────────────────────────────────────────────────────────
const props = defineProps<{
  customer?: string
  seller?: string
  formatCurrency: (amount: number, currency?: string) => string
}>()

// ─── TOAST ────────────────────────────────────────────────────────────────────
type ToastType = 'success' | 'error' | 'info'
interface Toast { id: number; message: string; type: ToastType }
const toasts = ref<Toast[]>([])
let toastId = 0

function showToast(message: string, type: ToastType = 'success') {
  const id = ++toastId
  toasts.value.push({ id, message, type })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, 3500)
}

// ─── STATE ────────────────────────────────────────────────────────────────────
const searchQuery  = ref('')
const fromDate     = ref('')
const toDate       = ref('')
const typeFilter   = ref<'all' | 'Receive' | 'Pay'>('all')
const expandedRow  = ref<string | null>(null)
const detailData   = ref<any>(null)
const processingId = ref('')

// ─── CONFIRM DIALOG ───────────────────────────────────────────────────────────
const confirmDialog = ref<{
  show: boolean; title: string; message: string
  confirmLabel: string; confirmClass: string; onConfirm: () => void
}>({ show: false, title: '', message: '', confirmLabel: 'Confirm', confirmClass: '', onConfirm: () => {} })

function openConfirm(opts: Partial<typeof confirmDialog.value> & { onConfirm: () => void }) {
  confirmDialog.value = { ...confirmDialog.value, show: true, ...opts }
}

// ─── RESOURCES ────────────────────────────────────────────────────────────────
const payments = createListResource({
  doctype: 'Payment Entry',
  fields: [
    'name', 'party', 'party_name', 'payment_type', 'mode_of_payment',
    'paid_amount', 'received_amount', 'docstatus',
    'posting_date', 'reference_no', 'reference_date',
    'remarks', 'paid_from', 'paid_to', 'company',
  ],
  filters: [],
  orderBy: 'posting_date desc',
  pageLength: 200,
  auto: false,
})

const peDetail = createResource({
  url: 'frappe.client.get',
  makeParams: (v: { name: string }) => ({ doctype: 'Payment Entry', name: v.name }),
  onSuccess(data: any) { detailData.value = data },
})

const cancelPE = createResource({
  url: 'frappe.client.cancel',
  onSuccess() {
    processingId.value = ''
    showToast('Payment Entry cancelled successfully!', 'success')
    payments.reload()
    if (expandedRow.value) peDetail.fetch({ name: expandedRow.value })
  },
  onError(err: any) {
    processingId.value = ''
    showToast(parseError(err), 'error')
  },
})

const deletePE = createResource({
  url: 'frappe.client.delete',
  onSuccess() {
    processingId.value = ''
    showToast('Payment Entry deleted!', 'success')
    expandedRow.value = null
    detailData.value = null
    payments.reload()
  },
  onError(err: any) {
    processingId.value = ''
    showToast(parseError(err), 'error')
  },
})

// ─── HELPERS ──────────────────────────────────────────────────────────────────
function parseError(err: any): string {
  try {
    const raw = err?.exc || err?.message || ''
    const lines = String(raw).split('\n')
    const lastLine = lines.filter(Boolean).at(-1) || ''
    return lastLine.replace(/^[A-Za-z.]+:\s*/, '').slice(0, 120) || 'Something went wrong'
  } catch { return 'Something went wrong' }
}

function getStatusInfo(docstatus: number, paymentType: string) {
  if (docstatus === 1) return { label: paymentType === 'Receive' ? 'Received' : 'Paid', color: 'green' }
  if (docstatus === 2) return { label: 'Cancelled', color: 'gray' }
  return { label: 'Draft', color: 'orange' }
}

function getModeIcon(mode: string) {
  const m = (mode || '').toLowerCase()
  if (m.includes('upi') || m.includes('phone') || m.includes('mobile')) return Smartphone
  if (m.includes('cheque') || m.includes('check')) return FileText
  if (m.includes('bank') || m.includes('transfer') || m.includes('neft') || m.includes('rtgs')) return Building2
  if (m.includes('wallet')) return Wallet
  return Banknote
}

function getModeColor(mode: string) {
  const m = (mode || '').toLowerCase()
  if (m.includes('upi') || m.includes('phone') || m.includes('mobile')) return 'violet'
  if (m.includes('cheque') || m.includes('check')) return 'blue'
  if (m.includes('bank') || m.includes('transfer') || m.includes('neft') || m.includes('rtgs')) return 'indigo'
  return 'green'
}

// ─── COMPUTED ─────────────────────────────────────────────────────────────────
const hasDateFilter = computed(() => fromDate.value !== '' || toDate.value !== '')

const filteredRows = computed(() => {
  let rows = (payments.data || []) as any[]

  if (typeFilter.value !== 'all')
    rows = rows.filter(r => r.payment_type === typeFilter.value)

  if (fromDate.value) rows = rows.filter(r => r.posting_date >= fromDate.value)
  if (toDate.value)   rows = rows.filter(r => r.posting_date <= toDate.value)

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    rows = rows.filter(r =>
      (r.name || '').toLowerCase().includes(q) ||
      (r.party_name || '').toLowerCase().includes(q) ||
      (r.mode_of_payment || '').toLowerCase().includes(q) ||
      (r.reference_no || '').toLowerCase().includes(q)
    )
  }
  return rows
})

const summaryStats = computed(() => {
  const all = (payments.data || []) as any[]
  const submitted = all.filter(r => r.docstatus === 1)
  const received = submitted.filter(r => r.payment_type === 'Receive')
  const paid     = submitted.filter(r => r.payment_type === 'Pay')
  return {
    totalReceived: received.reduce((s, r) => s + Number(r.received_amount || 0), 0),
    totalPaid:     paid.reduce((s, r) => s + Number(r.paid_amount || 0), 0),
    countReceived: received.length,
    countPaid:     paid.length,
    currency: 'INR',
  }
})

const isLoading = computed(() => payments.loading)
const hasData   = computed(() => (payments.data || []).length > 0)

// ─── WATCHERS ─────────────────────────────────────────────────────────────────
watch(
  () => props.customer,
  (customer) => {
    if (customer) {
      payments.update({
        filters: [['party_type', '=', 'Customer'], ['party', '=', customer]]
      })
      payments.reload()
    }
  },
  { immediate: true }
)

// ─── ACTIONS ──────────────────────────────────────────────────────────────────
function toggleExpand(name: string) {
  if (expandedRow.value === name) {
    expandedRow.value = null
    detailData.value  = null
  } else {
    expandedRow.value = name
    detailData.value  = null
    peDetail.fetch({ name })
  }
}

function handleCancel(name: string) {
  openConfirm({
    title: 'Cancel Payment Entry',
    message: `Are you sure you want to cancel ${name}? This will reverse the accounting entries.`,
    confirmLabel: 'Yes, Cancel',
    confirmClass: 'bg-orange-600 hover:bg-orange-700 text-white',
    onConfirm: () => {
      confirmDialog.value.show = false
      processingId.value = name
      cancelPE.submit({ doctype: 'Payment Entry', name })
    },
  })
}

function handleDelete(name: string) {
  openConfirm({
    title: 'Delete Payment Entry',
    message: `Delete ${name} permanently? This cannot be undone.`,
    confirmLabel: 'Yes, Delete',
    confirmClass: 'bg-red-600 hover:bg-red-700 text-white',
    onConfirm: () => {
      confirmDialog.value.show = false
      processingId.value = name
      deletePE.submit({ doctype: 'Payment Entry', name })
    },
  })
}

function clearFilters() {
  fromDate.value    = ''
  toDate.value      = ''
  searchQuery.value = ''
  typeFilter.value  = 'all'
}
</script>

<template>
  <div class="relative min-h-[200px]">

    <!-- ══ TOAST ══ -->
    <div class="fixed top-4 right-4 z-[200] flex flex-col gap-2 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts" :key="t.id"
          :class="[
            'flex items-center gap-2 px-4 py-3 rounded-2xl shadow-xl text-sm font-semibold pointer-events-auto',
            t.type === 'success' ? 'bg-green-600 text-white' :
            t.type === 'error'   ? 'bg-red-600 text-white'   :
                                   'bg-gray-800 text-white'
          ]"
        >
          <CheckCircle2 v-if="t.type === 'success'" class="w-4 h-4 flex-shrink-0" />
          <AlertTriangle v-else-if="t.type === 'error'" class="w-4 h-4 flex-shrink-0" />
          <Info v-else class="w-4 h-4 flex-shrink-0" />
          <span class="max-w-xs">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>

    <!-- ══ CONFIRM DIALOG ══ -->
    <Transition name="fade">
      <div v-if="confirmDialog.show" class="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-auto p-6">
          <div class="flex items-start gap-3 mb-4">
            <div class="p-2 bg-orange-50 rounded-xl flex-shrink-0">
              <AlertTriangle class="w-5 h-5 text-orange-500" />
            </div>
            <div>
              <h3 class="text-sm font-black text-gray-900 mb-1">{{ confirmDialog.title }}</h3>
              <p class="text-xs text-gray-500 leading-relaxed">{{ confirmDialog.message }}</p>
            </div>
          </div>
          <div class="flex gap-2 justify-end">
            <button @click="confirmDialog.show = false"
              class="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-xs font-bold text-gray-600 transition-colors">
              Cancel
            </button>
            <button @click="confirmDialog.onConfirm()"
              :class="['px-4 py-2 rounded-xl text-xs font-bold transition-colors', confirmDialog.confirmClass]">
              {{ confirmDialog.confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ══ HEADER ══ -->
    <div class="border-b border-gray-100 bg-gray-50/60">

      <!-- Row A: Title + stats + refresh -->
      <div class="flex flex-wrap items-center gap-2 px-3 sm:px-5 pt-3 pb-2">
        <div class="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
          <div class="p-1.5 sm:p-2 bg-violet-600 rounded-lg sm:rounded-xl text-white shadow flex-shrink-0">
            <CreditCard class="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div class="min-w-0">
            <h2 class="text-sm sm:text-base font-black tracking-tight leading-tight">Payment Entries</h2>
            <p class="text-[10px] sm:text-xs text-gray-400 font-medium">
              {{ filteredRows.length }} entries
              <span v-if="typeFilter !== 'all'"> · {{ typeFilter === 'Receive' ? 'Received only' : 'Paid only' }}</span>
            </p>
          </div>
        </div>

        <button
          @click="payments.reload()"
          :class="['flex items-center gap-1.5 px-2.5 sm:px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-600 transition-all', isLoading ? 'opacity-60 pointer-events-none' : '']"
        >
          <RefreshCcw :class="['w-3.5 h-3.5 flex-shrink-0', isLoading ? 'animate-spin' : '']" />
          <span class="hidden sm:inline">Refresh</span>
        </button>
      </div>

      <!-- Summary Stats -->
      <div v-if="hasData" class="grid grid-cols-2 gap-2 px-3 sm:px-5 pb-2.5">
        <div class="bg-green-50 border border-green-100 rounded-xl px-3 py-2.5 flex items-center gap-2">
          <ArrowDownCircle class="w-4 h-4 text-green-500 flex-shrink-0" />
          <div class="min-w-0">
            <p class="text-[9px] font-bold text-green-500 uppercase tracking-wide">Total Received</p>
            <p class="text-xs sm:text-sm font-black text-green-700 truncate">
              {{ props.formatCurrency(summaryStats.totalReceived, summaryStats.currency) }}
            </p>
          </div>
          <span class="ml-auto text-[9px] font-black text-green-400 bg-green-100 px-1.5 py-0.5 rounded-full">
            {{ summaryStats.countReceived }}
          </span>
        </div>
        <div class="bg-red-50 border border-red-100 rounded-xl px-3 py-2.5 flex items-center gap-2">
          <ArrowUpCircle class="w-4 h-4 text-red-400 flex-shrink-0" />
          <div class="min-w-0">
            <p class="text-[9px] font-bold text-red-400 uppercase tracking-wide">Total Paid</p>
            <p class="text-xs sm:text-sm font-black text-red-600 truncate">
              {{ props.formatCurrency(summaryStats.totalPaid, summaryStats.currency) }}
            </p>
          </div>
          <span class="ml-auto text-[9px] font-black text-red-400 bg-red-100 px-1.5 py-0.5 rounded-full">
            {{ summaryStats.countPaid }}
          </span>
        </div>
      </div>

      <!-- Row B: Filters -->
      <div class="flex flex-wrap items-center gap-2 px-3 sm:px-5 pb-3">

        <!-- Search -->
        <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 flex-1 min-w-[140px] max-w-[260px]">
          <Search class="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
          <input
            v-model="searchQuery" placeholder="Search entries…"
            class="text-[10px] sm:text-xs text-gray-700 bg-transparent outline-none border-none w-full min-w-0 font-medium placeholder-gray-300"
          />
          <button v-if="searchQuery" @click="searchQuery = ''" class="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0">
            <XCircle class="w-3 h-3" />
          </button>
        </div>

        <!-- Type Filter -->
        <div class="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-1 flex-shrink-0">
          <button
            v-for="opt in [{ key: 'all', label: 'All' }, { key: 'Receive', label: 'Received' }, { key: 'Pay', label: 'Paid' }]"
            :key="opt.key"
            @click="typeFilter = opt.key as any"
            :class="[
              'px-2.5 py-1 rounded-md text-[10px] font-bold transition-all whitespace-nowrap',
              typeFilter === opt.key
                ? opt.key === 'Receive' ? 'bg-green-600 text-white shadow-sm'
                  : opt.key === 'Pay'   ? 'bg-red-500 text-white shadow-sm'
                  : 'bg-gray-900 text-white shadow-sm'
                : 'text-gray-400 hover:text-gray-600'
            ]"
          >{{ opt.label }}</button>
        </div>

        <!-- Date From -->
        <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 flex-shrink-0">
          <span class="text-[9px] sm:text-[10px] font-bold text-gray-400 uppercase tracking-wide whitespace-nowrap select-none">From</span>
          <input type="date" v-model="fromDate" :max="toDate || undefined"
            class="text-[10px] sm:text-xs font-semibold text-gray-700 bg-transparent outline-none border-none w-[108px] sm:w-[122px] cursor-pointer" />
          <button v-if="fromDate" @click="fromDate = ''" class="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0 ml-0.5">
            <XCircle class="w-3 h-3" />
          </button>
        </div>

        <!-- Date To -->
        <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 flex-shrink-0">
          <span class="text-[9px] sm:text-[10px] font-bold text-gray-400 uppercase tracking-wide whitespace-nowrap select-none">To</span>
          <input type="date" v-model="toDate" :min="fromDate || undefined"
            class="text-[10px] sm:text-xs font-semibold text-gray-700 bg-transparent outline-none border-none w-[108px] sm:w-[122px] cursor-pointer" />
          <button v-if="toDate" @click="toDate = ''" class="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0 ml-0.5">
            <XCircle class="w-3 h-3" />
          </button>
        </div>

        <button v-if="hasDateFilter || searchQuery || typeFilter !== 'all'" @click="clearFilters"
          class="flex items-center gap-1 text-[10px] font-bold text-red-500 bg-red-50 border border-red-100 px-2 py-1.5 rounded-lg hover:bg-red-100 transition-all whitespace-nowrap">
          <XCircle class="w-3 h-3" /> Clear
        </button>
      </div>
    </div>

    <!-- ══ LOADING SKELETON ══ -->
    <div v-if="isLoading && !hasData" class="divide-y divide-gray-100">
      <div v-for="i in 5" :key="i" class="flex items-center gap-3 px-4 sm:px-6 py-4">
        <div class="w-8 h-8 bg-gray-100 rounded-xl animate-pulse flex-shrink-0" />
        <div class="flex-1 space-y-1.5">
          <div class="h-3 bg-gray-100 rounded-md animate-pulse w-2/5" />
          <div class="h-2.5 bg-gray-100 rounded-md animate-pulse w-3/5" />
        </div>
        <div class="h-3 bg-gray-100 rounded-md animate-pulse w-20" />
      </div>
    </div>

    <!-- ══ EMPTY STATE ══ -->
    <div v-else-if="!isLoading && !hasData"
      class="flex flex-col items-center justify-center py-20 sm:py-28 text-center px-6">
      <div class="p-4 bg-violet-50 rounded-2xl mb-4">
        <CreditCard class="w-10 h-10 text-violet-200" />
      </div>
      <p class="text-sm font-black text-gray-400">No Payment Entries</p>
      <p class="text-xs text-gray-300 mt-1.5 max-w-xs leading-relaxed">
        Payment entries for this customer will appear here once recorded.
      </p>
    </div>

    <!-- ══ NO RESULTS ══ -->
    <div v-else-if="!isLoading && hasData && filteredRows.length === 0"
      class="flex flex-col items-center justify-center py-16 text-center px-6">
      <Search class="w-8 h-8 text-gray-200 mb-3" />
      <p class="text-sm font-black text-gray-400">No results</p>
      <p class="text-xs text-gray-300 mt-1">Try adjusting your filters.</p>
      <button @click="clearFilters" class="mt-3 text-xs font-bold text-violet-600 hover:underline">Clear filters</button>
    </div>

    <!-- ══ LIST ══ -->
    <div v-else class="divide-y divide-gray-100/80">
      <div v-for="row in filteredRows" :key="row.name">

        <!-- Row -->
        <div
          @click="toggleExpand(row.name)"
          :class="[
            'flex items-center gap-2 sm:gap-3 px-3 sm:px-5 py-3 cursor-pointer transition-all select-none',
            expandedRow === row.name ? 'bg-violet-50/40' : 'hover:bg-gray-50/70 active:bg-gray-100/60'
          ]"
        >

          <!-- Mode Icon -->
          <div :class="[
            'w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm',
            row.payment_type === 'Receive'
              ? 'bg-green-100 text-green-600'
              : row.payment_type === 'Pay'
              ? 'bg-red-100 text-red-500'
              : 'bg-gray-100 text-gray-500'
          ]">
            <component :is="getModeIcon(row.mode_of_payment)" class="w-4 h-4 sm:w-4.5 sm:h-4.5" />
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="text-xs sm:text-sm font-black text-gray-900 truncate">{{ row.name }}</span>
              <span :class="[
                'text-[9px] font-black px-1.5 py-0.5 rounded-full leading-none whitespace-nowrap',
                row.payment_type === 'Receive' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
              ]">
                {{ row.payment_type === 'Receive' ? '↓ Received' : '↑ Paid' }}
              </span>
              <!-- Status -->
              <span :class="[
                'text-[9px] font-bold px-1.5 py-0.5 rounded-full leading-none whitespace-nowrap',
                row.docstatus === 1 ? 'bg-emerald-50 text-emerald-600' :
                row.docstatus === 2 ? 'bg-gray-100 text-gray-400' :
                                     'bg-orange-50 text-orange-500'
              ]">
                {{ row.docstatus === 1 ? 'Submitted' : row.docstatus === 2 ? 'Cancelled' : 'Draft' }}
              </span>
            </div>
            <div class="flex items-center gap-1.5 mt-0.5 flex-wrap">
              <Calendar class="w-2.5 h-2.5 text-gray-300 flex-shrink-0" />
              <span class="text-[10px] text-gray-400 font-medium">{{ row.posting_date }}</span>
              <span v-if="row.mode_of_payment" class="text-[10px] text-gray-300">·</span>
              <span v-if="row.mode_of_payment" class="text-[10px] text-gray-400 font-medium truncate">{{ row.mode_of_payment }}</span>
              <span v-if="row.reference_no" class="text-[10px] text-gray-300">·</span>
              <span v-if="row.reference_no" class="text-[10px] text-violet-500 font-semibold truncate">Ref: {{ row.reference_no }}</span>
            </div>
          </div>

          <!-- Amount -->
          <div class="text-right flex-shrink-0">
            <p :class="[
              'text-xs sm:text-sm font-black',
              row.payment_type === 'Receive' ? 'text-green-700' : 'text-red-600'
            ]">
              {{ props.formatCurrency(Number(row.received_amount || row.paid_amount || 0), 'INR') }}
            </p>
          </div>

          <!-- Expand Chevron -->
          <component
            :is="expandedRow === row.name ? ChevronDown : ChevronRight"
            class="w-4 h-4 text-gray-300 flex-shrink-0 transition-transform"
          />
        </div>

        <!-- ══ EXPANDED DETAIL ══ -->
        <Transition
          enter-active-class="transition-all duration-200 ease-out"
          leave-active-class="transition-all duration-150 ease-in"
          enter-from-class="opacity-0 -translate-y-1"
          leave-to-class="opacity-0 -translate-y-1"
        >
          <div v-if="expandedRow === row.name" class="border-t border-gray-100 bg-gray-50/70 px-3 sm:px-6 py-4">

            <!-- Loading -->
            <div v-if="peDetail.loading && !detailData" class="space-y-2">
              <div v-for="i in 4" :key="i" class="h-8 bg-gray-200/60 rounded-lg animate-pulse" />
            </div>

            <!-- Detail -->
            <div v-else-if="detailData && detailData.name === row.name" class="space-y-4">

              <!-- Meta Cards -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div class="bg-white rounded-xl p-3 border border-gray-100">
                  <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Mode</p>
                  <p class="text-xs font-black text-gray-800 truncate">{{ detailData.mode_of_payment || '—' }}</p>
                </div>
                <div class="bg-white rounded-xl p-3 border border-gray-100">
                  <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Paid Amount</p>
                  <p class="text-xs font-black text-gray-800">{{ props.formatCurrency(Number(detailData.paid_amount || 0), detailData.currency) }}</p>
                </div>
                <div class="bg-white rounded-xl p-3 border border-gray-100">
                  <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Ref No.</p>
                  <p class="text-xs font-black text-violet-600 truncate">{{ detailData.reference_no || '—' }}</p>
                </div>
                <div class="bg-white rounded-xl p-3 border border-gray-100">
                  <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Ref Date</p>
                  <p class="text-xs font-black text-gray-800">{{ detailData.reference_date || '—' }}</p>
                </div>
              </div>

              <!-- Account Info -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="bg-white rounded-xl p-3 border border-gray-100">
                  <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Paid From</p>
                  <p class="text-xs font-semibold text-gray-700 truncate">{{ detailData.paid_from || '—' }}</p>
                </div>
                <div class="bg-white rounded-xl p-3 border border-gray-100">
                  <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Paid To</p>
                  <p class="text-xs font-semibold text-gray-700 truncate">{{ detailData.paid_to || '—' }}</p>
                </div>
              </div>

              <!-- Invoice References Table -->
              <div v-if="detailData.references?.length" class="bg-white border border-gray-100 rounded-xl overflow-hidden">
                <div class="px-4 py-2.5 bg-gray-50 border-b border-gray-100 text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                  <FileText class="w-3 h-3" />
                  Invoice References
                </div>
                <div class="divide-y divide-gray-100/80 max-h-44 overflow-y-auto overscroll-contain">
                  <div
                    v-for="ref in detailData.references" :key="ref.name"
                    class="grid grid-cols-[1fr_0.6fr_0.7fr] gap-2 px-4 py-2.5 items-center"
                  >
                    <div class="min-w-0">
                      <p class="text-xs font-semibold text-gray-800 truncate">{{ ref.reference_name }}</p>
                      <p class="text-[9px] text-gray-400 truncate">{{ ref.reference_doctype }}</p>
                    </div>
                    <div class="text-center">
                      <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-0.5">Outstanding</p>
                      <p class="text-xs font-black text-red-500">{{ props.formatCurrency(Number(ref.outstanding_amount || 0), detailData.currency) }}</p>
                    </div>
                    <div class="text-right">
                      <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-0.5">Allocated</p>
                      <p class="text-xs font-black text-green-700">{{ props.formatCurrency(Number(ref.allocated_amount || 0), detailData.currency) }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Remarks -->
              <div v-if="detailData.remarks" class="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
                <p class="text-[9px] text-amber-600 font-bold uppercase tracking-wide mb-1">Remarks</p>
                <p class="text-xs text-amber-800 font-medium leading-relaxed">{{ detailData.remarks }}</p>
              </div>

              <!-- Actions -->
              <div class="flex flex-wrap gap-2 justify-end pt-1">

                <!-- Cancel (submitted) -->
                <button
                  v-if="detailData.docstatus === 1"
                  @click.stop="handleCancel(row.name)"
                  :disabled="processingId === row.name"
                  class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-orange-50 hover:bg-orange-100 disabled:opacity-60 text-orange-600 text-xs font-bold border border-orange-200 transition-colors"
                >
                  <RefreshCcw v-if="processingId === row.name" class="w-3.5 h-3.5 animate-spin" />
                  <Ban v-else class="w-3.5 h-3.5" />
                  Cancel
                </button>

                <!-- Delete (draft or cancelled) -->
                <button
                  v-if="detailData.docstatus === 0 || detailData.docstatus === 2"
                  @click.stop="handleDelete(row.name)"
                  :disabled="processingId === row.name"
                  class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-50 hover:bg-red-100 disabled:opacity-60 text-red-600 text-xs font-bold border border-red-200 transition-colors"
                >
                  <RefreshCcw v-if="processingId === row.name" class="w-3.5 h-3.5 animate-spin" />
                  <Trash2 v-else class="w-3.5 h-3.5" />
                  Delete
                </button>
              </div>
            </div>

            <!-- Fallback skeleton -->
            <div v-else class="space-y-2">
              <div v-for="i in 3" :key="i" class="h-8 bg-gray-200/60 rounded-lg animate-pulse" />
            </div>
          </div>
        </Transition>

      </div>
    </div>

    <!-- Loading more -->
    <div v-if="isLoading && hasData" class="flex justify-center py-4">
      <RefreshCcw class="w-5 h-5 text-gray-400 animate-spin" />
    </div>

  </div>
</template>

<style scoped>
.toast-enter-active { transition: all 0.3s ease-out; }
.toast-leave-active { transition: all 0.2s ease-in; }
.toast-enter-from   { opacity: 0; transform: translateY(-8px) scale(0.96); }
.toast-leave-to     { opacity: 0; transform: translateY(-4px) scale(0.98); }

.fade-enter-active { transition: opacity 0.15s ease; }
.fade-leave-active { transition: opacity 0.1s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
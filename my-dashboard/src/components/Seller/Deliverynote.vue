<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { createListResource, createResource } from 'frappe-ui'
import {
  Truck, RefreshCcw, XCircle, ChevronDown, ChevronRight,
  Package, Calendar, CheckCircle2, Clock, AlertCircle,
  Ban, Search, Send, Trash2, AlertTriangle, Printer, X, Loader2,
  Download, ExternalLink
} from 'lucide-vue-next'

const props = defineProps<{
  seller?: string
  customer?: string
  formatCurrency: (amount: number, currency?: string) => string
}>()

// ─── STATE ────────────────────────────────────────────────────────────────────
const searchQuery      = ref('')
const fromDate         = ref('')
const toDate           = ref('')
const statusFilter     = ref<string>('all')
const expandedRow      = ref<string | null>(null)
const detailData       = ref<any>(null)
const processingId     = ref<string>('')
const processingAction = ref<string>('')

// ── Print modal (blob-based — works via Vite→Frappe proxy, cross-origin safe) ──
const printModal = ref<{
  show: boolean
  loading: boolean
  blobUrl: string
  docName: string
  printFormat: string
  error: string
}>({ show: false, loading: false, blobUrl: '', docName: '', printFormat: '', error: '' })

const confirmDialog = ref<{
  show: boolean; title: string; message: string
  confirmLabel: string; confirmClass: string; onConfirm: () => void
}>({ show: false, title: '', message: '', confirmLabel: '', confirmClass: '', onConfirm: () => {} })

const errorDialog = ref({ show: false, message: '' })

const statusOptions = [
  { key: 'all', label: 'All' },
  { key: 'Draft', label: 'Draft' },
  { key: 'Submitted', label: 'Submitted' },
  { key: 'Cancelled', label: 'Cancelled' },
]

// ─── RESOURCES ────────────────────────────────────────────────────────────────
// ⚠️  against_sales_order = child-table field → NOT allowed in frappe.client.get_list
//     Causes 417 EXPECTATION FAILED. Only fetch in detail via frappe.client.get (full doc).
const deliveries = createListResource({
  doctype: 'Delivery Note',
  fields: [
    'name', 'customer', 'customer_name', 'status', 'posting_date',
    'grand_total', 'currency', 'docstatus', 'lr_no', 'lr_date',
    'per_billed', 'per_returned', 'set_warehouse', 'shipping_address_name',
  ],
  filters: [],
  orderBy: 'posting_date desc',
  pageLength: 200,
  auto: false,
})

const dnDetail = createResource({
  url: 'frappe.client.get',
  makeParams: (v: { name: string }) => ({ doctype: 'Delivery Note', name: v.name }),
  onSuccess(data: any) { detailData.value = data },
})

const submitDN = createResource({
  url: 'frappe.client.submit',
  onSuccess() {
    processingId.value = ''; processingAction.value = ''
    deliveries.reload()
    if (expandedRow.value) dnDetail.fetch({ name: expandedRow.value })
  },
  onError(err: any) {
    processingId.value = ''; processingAction.value = ''
    showError(err?.message || err?.exc_type || 'Submit failed')
  },
})

const cancelDN = createResource({
  url: 'frappe.client.cancel',
  onSuccess() {
    processingId.value = ''; processingAction.value = ''
    deliveries.reload()
    if (expandedRow.value) dnDetail.fetch({ name: expandedRow.value })
  },
  onError(err: any) {
    processingId.value = ''; processingAction.value = ''
    showError(err?.message || err?.exc_type || 'Cancel failed')
  },
})

const deleteDN = createResource({
  url: 'frappe.client.delete',
  onSuccess() {
    processingId.value = ''; processingAction.value = ''
    expandedRow.value = null; detailData.value = null
    deliveries.reload()
  },
  onError(err: any) {
    processingId.value = ''; processingAction.value = ''
    showError(err?.message || err?.exc_type || 'Delete failed')
  },
})

// ─── WATCHERS ─────────────────────────────────────────────────────────────────
watch(
  () => [props.customer, props.seller],
  ([customer]) => {
    const filters: any[] = []
    if (customer) filters.push(['customer', '=', customer])
    deliveries.update({ filters })
    deliveries.reload()
  },
  { immediate: true },
)

// ─── COMPUTED ─────────────────────────────────────────────────────────────────
const filtered = computed<any[]>(() => {
  let rows = (deliveries.data || []) as any[]
  if (statusFilter.value !== 'all')
    rows = rows.filter(r => {
      if (statusFilter.value === 'Draft')     return r.docstatus === 0
      if (statusFilter.value === 'Submitted') return r.docstatus === 1
      if (statusFilter.value === 'Cancelled') return r.docstatus === 2
      return true
    })
  if (fromDate.value) rows = rows.filter(r => r.posting_date >= fromDate.value)
  if (toDate.value)   rows = rows.filter(r => r.posting_date <= toDate.value)
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    rows = rows.filter(r =>
      r.name?.toLowerCase().includes(q) ||
      r.customer_name?.toLowerCase().includes(q),
    )
  }
  return rows
})

const hasDateFilter = computed(() => fromDate.value !== '' || toDate.value !== '')
const isLoading     = computed(() => deliveries.loading)
const hasData       = computed(() => (deliveries.data || []).length > 0)

const summary = computed(() => {
  const rows = (deliveries.data || []) as any[]
  return {
    total:     rows.length,
    draft:     rows.filter(r => r.docstatus === 0).length,
    submitted: rows.filter(r => r.docstatus === 1).length,
    cancelled: rows.filter(r => r.docstatus === 2).length,
  }
})

function clearFilters() {
  fromDate.value = ''; toDate.value = ''; statusFilter.value = 'all'; searchQuery.value = ''
}

// ─── HELPERS ──────────────────────────────────────────────────────────────────
type BadgeTheme = 'gray' | 'blue' | 'green' | 'red' | 'orange' | 'purple'

function getStatusInfo(row: any): { label: string; theme: BadgeTheme; icon: any } {
  if (row.docstatus === 2)   return { label: 'Cancelled',     theme: 'gray',   icon: Ban          }
  if (row.docstatus === 0)   return { label: 'Draft',         theme: 'orange', icon: Clock        }
  if (row.per_billed >= 100) return { label: 'Completed',     theme: 'green',  icon: CheckCircle2 }
  if (row.per_billed > 0)    return { label: 'Partly Billed', theme: 'blue',   icon: AlertCircle  }
  return { label: 'To Bill', theme: 'purple', icon: Package }
}

const themeClasses: Record<BadgeTheme, string> = {
  gray:   'bg-gray-100 text-gray-600',
  blue:   'bg-blue-50 text-blue-700',
  green:  'bg-green-50 text-green-700',
  red:    'bg-red-50 text-red-700',
  orange: 'bg-orange-50 text-orange-700',
  purple: 'bg-violet-50 text-violet-700',
}

function toggleExpand(name: string) {
  if (expandedRow.value === name) { expandedRow.value = null; detailData.value = null }
  else { expandedRow.value = name; detailData.value = null; dnDetail.fetch({ name }) }
}

function showError(msg: string) {
  const clean = msg.replace(/<[^>]*>/g, '').trim().split('\n')[0]
  errorDialog.value = { show: true, message: clean }
}

// ─── PRINT — BLOB via Vite proxy (port 5173 → Frappe 8000) ───────────────────
// Step 1: Fetch the default print format for this doctype from ERPNext
// Step 2: Use that format (or 'Standard' fallback) to download PDF as blob
// Step 3: Show blob URL in embedded <iframe> inside full-screen modal
// This avoids CORS / cross-origin redirect issues between Vite:5173 & Frappe:8000

async function getDefaultPrintFormat(doctype: string): Promise<string> {
  try {
    // Frappe API to get default print format set in Print Format List
    const res = await fetch(
      `/api/method/frappe.client.get_value?doctype=Property+Setter` +
      `&filters=${encodeURIComponent(JSON.stringify([
        ['doc_type', '=', doctype],
        ['property', '=', 'default_print_format'],
      ]))}` +
      `&fieldname=value`,
      { credentials: 'include' }
    )
    if (res.ok) {
      const data = await res.json()
      const fmt = data?.message?.value
      if (fmt && fmt.trim()) return fmt.trim()
    }
  } catch (_) { /* fall through */ }

  // Fallback: query Print Format where doc_type = doctype AND is_default = 1
  try {
    const res = await fetch(
      `/api/resource/Print+Format?filters=${encodeURIComponent(JSON.stringify([
        ['doc_type', '=', doctype],
        ['disabled', '=', 0],
      ]))}` +
      `&fields=${encodeURIComponent(JSON.stringify(['name', 'default_format']))}` +
      `&order_by=modified+desc&limit=50`,
      { credentials: 'include' }
    )
    if (res.ok) {
      const data = await res.json()
      const formats: any[] = data?.data || []
      // Find one marked as default, or first in list
      const def = formats.find((f: any) => f.default_format === 1)
      if (def?.name) return def.name
      if (formats[0]?.name) return formats[0].name
    }
  } catch (_) { /* fall through */ }

  return 'Standard'
}

async function openPrint(name: string) {
  // Reset modal, show loading
  printModal.value = { show: true, loading: true, blobUrl: '', docName: name, printFormat: '', error: '' }

  try {
    // 1️⃣ Detect default print format
    const fmt = await getDefaultPrintFormat('Delivery Note')
    printModal.value.printFormat = fmt

    // 2️⃣ Fetch PDF as blob — goes through Vite proxy to Frappe :8000
    //    /api/... is proxied by vite.config: target http://127.0.0.1:8000
    const pdfUrl =
      `/api/method/frappe.utils.print_format.download_pdf` +
      `?doctype=${encodeURIComponent('Delivery Note')}` +
      `&name=${encodeURIComponent(name)}` +
      `&format=${encodeURIComponent(fmt)}` +
      `&no_letterhead=0` +
      `&letterhead=No+Letterhead`

    const res = await fetch(pdfUrl, { credentials: 'include' })

    if (!res.ok) {
      // If chosen format fails, retry with Standard
      if (fmt !== 'Standard') {
        const fallback = await fetch(
          `/api/method/frappe.utils.print_format.download_pdf` +
          `?doctype=${encodeURIComponent('Delivery Note')}` +
          `&name=${encodeURIComponent(name)}` +
          `&format=Standard&no_letterhead=0`,
          { credentials: 'include' }
        )
        if (!fallback.ok) throw new Error(`HTTP ${fallback.status} — PDF generation failed`)
        const blob = await fallback.blob()
        const blobUrl = URL.createObjectURL(blob)
        printModal.value = { show: true, loading: false, blobUrl, docName: name, printFormat: 'Standard (fallback)', error: '' }
        return
      }
      throw new Error(`HTTP ${res.status} — PDF generation failed`)
    }

    const blob = await res.blob()
    const blobUrl = URL.createObjectURL(blob)
    printModal.value = { show: true, loading: false, blobUrl, docName: name, printFormat: fmt, error: '' }

  } catch (e: any) {
    const msg = e?.message || 'Could not load PDF'
    printModal.value = { show: true, loading: false, blobUrl: '', docName: name, printFormat: '', error: msg }
  }
}

function closePrint() {
  if (printModal.value.blobUrl) URL.revokeObjectURL(printModal.value.blobUrl)
  printModal.value = { show: false, loading: false, blobUrl: '', docName: '', printFormat: '', error: '' }
}

function downloadPdf() {
  if (!printModal.value.blobUrl) return
  const a = document.createElement('a')
  a.href = printModal.value.blobUrl
  a.download = `${printModal.value.docName}.pdf`
  a.click()
}

// ─── ACTIONS ──────────────────────────────────────────────────────────────────
function askConfirm(opts: {
  title: string; message: string; confirmLabel: string; confirmClass: string; onConfirm: () => void
}) {
  confirmDialog.value = { show: true, ...opts }
}

function handleSubmit(name: string) {
  if (!detailData.value) return
  askConfirm({
    title: 'Submit Delivery Note',
    message: `Submit ${name}? Stock entries will be posted and cannot be easily undone.`,
    confirmLabel: 'Submit',
    confirmClass: 'bg-blue-600 hover:bg-blue-700 text-white',
    onConfirm: () => {
      confirmDialog.value.show = false
      processingId.value = name; processingAction.value = 'submit'
      submitDN.fetch({ doc: detailData.value })
    },
  })
}

function handleCancel(name: string) {
  askConfirm({
    title: 'Cancel Delivery Note',
    message: `Cancel ${name}? Stock entries will be reversed.`,
    confirmLabel: 'Cancel DN',
    confirmClass: 'bg-red-600 hover:bg-red-700 text-white',
    onConfirm: () => {
      confirmDialog.value.show = false
      processingId.value = name; processingAction.value = 'cancel'
      cancelDN.fetch({ doctype: 'Delivery Note', name })
    },
  })
}

function handleDelete(name: string) {
  askConfirm({
    title: 'Delete Delivery Note',
    message: `Permanently delete ${name}? This cannot be undone.`,
    confirmLabel: 'Delete',
    confirmClass: 'bg-red-700 hover:bg-red-800 text-white',
    onConfirm: () => {
      confirmDialog.value.show = false
      processingId.value = name; processingAction.value = 'delete'
      deleteDN.fetch({ doctype: 'Delivery Note', name })
    },
  })
}
</script>

<template>
  <div class="w-full min-w-0">

    <!-- ══════════════════════════════════════════════════════════════
         PRINT MODAL — full-screen blob PDF viewer
         PDF loaded via Vite proxy → Frappe :8000 (no CORS issues)
    ══════════════════════════════════════════════════════════════ -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-all duration-250 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-all duration-200"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="printModal.show" class="fixed inset-0 z-[1000] flex flex-col bg-gray-950">

          <!-- Modal header -->
          <div class="flex items-center gap-3 bg-gray-900 px-4 py-3 border-b border-white/10 flex-shrink-0 shadow-lg">
            <div class="p-1.5 bg-white/10 rounded-lg flex-shrink-0">
              <Printer class="w-4 h-4 text-white" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-black text-white truncate">{{ printModal.docName }}</p>
              <p v-if="printModal.printFormat" class="text-[10px] text-gray-400 font-medium">
                Format: <span class="text-blue-400">{{ printModal.printFormat }}</span>
              </p>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <!-- Download button -->
              <button
                v-if="printModal.blobUrl"
                @click="downloadPdf"
                class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold transition-colors"
              >
                <Download class="w-3.5 h-3.5" />
                <span class="hidden sm:inline">Download</span>
              </button>
              <!-- Close button -->
              <button
                @click="closePrint"
                class="flex items-center justify-center w-9 h-9 rounded-xl bg-white/10 hover:bg-red-500 text-white transition-colors"
              >
                <X class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- Loading state -->
          <div v-if="printModal.loading" class="flex-1 flex items-center justify-center">
            <div class="flex flex-col items-center gap-4">
              <div class="relative">
                <div class="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center">
                  <Printer class="w-7 h-7 text-white/60" />
                </div>
                <div class="absolute inset-0 rounded-2xl border-2 border-blue-400 border-t-transparent animate-spin" />
              </div>
              <div class="text-center">
                <p class="text-sm font-bold text-white">Preparing PDF…</p>
                <p class="text-xs text-gray-500 mt-0.5">Detecting default print format</p>
              </div>
            </div>
          </div>

          <!-- Error state -->
          <div v-else-if="printModal.error" class="flex-1 flex items-center justify-center p-6">
            <div class="bg-red-950/50 border border-red-800 rounded-2xl p-6 max-w-sm w-full text-center space-y-4">
              <div class="w-12 h-12 rounded-2xl bg-red-500/20 flex items-center justify-center mx-auto">
                <AlertTriangle class="w-6 h-6 text-red-400" />
              </div>
              <div>
                <p class="text-sm font-black text-red-300">PDF Load Failed</p>
                <p class="text-xs text-red-500 mt-1 break-words">{{ printModal.error }}</p>
              </div>
              <button @click="closePrint" class="w-full py-2 bg-red-700 hover:bg-red-600 text-white text-xs font-bold rounded-xl transition-colors">
                Close
              </button>
            </div>
          </div>

          <!-- PDF blob embedded — works on Chrome/Edge/Firefox desktop & Android -->
          <iframe
            v-else-if="printModal.blobUrl"
            :src="printModal.blobUrl"
            class="flex-1 w-full border-0"
            title="Print Preview"
          />

        </div>
      </Transition>
    </Teleport>

    <!-- ══ CONFIRM DIALOG ══════════════════════════════════════════ -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 scale-95"
        enter-to-class="opacity-100 scale-100"
        leave-active-class="transition-all duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0 scale-95"
      >
        <div
          v-if="confirmDialog.show"
          class="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
          @click.self="confirmDialog.show = false"
        >
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 space-y-4">
            <div class="flex items-start gap-3">
              <div class="p-2 bg-orange-50 rounded-xl flex-shrink-0">
                <AlertTriangle class="w-5 h-5 text-orange-500" />
              </div>
              <div>
                <h3 class="text-sm font-black text-gray-900">{{ confirmDialog.title }}</h3>
                <p class="text-xs text-gray-500 mt-1 leading-relaxed">{{ confirmDialog.message }}</p>
              </div>
            </div>
            <div class="flex gap-2 justify-end">
              <button
                @click="confirmDialog.show = false"
                class="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-xs font-bold text-gray-600 transition-colors"
              >
                Go Back
              </button>
              <button
                @click="confirmDialog.onConfirm()"
                :class="['px-4 py-2 rounded-xl text-xs font-bold transition-colors', confirmDialog.confirmClass]"
              >
                {{ confirmDialog.confirmLabel }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ══ ERROR DIALOG ═════════════════════════════════════════════ -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 scale-95"
        enter-to-class="opacity-100 scale-100"
        leave-active-class="transition-all duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="errorDialog.show"
          class="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
          @click.self="errorDialog.show = false"
        >
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 space-y-4">
            <div class="flex items-start gap-3">
              <div class="p-2 bg-red-50 rounded-xl flex-shrink-0">
                <AlertTriangle class="w-5 h-5 text-red-500" />
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="text-sm font-black text-gray-900">Action Failed</h3>
                <p class="text-xs text-red-600 mt-1 leading-relaxed break-words">{{ errorDialog.message }}</p>
              </div>
            </div>
            <div class="flex justify-end">
              <button
                @click="errorDialog.show = false"
                class="px-4 py-2 rounded-xl bg-gray-900 text-white text-xs font-bold hover:bg-gray-700 transition-colors"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ── Summary Cards ── -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 px-3 sm:px-5 pt-3 pb-2">
      <div class="bg-gradient-to-br from-gray-900 to-gray-700 rounded-xl p-3 text-white">
        <p class="text-[9px] font-bold uppercase tracking-wider opacity-70 mb-1">Total DNs</p>
        <p class="text-sm sm:text-base font-black leading-tight">{{ summary.total }}</p>
      </div>
      <div class="bg-gradient-to-br from-orange-500 to-amber-400 rounded-xl p-3 text-white">
        <p class="text-[9px] font-bold uppercase tracking-wider opacity-70 mb-1">Draft</p>
        <p class="text-sm sm:text-base font-black leading-tight">{{ summary.draft }}</p>
      </div>
      <div class="bg-gradient-to-br from-green-600 to-green-500 rounded-xl p-3 text-white">
        <p class="text-[9px] font-bold uppercase tracking-wider opacity-70 mb-1">Submitted</p>
        <p class="text-sm sm:text-base font-black leading-tight">{{ summary.submitted }}</p>
      </div>
      <div class="bg-gradient-to-br from-gray-500 to-gray-400 rounded-xl p-3 text-white">
        <p class="text-[9px] font-bold uppercase tracking-wider opacity-70 mb-1">Cancelled</p>
        <p class="text-sm sm:text-base font-black leading-tight">{{ summary.cancelled }}</p>
      </div>
    </div>

    <!-- ── Filters ── -->
    <div class="border-b border-gray-100 bg-gray-50/60 space-y-2.5 px-3 sm:px-5 pt-2 pb-3">
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex items-center gap-2 flex-1 min-w-0">
          <div class="p-1.5 sm:p-2 bg-gray-900 rounded-lg sm:rounded-xl text-white shadow flex-shrink-0">
            <Truck class="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div class="min-w-0">
            <h2 class="text-sm sm:text-base font-black tracking-tight leading-tight">Delivery Notes</h2>
            <p class="text-[10px] text-gray-400 font-medium mt-0.5">
              {{ filtered.length }} record{{ filtered.length !== 1 ? 's' : '' }}
              <span v-if="hasDateFilter || statusFilter !== 'all' || searchQuery" class="text-blue-500"> (filtered)</span>
            </p>
          </div>
        </div>
        <button
          @click="deliveries.reload()"
          :class="['flex items-center gap-1.5 px-2.5 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-600 transition-all', isLoading ? 'opacity-60 pointer-events-none' : '']"
        >
          <RefreshCcw :class="['w-3.5 h-3.5', isLoading ? 'animate-spin' : '']" />
          <span class="hidden sm:inline">Refresh</span>
        </button>
      </div>

      <!-- Search -->
      <div class="relative">
        <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by DN #, customer…"
          class="w-full pl-8 pr-8 py-2 text-xs sm:text-sm bg-white border border-gray-200 rounded-lg outline-none focus:border-gray-400 transition-colors"
        />
        <button v-if="searchQuery" @click="searchQuery = ''" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-300 hover:text-red-400">
          <XCircle class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Status + date filters -->
      <div class="flex flex-wrap gap-2 items-center">
        <div class="flex gap-1 flex-wrap">
          <button
            v-for="s in statusOptions"
            :key="s.key"
            @click="statusFilter = s.key"
            :class="[
              'px-2.5 py-1 rounded-full text-[10px] sm:text-xs font-bold transition-all whitespace-nowrap',
              statusFilter === s.key ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200',
            ]"
          >
            {{ s.label }}
          </button>
        </div>
        <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2 py-1.5 flex-shrink-0">
          <span class="text-[9px] font-bold text-gray-400 uppercase select-none whitespace-nowrap">From</span>
          <input
            type="date" v-model="fromDate" :max="toDate || undefined"
            class="text-[10px] sm:text-xs font-semibold text-gray-700 bg-transparent outline-none border-none w-[108px] sm:w-[122px] cursor-pointer"
          />
          <button v-if="fromDate" @click="fromDate = ''" class="text-gray-300 hover:text-red-400">
            <XCircle class="w-3 h-3" />
          </button>
        </div>
        <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2 py-1.5 flex-shrink-0">
          <span class="text-[9px] font-bold text-gray-400 uppercase select-none whitespace-nowrap">To</span>
          <input
            type="date" v-model="toDate" :min="fromDate || undefined"
            class="text-[10px] sm:text-xs font-semibold text-gray-700 bg-transparent outline-none border-none w-[108px] sm:w-[122px] cursor-pointer"
          />
          <button v-if="toDate" @click="toDate = ''" class="text-gray-300 hover:text-red-400">
            <XCircle class="w-3 h-3" />
          </button>
        </div>
        <button
          v-if="hasDateFilter || statusFilter !== 'all' || searchQuery"
          @click="clearFilters"
          class="flex items-center gap-1 text-[10px] font-bold text-red-500 bg-red-50 border border-red-100 px-2 py-1.5 rounded-lg hover:bg-red-100 transition-all whitespace-nowrap"
        >
          <XCircle class="w-3 h-3" /> Clear All
        </button>
      </div>
    </div>

    <!-- ── Loading skeleton ── -->
    <div v-if="isLoading && !hasData" class="p-6 space-y-3">
      <div v-for="i in 5" :key="i" class="h-16 bg-gray-100 rounded-xl animate-pulse" />
    </div>

    <!-- ── Empty state ── -->
    <div
      v-else-if="!isLoading && filtered.length === 0"
      class="flex flex-col items-center justify-center py-20 text-center px-4"
    >
      <div class="p-4 bg-gray-100 rounded-2xl mb-4">
        <Truck class="w-10 h-10 text-gray-300" />
      </div>
      <p class="text-sm font-black text-gray-300">No Delivery Notes Found</p>
      <p class="text-xs text-gray-300 mt-1">Try adjusting your filters</p>
    </div>

    <!-- ── Table ── -->
    <div v-else>

      <!-- Desktop column headers -->
      <div class="hidden sm:grid grid-cols-[1fr_1.4fr_0.8fr_0.8fr_0.6fr_36px] gap-2 px-5 py-2.5 border-b border-gray-100 bg-gray-50/40 text-[10px] font-black text-gray-400 uppercase tracking-widest">
        <span>DN #</span>
        <span>Customer</span>
        <span>Date</span>
        <span class="text-right">Amount</span>
        <span class="text-center">Status</span>
        <span />
      </div>

      <div class="divide-y divide-gray-100/80">
        <div v-for="row in filtered" :key="row.name">

          <!-- ── Main row ── -->
          <div
            @click="toggleExpand(row.name)"
            class="grid grid-cols-[1fr_36px] sm:grid-cols-[1fr_1.4fr_0.8fr_0.8fr_0.6fr_36px] gap-2 items-center px-3 sm:px-5 py-3 sm:py-3.5 hover:bg-gray-50/60 active:bg-gray-100/70 transition-colors cursor-pointer select-none"
          >
            <!-- Mobile layout -->
            <div class="sm:hidden flex flex-col gap-0.5 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs font-black text-gray-900 truncate">{{ row.name }}</span>
                <span :class="['inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold', themeClasses[getStatusInfo(row).theme]]">
                  <component :is="getStatusInfo(row).icon" class="w-2.5 h-2.5 flex-shrink-0" />
                  {{ getStatusInfo(row).label }}
                </span>
              </div>
              <span class="text-[10px] text-gray-500 font-medium truncate">{{ row.customer_name }}</span>
              <div class="flex items-center gap-2 flex-wrap mt-0.5">
                <span class="text-[9px] text-gray-400 flex items-center gap-0.5">
                  <Calendar class="w-2.5 h-2.5" />{{ row.posting_date }}
                </span>
                <span class="text-[10px] font-black text-gray-800">{{ formatCurrency(row.grand_total, row.currency) }}</span>
                <span v-if="row.per_billed > 0 && row.per_billed < 100" class="text-[9px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-semibold">
                  {{ row.per_billed?.toFixed(0) }}% billed
                </span>
              </div>
            </div>

            <!-- Desktop columns -->
            <span class="hidden sm:block text-xs font-black text-gray-900 truncate">{{ row.name }}</span>
            <span class="hidden sm:block text-xs text-gray-600 font-medium truncate">{{ row.customer_name }}</span>
            <span class="hidden sm:flex items-center gap-1 text-xs text-gray-500">
              <Calendar class="w-3 h-3 flex-shrink-0 text-gray-400" />{{ row.posting_date }}
            </span>
            <span class="hidden sm:block text-xs font-black text-gray-900 text-right">
              {{ formatCurrency(row.grand_total, row.currency) }}
            </span>
            <span class="hidden sm:flex justify-center">
              <span :class="['inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold whitespace-nowrap', themeClasses[getStatusInfo(row).theme]]">
                <component :is="getStatusInfo(row).icon" class="w-2.5 h-2.5 flex-shrink-0" />
                {{ getStatusInfo(row).label }}
              </span>
            </span>
            <div class="flex justify-center text-gray-400">
              <ChevronDown v-if="expandedRow === row.name" class="w-4 h-4 text-gray-700" />
              <ChevronRight v-else class="w-4 h-4" />
            </div>
          </div>

          <!-- ── Expanded detail panel ── -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition-all duration-150 ease-in"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
          >
            <div
              v-if="expandedRow === row.name"
              class="border-t border-gray-100 bg-gray-50/70 px-3 sm:px-6 py-4"
            >
              <!-- Skeleton while loading -->
              <div v-if="dnDetail.loading && !detailData" class="space-y-2">
                <div v-for="i in 4" :key="i" class="h-8 bg-gray-200/60 rounded-lg animate-pulse" />
              </div>

              <div v-else-if="detailData && detailData.name === row.name" class="space-y-4">

                <!-- Row 1: SO ref + LR + dates + billed % -->
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <!-- Against SO — only available in full doc, not get_list -->
                  <div class="col-span-2 sm:col-span-1 bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Against Sales Order</p>
                    <p class="text-xs font-black text-blue-700 truncate">
                      {{
                        detailData.items?.map((i: any) => i.against_sales_order).filter(Boolean).filter((v: string, idx: number, arr: string[]) => arr.indexOf(v) === idx).join(', ') || '—'
                      }}
                    </p>
                  </div>
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">LR Number</p>
                    <p class="text-xs font-black text-gray-800">{{ detailData.lr_no || '—' }}</p>
                  </div>
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">LR Date</p>
                    <p class="text-xs font-black text-gray-800">{{ detailData.lr_date || '—' }}</p>
                  </div>
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Billed %</p>
                    <p class="text-xs font-black text-gray-800">{{ detailData.per_billed ?? 0 }}%</p>
                  </div>
                </div>

                <!-- Row 2: Warehouse, returned, vehicle -->
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Warehouse</p>
                    <p class="text-xs font-black text-gray-800 truncate">{{ detailData.set_warehouse || '—' }}</p>
                  </div>
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">% Returned</p>
                    <p class="text-xs font-black text-gray-800">{{ detailData.per_returned ?? 0 }}%</p>
                  </div>
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Vehicle No</p>
                    <p class="text-xs font-black text-gray-800">{{ detailData.vehicle_no || '—' }}</p>
                  </div>
                </div>

                <!-- Items table -->
                <div v-if="detailData.items?.length" class="bg-white border border-gray-100 rounded-xl overflow-hidden">
                  <div class="grid grid-cols-[1fr_0.5fr_0.5fr_0.7fr] gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-100 text-[9px] sm:text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    <span>Item</span>
                    <span class="text-center">Qty</span>
                    <span class="text-center">Rate</span>
                    <span class="text-right">Amount</span>
                  </div>
                  <div class="divide-y divide-gray-100/80 max-h-52 overflow-y-auto overscroll-contain">
                    <div
                      v-for="item in detailData.items"
                      :key="item.name"
                      class="grid grid-cols-[1fr_0.5fr_0.5fr_0.7fr] gap-2 px-4 py-2.5 items-center"
                    >
                      <div class="min-w-0">
                        <p class="text-xs font-semibold text-gray-800 truncate">{{ item.item_name }}</p>
                        <p class="text-[9px] text-gray-400 truncate">{{ item.item_code }}</p>
                        <p v-if="item.against_sales_order" class="text-[9px] text-blue-500 font-semibold truncate">
                          SO: {{ item.against_sales_order }}
                        </p>
                      </div>
                      <span class="text-xs text-gray-600 text-center font-medium">{{ item.qty }} {{ item.uom }}</span>
                      <span class="text-xs text-gray-600 text-center">{{ formatCurrency(item.rate, detailData.currency) }}</span>
                      <span class="text-xs font-black text-gray-900 text-right">{{ formatCurrency(item.amount, detailData.currency) }}</span>
                    </div>
                  </div>
                  <div class="border-t border-gray-200 px-4 py-3 flex justify-between items-center">
                    <div v-if="detailData.total_taxes_and_charges" class="text-xs text-gray-500">
                      Tax: {{ formatCurrency(detailData.total_taxes_and_charges, detailData.currency) }}
                    </div>
                    <div class="text-right ml-auto">
                      <p class="text-[9px] text-gray-400 font-bold uppercase">Grand Total</p>
                      <p class="text-sm font-black text-gray-900">{{ formatCurrency(detailData.grand_total, detailData.currency) }}</p>
                    </div>
                  </div>
                </div>

                <!-- ── Action buttons ── -->
                <div class="flex flex-wrap gap-2 justify-end pt-1">

                  <!-- 🖨️ PRINT — blob via Vite proxy, auto-detects default print format -->
                  <button
                    @click.stop="openPrint(row.name)"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gray-900 hover:bg-gray-700 text-white text-xs font-bold transition-colors shadow-sm"
                  >
                    <Printer class="w-3.5 h-3.5" />
                    Print / PDF
                  </button>

                  <!-- Submit — Draft only -->
                  <button
                    v-if="detailData.docstatus === 0"
                    @click.stop="handleSubmit(row.name)"
                    :disabled="processingId === row.name"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-bold transition-colors"
                  >
                    <RefreshCcw v-if="processingId === row.name && processingAction === 'submit'" class="w-3.5 h-3.5 animate-spin" />
                    <Send v-else class="w-3.5 h-3.5" />
                    Submit
                  </button>

                  <!-- Delete — Draft only -->
                  <button
                    v-if="detailData.docstatus === 0"
                    @click.stop="handleDelete(row.name)"
                    :disabled="processingId === row.name"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-50 hover:bg-red-100 disabled:opacity-60 text-red-600 text-xs font-bold border border-red-200 transition-colors"
                  >
                    <RefreshCcw v-if="processingId === row.name && processingAction === 'delete'" class="w-3.5 h-3.5 animate-spin" />
                    <Trash2 v-else class="w-3.5 h-3.5" />
                    Delete
                  </button>

                  <!-- Cancel — Submitted only -->
                  <button
                    v-if="detailData.docstatus === 1"
                    @click.stop="handleCancel(row.name)"
                    :disabled="processingId === row.name"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-orange-50 hover:bg-orange-100 disabled:opacity-60 text-orange-600 text-xs font-bold border border-orange-200 transition-colors"
                  >
                    <RefreshCcw v-if="processingId === row.name && processingAction === 'cancel'" class="w-3.5 h-3.5 animate-spin" />
                    <Ban v-else class="w-3.5 h-3.5" />
                    Cancel
                  </button>

                  <!-- Delete — Cancelled only -->
                  <button
                    v-if="detailData.docstatus === 2"
                    @click.stop="handleDelete(row.name)"
                    :disabled="processingId === row.name"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-50 hover:bg-red-100 disabled:opacity-60 text-red-600 text-xs font-bold border border-red-200 transition-colors"
                  >
                    <RefreshCcw v-if="processingId === row.name && processingAction === 'delete'" class="w-3.5 h-3.5 animate-spin" />
                    <Trash2 v-else class="w-3.5 h-3.5" />
                    Delete
                  </button>

                </div>
              </div>

              <!-- Fallback skeleton if detailData mismatched -->
              <div v-else class="space-y-2">
                <div v-for="i in 3" :key="i" class="h-8 bg-gray-200/60 rounded-lg animate-pulse" />
              </div>

            </div>
          </Transition>
        </div>
      </div>

      <!-- Bottom refresh indicator -->
      <div v-if="isLoading && hasData" class="flex justify-center py-4">
        <RefreshCcw class="w-5 h-5 text-gray-400 animate-spin" />
      </div>
    </div>
  </div>
</template>
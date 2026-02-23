<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { createListResource, createResource } from 'frappe-ui'
import {
  Receipt, RefreshCcw, XCircle, ChevronDown, ChevronRight,
  Calendar, CheckCircle2, Clock, Ban, AlertCircle,
  CreditCard, Search, TrendingUp, Send,
  Trash2, AlertTriangle, Printer, X, Download, Mail,
  CheckCheck, IndianRupee, Smartphone, FileText, Banknote,
} from 'lucide-vue-next'

import PaymentRequestModal from '@/components/PaymentRequestModal.vue'

const props = defineProps<{
  seller?: string
  customer?: string
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
const searchQuery      = ref('')
const fromDate         = ref('')
const toDate           = ref('')
const statusFilter     = ref<string>('all')
const expandedRow      = ref<string | null>(null)
const detailData       = ref<any>(null)
const processingId     = ref<string>('')
const processingAction = ref<string>('')

// ── Payment Request Modal ─────────────────────────────────────────────────────
const paymentModalShow    = ref(false)
const paymentModalInvoice = ref('')
function openPaymentModal(invoiceName: string) {
  paymentModalInvoice.value = invoiceName
  paymentModalShow.value    = true
}

// ── Payment Received Modal ────────────────────────────────────────────────────
type PayMode = 'UPI' | 'Cheque' | 'Cash'
const payRecvModal = ref<{
  show: boolean
  invoiceName: string
  outstandingAmount: number
  currency: string
  loading: boolean
  fetchingFresh: boolean   // ✅ NEW — fresh outstanding fetch ka loading state
  paymentMode: PayMode
  amount: number
  paymentDate: string
  upiTransactionId: string
  chequeNo: string
  chequeDate: string
  bankName: string
  createdEntry: string
  error: string
}>({
  show: false, invoiceName: '', outstandingAmount: 0, currency: 'INR',
  loading: false, fetchingFresh: false, paymentMode: 'UPI', amount: 0, paymentDate: '',
  upiTransactionId: '', chequeNo: '', chequeDate: '', bankName: '',
  createdEntry: '', error: '',
})

function getCsrfToken(): string {
  try { const m = document.cookie.match(/csrftoken=([^;]+)/); return m ? m[1] : '' }
  catch { return '' }
}

// ✅ FIX: Modal kholne se pehle FRESH outstanding_amount fetch karo DB se
// Yahi root cause tha — list mein stale data tha, modal purane amount se khul raha tha
async function openPayRecvModal(inv: any) {
  const today = new Date().toISOString().split('T')[0]

  // Pehle modal kholo initial data ke saath (stale bhi chalega)
  payRecvModal.value = {
    show: true,
    invoiceName: inv.name,
    outstandingAmount: inv.outstanding_amount,
    currency: inv.currency || 'INR',
    loading: false,
    fetchingFresh: true,  // spinner dikhao
    paymentMode: 'UPI',
    amount: inv.outstanding_amount,
    paymentDate: today,
    upiTransactionId: '',
    chequeNo: '', chequeDate: today, bankName: '',
    createdEntry: '', error: '',
  }

  // ✅ Phir FRESH data fetch karo backend se
  try {
    const r = await fetch('/api/method/my_frappe_app.payment_utils.get_invoice_outstanding', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': getCsrfToken(),
      },
      body: JSON.stringify({ invoice_name: inv.name }),
    })

    if (r.ok) {
      const j = await r.json()
      const freshData = j?.message

      if (freshData) {
        if (freshData.is_paid || freshData.outstanding_amount <= 0) {
          // Invoice already paid hai — modal band karo, error dikhao
          payRecvModal.value.show = false
          showToast(`Invoice ${inv.name} already fully paid. Please refresh.`, 'error')
          invoices.reload()
          return
        }

        // Fresh data se modal update karo
        payRecvModal.value.outstandingAmount = freshData.outstanding_amount
        payRecvModal.value.amount = freshData.outstanding_amount
        payRecvModal.value.currency = freshData.currency || 'INR'
      }
    }
  } catch (e) {
    // Fetch fail hua — stale data se kaam chalao (backend pe bhi validation hai)
    console.warn('Fresh outstanding fetch failed, using cached data:', e)
  } finally {
    payRecvModal.value.fetchingFresh = false
  }
}

function closePayRecvModal() {
  payRecvModal.value.show = false
}

const payModes: { key: PayMode; label: string; icon: any; color: string }[] = [
  { key: 'UPI',    label: 'UPI',    icon: Smartphone, color: 'violet' },
  { key: 'Cheque', label: 'Cheque', icon: FileText,   color: 'blue'   },
  { key: 'Cash',   label: 'Cash',   icon: Banknote,   color: 'green'  },
]

// ─── PRINT MODAL ──────────────────────────────────────────────────────────────
const printModal = ref<{
  show: boolean; loading: boolean; blobUrl: string
  docName: string; printFormat: string; error: string
}>({ show: false, loading: false, blobUrl: '', docName: '', printFormat: '', error: '' })

const confirmDialog = ref<{
  show: boolean; title: string; message: string
  confirmLabel: string; confirmClass: string; onConfirm: () => void
}>({ show: false, title: '', message: '', confirmLabel: '', confirmClass: '', onConfirm: () => {} })

const statusOptions = [
  { key: 'all',       label: 'All'       },
  { key: 'Draft',     label: 'Draft'     },
  { key: 'Unpaid',    label: 'Unpaid'    },
  { key: 'Paid',      label: 'Paid'      },
  { key: 'Overdue',   label: 'Overdue'   },
  { key: 'Cancelled', label: 'Cancelled' },
]

// ─── RESOURCES ────────────────────────────────────────────────────────────────
const invoices = createListResource({
  doctype: 'Sales Invoice',
  fields: [
    'name', 'customer', 'customer_name', 'status', 'posting_date',
    'grand_total', 'outstanding_amount', 'currency', 'docstatus',
    'due_date', 'paid_amount', 'discount_amount', 'taxes_and_charges',
    'is_return', 'return_against', 'debit_to', 'company',
  ],
  filters: [],
  orderBy: 'posting_date desc',
  pageLength: 200,
  auto: false,
})

const invDetail = createResource({
  url: 'frappe.client.get',
  makeParams: (v: { name: string }) => ({ doctype: 'Sales Invoice', name: v.name }),
  onSuccess(data: any) { detailData.value = data },
})

const submitInv = createResource({
  url: 'frappe.client.submit',
  onSuccess() {
    processingId.value = ''; processingAction.value = ''
    showToast('Invoice submitted successfully!', 'success')
    invoices.reload()
    if (expandedRow.value) invDetail.fetch({ name: expandedRow.value })
  },
  onError(err: any) {
    processingId.value = ''; processingAction.value = ''
    showToast(parseError(err), 'error')
  },
})

const cancelInv = createResource({
  url: 'frappe.client.cancel',
  onSuccess() {
    processingId.value = ''; processingAction.value = ''
    showToast('Invoice cancelled.', 'info')
    invoices.reload()
    if (expandedRow.value) invDetail.fetch({ name: expandedRow.value })
  },
  onError(err: any) {
    processingId.value = ''; processingAction.value = ''
    showToast(parseError(err), 'error')
  },
})

const deleteInv = createResource({
  url: 'frappe.client.delete',
  onSuccess() {
    processingId.value = ''; processingAction.value = ''
    expandedRow.value = null; detailData.value = null
    showToast('Invoice deleted.', 'info')
    invoices.reload()
  },
  onError(err: any) {
    processingId.value = ''; processingAction.value = ''
    showToast(parseError(err), 'error')
  },
})

// ─── PAYMENT ENTRY RESOURCE ───────────────────────────────────────────────────
const createPaymentEntry = createResource({
  url: 'my_frappe_app.payment_utils.create_payment_entry',
  onSuccess(data: any) {
    payRecvModal.value.loading  = false
    payRecvModal.value.createdEntry = data.name
    showToast(`Payment recorded! Entry: ${data.name}`, 'success')
    invoices.reload()
    if (expandedRow.value) invDetail.fetch({ name: expandedRow.value })
  },
  onError(err: any) {
    payRecvModal.value.loading = false
    const errMsg = parseError(err)
    payRecvModal.value.error = errMsg

    // ✅ FIX: Agar "already paid" error aaye, to list reload karo aur modal band karo
    if (errMsg.toLowerCase().includes('already') && errMsg.toLowerCase().includes('paid')) {
      showToast('Invoice already paid. Refreshing...', 'info')
      setTimeout(() => {
        closePayRecvModal()
        invoices.reload()
      }, 1500)
    } else {
      showToast('Payment entry creation failed.', 'error')
    }
  },
})

// ─── WATCHERS ─────────────────────────────────────────────────────────────────
watch(
  () => [props.customer, props.seller],
  ([customer]) => {
    const filters: any[] = []
    if (customer) filters.push(['customer', '=', customer])
    invoices.update({ filters })
    invoices.reload()
  },
  { immediate: true },
)

// ─── COMPUTED ─────────────────────────────────────────────────────────────────
const filtered = computed<any[]>(() => {
  let rows = (invoices.data || []) as any[]
  if (statusFilter.value !== 'all') {
    if (statusFilter.value === 'Draft')          rows = rows.filter(r => r.docstatus === 0)
    else if (statusFilter.value === 'Cancelled') rows = rows.filter(r => r.docstatus === 2)
    else                                         rows = rows.filter(r => r.status === statusFilter.value)
  }
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
const isLoading     = computed(() => invoices.loading)
const hasData       = computed(() => (invoices.data || []).length > 0)

const summary = computed(() => {
  const rows = (invoices.data || []) as any[]
  const sub  = rows.filter(r => r.docstatus === 1)
  return {
    total:       sub.reduce((s: number, r: any) => s + (r.grand_total        || 0), 0),
    outstanding: sub.reduce((s: number, r: any) => s + (r.outstanding_amount || 0), 0),
    paid:        sub.reduce((s: number, r: any) => s + (r.paid_amount        || 0), 0),
    overdue:     sub.filter((r: any) => r.status === 'Overdue').length,
  }
})

function clearFilters() {
  fromDate.value = ''; toDate.value = ''; statusFilter.value = 'all'; searchQuery.value = ''
}

// ─── HELPERS ──────────────────────────────────────────────────────────────────
type BadgeTheme = 'gray' | 'blue' | 'green' | 'red' | 'orange' | 'purple'

function getStatusInfo(row: any): { label: string; theme: BadgeTheme; icon: any } {
  if (row.docstatus === 2)          return { label: 'Cancelled', theme: 'gray',   icon: Ban          }
  if (row.docstatus === 0)          return { label: 'Draft',     theme: 'orange', icon: Clock        }
  if (row.status === 'Paid')        return { label: 'Paid',      theme: 'green',  icon: CheckCircle2 }
  if (row.status === 'Overdue')     return { label: 'Overdue',   theme: 'red',    icon: AlertCircle  }
  if (row.status === 'Unpaid')      return { label: 'Unpaid',    theme: 'blue',   icon: CreditCard   }
  if (row.status === 'Partly Paid') return { label: 'Part Paid', theme: 'purple', icon: TrendingUp   }
  return { label: row.status || 'Unknown', theme: 'gray', icon: Receipt }
}

const themeClasses: Record<BadgeTheme, string> = {
  gray:   'bg-gray-100 text-gray-600',
  blue:   'bg-blue-50 text-blue-700',
  green:  'bg-green-50 text-green-700',
  red:    'bg-red-50 text-red-700',
  orange: 'bg-orange-50 text-orange-700',
  purple: 'bg-violet-50 text-violet-700',
}

function outstandingPercent(row: any) {
  if (!row.grand_total) return 0
  return Math.round((row.outstanding_amount / row.grand_total) * 100)
}

function toggleExpand(name: string) {
  if (expandedRow.value === name) { expandedRow.value = null; detailData.value = null }
  else { expandedRow.value = name; detailData.value = null; invDetail.fetch({ name }) }
}

function parseError(err: any): string {
  if (!err) return 'Unknown error'
  let msg = err?.message || err?.exc || ''
  msg = msg.replace(/<[^>]*>/g, '').trim()
  if (msg.includes('Traceback') || msg.includes('\n')) {
    const lines = msg.split('\n').map((l: string) => l.trim()).filter((l: string) =>
      l.length > 0 && !l.startsWith('Traceback') && !l.startsWith('File "') &&
      !l.startsWith('During handling') && !/^\s{2,}/.test(l),
    )
    msg = lines[lines.length - 1] || msg.split('\n')[0]
  }
  return msg || 'Backend error — check Frappe Error Log'
}

// ─── PAYMENT ENTRY CREATION ───────────────────────────────────────────────────
async function fetchAccountForModeOfPayment(modeOfPayment: string, company: string): Promise<string> {
  try {
    const r = await fetch('/api/method/my_frappe_app.payment_utils.get_payment_account', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': getCsrfToken() },
      body: JSON.stringify({ mode_of_payment: modeOfPayment, company }),
    })
    if (r.ok) { const j = await r.json(); return j?.message || '' }
  } catch { /* fall through */ }
  return ''
}

async function fetchDefaultReceivableAccount(company: string, _customer: string): Promise<string> {
  try {
    const r = await fetch('/api/method/my_frappe_app.payment_utils.get_receivable_account', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': getCsrfToken() },
      body: JSON.stringify({ company }),
    })
    if (r.ok) { const j = await r.json(); return j?.message || '' }
  } catch { /* fall through */ }
  return ''
}

async function fetchCompanyDefaultAccount(company: string, fieldname: string): Promise<string> {
  try {
    const r = await fetch('/api/method/my_frappe_app.payment_utils.get_company_account', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': getCsrfToken() },
      body: JSON.stringify({ company, fieldname }),
    })
    if (r.ok) { const j = await r.json(); return j?.message || '' }
  } catch { /* fall through */ }
  return ''
}

async function submitPayRecvForm() {
  const m = payRecvModal.value
  m.error = ''

  // ✅ FIX: Agar fresh data abhi bhi fetch ho raha hai, to wait karo
  if (m.fetchingFresh) {
    m.error = 'Please wait, loading latest invoice data...'
    return
  }

  // Validation
  if (!m.amount || m.amount <= 0)    { m.error = 'Amount must be greater than 0'; return }
  if (m.amount > m.outstandingAmount) { m.error = `Amount cannot exceed outstanding ₹${m.outstandingAmount.toFixed(2)}`; return }
  if (!m.paymentDate)                 { m.error = 'Payment date is required'; return }
  if (m.paymentMode === 'UPI' && !m.upiTransactionId.trim()) { m.error = 'UPI Transaction ID is required'; return }
  if (m.paymentMode === 'Cheque') {
    if (!m.chequeNo.trim()) { m.error = 'Cheque number is required'; return }
    if (!m.chequeDate)       { m.error = 'Cheque date is required'; return }
  }

  m.loading = true

  const modeMap: Record<PayMode, string> = { UPI: 'UPI', Cheque: 'Cheque', Cash: 'Cash' }

  const invRow = (invoices.data || []).find((r: any) => r.name === m.invoiceName) as any
  const company  = invRow?.company  || ''
  const customer = invRow?.customer || ''
  const debitTo  = invRow?.debit_to || ''
  const mopName  = modeMap[m.paymentMode]

  let paidToAccount = await fetchAccountForModeOfPayment(mopName, company)
  if (!paidToAccount) {
    const fieldname = m.paymentMode === 'Cash' ? 'default_cash_account' : 'default_bank_account'
    paidToAccount = await fetchCompanyDefaultAccount(company, fieldname)
  }

  const paidFromAccount = debitTo || await fetchDefaultReceivableAccount(company, customer)

  if (!paidFromAccount) {
    m.loading = false
    m.error = 'Could not determine receivable account. Please check company settings.'
    return
  }
  if (!paidToAccount) {
    m.loading = false
    m.error = `Could not determine ${m.paymentMode} account. Please set default account for "${mopName}" mode of payment.`
    return
  }

  const payDoc: any = {
    doctype:         'Payment Entry',
    payment_type:    'Receive',
    mode_of_payment: mopName,
    party_type:      'Customer',
    party:           customer,
    party_name:      invRow?.customer_name || '',
    posting_date:    m.paymentDate,
    paid_amount:     m.amount,
    received_amount: m.amount,
    company:         company,
    paid_from:       paidFromAccount,
    paid_to:         paidToAccount,
    references: [{
      reference_doctype: 'Sales Invoice',
      reference_name:    m.invoiceName,
      allocated_amount:  m.amount,
    }],
  }

  if (m.paymentMode === 'UPI') {
    payDoc.reference_no   = m.upiTransactionId
    payDoc.reference_date = m.paymentDate
    payDoc.remarks        = `UPI Payment for ${m.invoiceName}. Transaction ID: ${m.upiTransactionId}`
  } else if (m.paymentMode === 'Cheque') {
    payDoc.reference_no   = m.chequeNo
    payDoc.reference_date = m.chequeDate
    payDoc.remarks        = `Cheque Payment for ${m.invoiceName}. Cheque No: ${m.chequeNo}${m.bankName ? ` | Bank: ${m.bankName}` : ''}`
  } else {
    payDoc.reference_no   = `CASH-${m.paymentDate}`
    payDoc.reference_date = m.paymentDate
    payDoc.remarks        = `Cash Payment for ${m.invoiceName}`
  }

  createPaymentEntry.fetch({ doc: JSON.stringify(payDoc) })
}

// ─── PRINT ────────────────────────────────────────────────────────────────────
async function getDefaultPrintFormat(): Promise<string | null> {
  try {
    const r = await fetch('/api/method/my_frappe_app.payment_utils.get_print_format', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': getCsrfToken() },
      body: JSON.stringify({}),
    })
    if (!r.ok) return null
    const j = await r.json()
    return j?.message || null
  } catch { return null }
}

async function openPrint(docName: string) {
  printModal.value = { show: true, loading: true, blobUrl: '', docName, printFormat: 'Detecting…', error: '' }
  try {
    const fmt = await getDefaultPrintFormat()
    printModal.value.printFormat = fmt ?? 'Server Default'
    const blob = await fetchPdfBlob(docName, fmt)
    printModal.value = { show: true, loading: false, blobUrl: URL.createObjectURL(blob), docName, printFormat: fmt ?? 'Server Default', error: '' }
  } catch (e: any) {
    printModal.value = { show: true, loading: false, blobUrl: '', docName, printFormat: '', error: e?.message || 'Failed to load PDF' }
  }
}

async function fetchPdfBlob(docName: string, fmt: string | null): Promise<Blob> {
  const url = (f?: string) => {
    const p: Record<string, string> = { doctype: 'Sales Invoice', name: docName, no_letterhead: '0', letterhead: 'No Letterhead' }
    if (f) p.format = f
    return '/api/method/frappe.utils.print_format.download_pdf?' + new URLSearchParams(p)
  }
  if (fmt) { const r = await fetch(url(fmt), { credentials: 'include' }); if (r.ok) { const b = await r.blob(); if (b.size > 500) return b } }
  const r2 = await fetch(url(), { credentials: 'include' })
  if (r2.ok) { const b = await r2.blob(); if (b.size > 500) return b }
  throw new Error(`PDF generation failed — HTTP ${r2.status}`)
}

function closePrint() {
  if (printModal.value.blobUrl) URL.revokeObjectURL(printModal.value.blobUrl)
  printModal.value = { show: false, loading: false, blobUrl: '', docName: '', printFormat: '', error: '' }
}

function downloadPdf() {
  if (!printModal.value.blobUrl) return
  const a = document.createElement('a')
  a.href = printModal.value.blobUrl; a.download = `${printModal.value.docName}.pdf`; a.click()
}

// ─── INVOICE ACTIONS ──────────────────────────────────────────────────────────
function askConfirm(opts: { title: string; message: string; confirmLabel: string; confirmClass: string; onConfirm: () => void }) {
  confirmDialog.value = { show: true, ...opts }
}

function handleSubmit(name: string) {
  if (!detailData.value) return
  askConfirm({
    title: 'Submit Sales Invoice', message: `Submit ${name}? Accounting entries will be posted.`,
    confirmLabel: 'Submit', confirmClass: 'bg-blue-600 hover:bg-blue-700 text-white',
    onConfirm: () => {
      confirmDialog.value.show = false
      processingId.value = name; processingAction.value = 'submit'
      submitInv.fetch({ doc: detailData.value })
    },
  })
}

function handleCancel(name: string) {
  askConfirm({
    title: 'Cancel Sales Invoice', message: `Cancel ${name}? All accounting entries will be reversed.`,
    confirmLabel: 'Cancel Invoice', confirmClass: 'bg-red-600 hover:bg-red-700 text-white',
    onConfirm: () => {
      confirmDialog.value.show = false
      processingId.value = name; processingAction.value = 'cancel'
      cancelInv.fetch({ doctype: 'Sales Invoice', name })
    },
  })
}

function handleDelete(name: string) {
  askConfirm({
    title: 'Delete Sales Invoice', message: `Permanently delete ${name}? This cannot be undone.`,
    confirmLabel: 'Delete', confirmClass: 'bg-red-700 hover:bg-red-800 text-white',
    onConfirm: () => {
      confirmDialog.value.show = false
      processingId.value = name; processingAction.value = 'delete'
      deleteInv.fetch({ doctype: 'Sales Invoice', name })
    },
  })
}
</script>

<template>
  <div class="w-full min-w-0">

    <!-- ══ TOAST NOTIFICATIONS ══════════════════════════════════════════════ -->
    <Teleport to="body">
      <div class="fixed top-4 right-4 z-[2000] flex flex-col gap-2 pointer-events-none max-w-xs w-full">
        <TransitionGroup
          enter-active-class="transition-all duration-300 ease-out"
          enter-from-class="opacity-0 translate-x-8 scale-95"
          enter-to-class="opacity-100 translate-x-0 scale-100"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 translate-x-0"
          leave-to-class="opacity-0 translate-x-8"
        >
          <div
            v-for="toast in toasts"
            :key="toast.id"
            :class="[
              'flex items-center gap-3 px-4 py-3 rounded-2xl shadow-xl pointer-events-auto',
              'border backdrop-blur-sm',
              toast.type === 'success' ? 'bg-green-50 border-green-200 text-green-800' :
              toast.type === 'error'   ? 'bg-red-50 border-red-200 text-red-800' :
                                         'bg-blue-50 border-blue-200 text-blue-800',
            ]"
          >
            <div :class="['p-1 rounded-lg flex-shrink-0',
              toast.type === 'success' ? 'bg-green-100' :
              toast.type === 'error'   ? 'bg-red-100' : 'bg-blue-100']">
              <CheckCheck v-if="toast.type === 'success'" class="w-3.5 h-3.5" />
              <AlertTriangle v-else-if="toast.type === 'error'" class="w-3.5 h-3.5" />
              <AlertCircle v-else class="w-3.5 h-3.5" />
            </div>
            <p class="text-xs font-semibold leading-snug flex-1">{{ toast.message }}</p>
          </div>
        </TransitionGroup>
      </div>
    </Teleport>

    <!-- ══ PAYMENT REQUEST MODAL ════════════════════════════════════════════ -->
    <PaymentRequestModal
      :invoice-name="paymentModalInvoice"
      :show="paymentModalShow"
      @close="paymentModalShow = false"
      @sent="showToast('Payment request email sent!', 'success')"
    />

    <!-- ══ PAYMENT RECEIVED MODAL ═══════════════════════════════════════════ -->
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
          v-if="payRecvModal.show"
          class="fixed inset-0 z-[999] flex items-end sm:items-center justify-center
                 sm:p-4 bg-black/50 backdrop-blur-sm"
          @click.self="closePayRecvModal"
        >
          <div class="bg-white w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl
                      shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">

            <!-- Header -->
            <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100 flex-shrink-0">
              <div class="flex items-center gap-3 min-w-0">
                <div class="p-2 bg-violet-50 rounded-xl flex-shrink-0">
                  <IndianRupee class="w-4 h-4 text-violet-600" />
                </div>
                <div class="min-w-0">
                  <h3 class="text-sm font-black text-gray-900">Record Payment</h3>
                  <p class="text-[10px] text-gray-400 font-medium truncate mt-0.5">
                    {{ payRecvModal.invoiceName }}
                    <!-- ✅ FIX: Fetching fresh data ke time spinner dikhao -->
                    <span v-if="payRecvModal.fetchingFresh" class="ml-1.5 text-gray-400 font-semibold animate-pulse">
                      Loading latest amount...
                    </span>
                    <span v-else class="ml-1.5 text-red-500 font-black">
                      ₹{{ payRecvModal.outstandingAmount?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) }} due
                    </span>
                  </p>
                </div>
              </div>
              <button @click="closePayRecvModal"
                class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors flex-shrink-0 ml-2">
                <X class="w-4 h-4" />
              </button>
            </div>

            <!-- ✅ FIX: Fresh data fetch ho raha hai to skeleton dikhao -->
            <div v-if="payRecvModal.fetchingFresh" class="flex-1 flex flex-col items-center justify-center gap-3 p-8">
              <RefreshCcw class="w-8 h-8 text-violet-400 animate-spin" />
              <p class="text-xs text-gray-500 font-semibold">Verifying invoice status...</p>
            </div>

            <!-- SUCCESS STATE -->
            <div v-else-if="payRecvModal.createdEntry" class="flex-1 flex flex-col items-center justify-center gap-4 p-8 text-center">
              <div class="p-4 bg-green-50 rounded-2xl">
                <CheckCheck class="w-10 h-10 text-green-600" />
              </div>
              <div>
                <p class="text-base font-black text-gray-900 mb-1">Payment Recorded!</p>
                <p class="text-xs text-gray-500">
                  Entry created and submitted:
                  <span class="font-black text-gray-800">{{ payRecvModal.createdEntry }}</span>
                </p>
              </div>
              <button @click="closePayRecvModal"
                class="mt-2 px-6 py-2.5 bg-gray-900 hover:bg-gray-700 text-white text-xs font-black rounded-xl transition-colors">
                Done
              </button>
            </div>

            <!-- FORM STATE -->
            <template v-else>
              <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">

                <!-- Payment Mode selector -->
                <div>
                  <p class="text-[10px] font-black text-gray-500 uppercase tracking-wide mb-2">Payment Mode</p>
                  <div class="grid grid-cols-3 gap-2">
                    <button
                      v-for="mode in payModes"
                      :key="mode.key"
                      @click="payRecvModal.paymentMode = mode.key"
                      :class="[
                        'flex flex-col items-center gap-1.5 py-3 px-2 rounded-xl border-2 transition-all',
                        payRecvModal.paymentMode === mode.key
                          ? mode.color === 'violet' ? 'border-violet-500 bg-violet-50 text-violet-700'
                          : mode.color === 'blue'   ? 'border-blue-500 bg-blue-50 text-blue-700'
                          :                           'border-green-500 bg-green-50 text-green-700'
                          : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300',
                      ]"
                    >
                      <component :is="mode.icon" class="w-5 h-5" />
                      <span class="text-[11px] font-black">{{ mode.label }}</span>
                    </button>
                  </div>
                </div>

                <!-- Amount + Date -->
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-[10px] font-black text-gray-500 uppercase tracking-wide mb-1.5">
                      Amount (₹)
                    </label>
                    <input
                      v-model.number="payRecvModal.amount"
                      type="number" step="0.01" :max="payRecvModal.outstandingAmount"
                      class="w-full px-3 py-2.5 text-sm font-black text-gray-900 bg-gray-50
                             border border-gray-200 rounded-xl outline-none
                             focus:border-gray-400 focus:bg-white transition-colors"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label class="block text-[10px] font-black text-gray-500 uppercase tracking-wide mb-1.5">
                      Payment Date
                    </label>
                    <input
                      v-model="payRecvModal.paymentDate"
                      type="date"
                      class="w-full px-3 py-2.5 text-sm font-semibold text-gray-700 bg-gray-50
                             border border-gray-200 rounded-xl outline-none
                             focus:border-gray-400 focus:bg-white transition-colors cursor-pointer"
                    />
                  </div>
                </div>

                <!-- UPI fields -->
                <div v-if="payRecvModal.paymentMode === 'UPI'" class="space-y-3">
                  <div class="flex items-center gap-2 text-violet-600 mb-1">
                    <Smartphone class="w-4 h-4" />
                    <span class="text-xs font-black">UPI Transaction Details</span>
                  </div>
                  <div>
                    <label class="block text-[10px] font-black text-gray-500 uppercase tracking-wide mb-1.5">
                      UPI Transaction ID *
                    </label>
                    <input
                      v-model="payRecvModal.upiTransactionId"
                      type="text"
                      class="w-full px-3 py-2.5 text-sm font-mono text-gray-900 bg-gray-50
                             border border-gray-200 rounded-xl outline-none
                             focus:border-violet-400 focus:bg-white transition-colors"
                      placeholder="e.g. 123456789012"
                    />
                    <p class="text-[10px] text-gray-400 mt-1">
                      Transaction ID from GPay / PhonePe / Paytm confirmation screen
                    </p>
                  </div>
                </div>

                <!-- Cheque fields -->
                <div v-if="payRecvModal.paymentMode === 'Cheque'" class="space-y-3">
                  <div class="flex items-center gap-2 text-blue-600 mb-1">
                    <FileText class="w-4 h-4" />
                    <span class="text-xs font-black">Cheque Details</span>
                  </div>
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="block text-[10px] font-black text-gray-500 uppercase tracking-wide mb-1.5">
                        Cheque No *
                      </label>
                      <input
                        v-model="payRecvModal.chequeNo"
                        type="text"
                        class="w-full px-3 py-2.5 text-sm font-mono text-gray-900 bg-gray-50
                               border border-gray-200 rounded-xl outline-none
                               focus:border-blue-400 focus:bg-white transition-colors"
                        placeholder="123456"
                      />
                    </div>
                    <div>
                      <label class="block text-[10px] font-black text-gray-500 uppercase tracking-wide mb-1.5">
                        Cheque Date *
                      </label>
                      <input
                        v-model="payRecvModal.chequeDate"
                        type="date"
                        class="w-full px-3 py-2.5 text-sm font-semibold text-gray-700 bg-gray-50
                               border border-gray-200 rounded-xl outline-none
                               focus:border-blue-400 focus:bg-white transition-colors cursor-pointer"
                      />
                    </div>
                  </div>
                  <div>
                    <label class="block text-[10px] font-black text-gray-500 uppercase tracking-wide mb-1.5">
                      Bank Name (optional)
                    </label>
                    <input
                      v-model="payRecvModal.bankName"
                      type="text"
                      class="w-full px-3 py-2.5 text-sm text-gray-900 bg-gray-50
                             border border-gray-200 rounded-xl outline-none
                             focus:border-blue-400 focus:bg-white transition-colors"
                      placeholder="e.g. HDFC Bank"
                    />
                  </div>
                </div>

                <!-- Cash info -->
                <div v-if="payRecvModal.paymentMode === 'Cash'"
                  class="bg-green-50 border border-green-100 rounded-xl px-4 py-3">
                  <div class="flex items-center gap-2 text-green-700">
                    <Banknote class="w-4 h-4 flex-shrink-0" />
                    <p class="text-xs font-semibold leading-relaxed">
                      Cash payment entry will be created with today's date.
                      Confirm the amount above and click Record Payment.
                    </p>
                  </div>
                </div>

                <!-- Error -->
                <div v-if="payRecvModal.error"
                  class="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-3 py-3">
                  <AlertTriangle class="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <p class="text-xs text-red-700 font-medium leading-relaxed">{{ payRecvModal.error }}</p>
                </div>

              </div>

              <!-- Footer -->
              <div class="flex items-center gap-2 px-5 py-4 border-t border-gray-100 bg-gray-50/80 flex-shrink-0">
                <button
                  @click="closePayRecvModal"
                  :disabled="payRecvModal.loading"
                  class="px-4 py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 disabled:opacity-50
                         text-xs font-bold text-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <div class="flex-1" />
                <button
                  @click="submitPayRecvForm"
                  :disabled="payRecvModal.loading || payRecvModal.fetchingFresh"
                  class="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-violet-600
                         hover:bg-violet-700 disabled:opacity-50 text-white text-xs font-black
                         transition-colors shadow-sm"
                >
                  <RefreshCcw v-if="payRecvModal.loading || payRecvModal.fetchingFresh" class="w-3.5 h-3.5 animate-spin" />
                  <CheckCheck v-else class="w-3.5 h-3.5" />
                  {{ payRecvModal.loading ? 'Processing…' : payRecvModal.fetchingFresh ? 'Verifying...' : 'Record Payment' }}
                </button>
              </div>
            </template>

          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ══ PRINT MODAL ══ -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-all duration-250 ease-out" enter-from-class="opacity-0" enter-to-class="opacity-100"
        leave-active-class="transition-all duration-200" leave-from-class="opacity-100" leave-to-class="opacity-0"
      >
        <div v-if="printModal.show" class="fixed inset-0 z-[1000] flex flex-col bg-gray-950">
          <div class="flex items-center gap-3 bg-gray-900 px-4 py-3 border-b border-white/10 flex-shrink-0">
            <div class="p-1.5 bg-white/10 rounded-lg flex-shrink-0"><Printer class="w-4 h-4 text-white" /></div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-black text-white truncate">{{ printModal.docName }}</p>
              <p class="text-[10px] font-medium" :class="printModal.loading ? 'text-gray-500 animate-pulse' : 'text-gray-400'">
                Format: <span class="text-emerald-400">{{ printModal.printFormat || '…' }}</span>
              </p>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <button v-if="printModal.blobUrl" @click="downloadPdf"
                class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold transition-colors">
                <Download class="w-3.5 h-3.5" /><span class="hidden sm:inline">Download</span>
              </button>
              <button @click="closePrint"
                class="flex items-center justify-center w-9 h-9 rounded-xl bg-white/10 hover:bg-red-500 text-white transition-colors">
                <X class="w-4 h-4" />
              </button>
            </div>
          </div>
          <div v-if="printModal.loading" class="flex-1 flex items-center justify-center">
            <div class="flex flex-col items-center gap-4">
              <div class="relative">
                <div class="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center">
                  <Receipt class="w-7 h-7 text-white/60" />
                </div>
                <div class="absolute inset-0 rounded-2xl border-2 border-emerald-400 border-t-transparent animate-spin" />
              </div>
              <p class="text-sm font-bold text-white">Preparing PDF…</p>
            </div>
          </div>
          <div v-else-if="printModal.error" class="flex-1 flex items-center justify-center p-6">
            <div class="bg-red-950/50 border border-red-800 rounded-2xl p-6 max-w-sm w-full text-center space-y-4">
              <AlertTriangle class="w-8 h-8 text-red-400 mx-auto" />
              <p class="text-sm font-black text-red-300">PDF Load Failed</p>
              <p class="text-xs text-red-500 break-words">{{ printModal.error }}</p>
              <button @click="closePrint" class="w-full py-2 bg-red-700 hover:bg-red-600 text-white text-xs font-bold rounded-xl">Close</button>
            </div>
          </div>
          <iframe v-else-if="printModal.blobUrl" :src="printModal.blobUrl" class="flex-1 w-full border-0" />
        </div>
      </Transition>
    </Teleport>

    <!-- ══ CONFIRM DIALOG ══ -->
    <Teleport to="body">
      <Transition enter-active-class="transition-all duration-200 ease-out" enter-from-class="opacity-0 scale-95"
        enter-to-class="opacity-100 scale-100" leave-active-class="transition-all duration-150"
        leave-from-class="opacity-100" leave-to-class="opacity-0 scale-95">
        <div v-if="confirmDialog.show"
          class="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
          @click.self="confirmDialog.show = false">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 space-y-4">
            <div class="flex items-start gap-3">
              <div class="p-2 bg-orange-50 rounded-xl flex-shrink-0"><AlertTriangle class="w-5 h-5 text-orange-500" /></div>
              <div>
                <h3 class="text-sm font-black text-gray-900">{{ confirmDialog.title }}</h3>
                <p class="text-xs text-gray-500 mt-1 leading-relaxed">{{ confirmDialog.message }}</p>
              </div>
            </div>
            <div class="flex gap-2 justify-end">
              <button @click="confirmDialog.show = false"
                class="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-xs font-bold text-gray-600 transition-colors">Go Back</button>
              <button @click="confirmDialog.onConfirm()"
                :class="['px-4 py-2 rounded-xl text-xs font-bold transition-colors', confirmDialog.confirmClass]">
                {{ confirmDialog.confirmLabel }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ── Summary cards ── -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 px-3 sm:px-5 pt-3 pb-2">
      <div class="bg-gradient-to-br from-gray-900 to-gray-700 rounded-xl p-3 text-white">
        <p class="text-[9px] font-bold uppercase tracking-wider opacity-70 mb-1">Total Billed</p>
        <p class="text-sm sm:text-base font-black leading-tight">{{ formatCurrency(summary.total) }}</p>
      </div>
      <div class="bg-gradient-to-br from-blue-600 to-blue-500 rounded-xl p-3 text-white">
        <p class="text-[9px] font-bold uppercase tracking-wider opacity-70 mb-1">Outstanding</p>
        <p class="text-sm sm:text-base font-black leading-tight">{{ formatCurrency(summary.outstanding) }}</p>
      </div>
      <div class="bg-gradient-to-br from-green-600 to-green-500 rounded-xl p-3 text-white">
        <p class="text-[9px] font-bold uppercase tracking-wider opacity-70 mb-1">Collected</p>
        <p class="text-sm sm:text-base font-black leading-tight">{{ formatCurrency(summary.paid) }}</p>
      </div>
      <div class="bg-gradient-to-br from-red-500 to-red-400 rounded-xl p-3 text-white">
        <p class="text-[9px] font-bold uppercase tracking-wider opacity-70 mb-1">Overdue</p>
        <p class="text-sm sm:text-base font-black leading-tight">
          {{ summary.overdue }} invoice{{ summary.overdue !== 1 ? 's' : '' }}
        </p>
      </div>
    </div>

    <!-- ── Filters ── -->
    <div class="border-b border-gray-100 bg-gray-50/60 space-y-2.5 px-3 sm:px-5 pt-2 pb-3">
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex items-center gap-2 flex-1 min-w-0">
          <div class="p-1.5 sm:p-2 bg-gray-900 rounded-lg sm:rounded-xl text-white shadow flex-shrink-0">
            <Receipt class="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div class="min-w-0">
            <h2 class="text-sm sm:text-base font-black tracking-tight leading-tight">Sales Invoices</h2>
            <p class="text-[10px] text-gray-400 font-medium mt-0.5">
              {{ filtered.length }} record{{ filtered.length !== 1 ? 's' : '' }}
              <span v-if="hasDateFilter || statusFilter !== 'all' || searchQuery" class="text-blue-500"> (filtered)</span>
            </p>
          </div>
        </div>
        <button @click="invoices.reload()"
          :class="['flex items-center gap-1.5 px-2.5 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-600 transition-all', isLoading ? 'opacity-60 pointer-events-none' : '']">
          <RefreshCcw :class="['w-3.5 h-3.5', isLoading ? 'animate-spin' : '']" />
          <span class="hidden sm:inline">Refresh</span>
        </button>
      </div>
      <div class="relative">
        <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
        <input v-model="searchQuery" type="text" placeholder="Search invoice # or customer…"
          class="w-full pl-8 pr-8 py-2 text-xs sm:text-sm bg-white border border-gray-200 rounded-lg outline-none focus:border-gray-400 transition-colors" />
        <button v-if="searchQuery" @click="searchQuery = ''" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-300 hover:text-red-400">
          <XCircle class="w-3.5 h-3.5" />
        </button>
      </div>
      <div class="flex flex-wrap gap-2 items-center">
        <div class="flex gap-1 flex-wrap">
          <button v-for="s in statusOptions" :key="s.key" @click="statusFilter = s.key"
            :class="['px-2.5 py-1 rounded-full text-[10px] sm:text-xs font-bold transition-all whitespace-nowrap',
              statusFilter === s.key ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200']">
            {{ s.label }}
          </button>
        </div>
        <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2 py-1.5 flex-shrink-0">
          <span class="text-[9px] font-bold text-gray-400 uppercase select-none whitespace-nowrap">From</span>
          <input type="date" v-model="fromDate" :max="toDate || undefined"
            class="text-[10px] sm:text-xs font-semibold text-gray-700 bg-transparent outline-none border-none w-[108px] sm:w-[122px] cursor-pointer" />
          <button v-if="fromDate" @click="fromDate = ''" class="text-gray-300 hover:text-red-400"><XCircle class="w-3 h-3" /></button>
        </div>
        <div class="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2 py-1.5 flex-shrink-0">
          <span class="text-[9px] font-bold text-gray-400 uppercase select-none whitespace-nowrap">To</span>
          <input type="date" v-model="toDate" :min="fromDate || undefined"
            class="text-[10px] sm:text-xs font-semibold text-gray-700 bg-transparent outline-none border-none w-[108px] sm:w-[122px] cursor-pointer" />
          <button v-if="toDate" @click="toDate = ''" class="text-gray-300 hover:text-red-400"><XCircle class="w-3 h-3" /></button>
        </div>
        <button v-if="hasDateFilter || statusFilter !== 'all' || searchQuery" @click="clearFilters"
          class="flex items-center gap-1 text-[10px] font-bold text-red-500 bg-red-50 border border-red-100 px-2 py-1.5 rounded-lg hover:bg-red-100 transition-all whitespace-nowrap">
          <XCircle class="w-3 h-3" /> Clear All
        </button>
      </div>
    </div>

    <!-- Loading / Empty / Table -->
    <div v-if="isLoading && !hasData" class="p-6 space-y-3">
      <div v-for="i in 5" :key="i" class="h-16 bg-gray-100 rounded-xl animate-pulse" />
    </div>
    <div v-else-if="!isLoading && filtered.length === 0"
      class="flex flex-col items-center justify-center py-20 text-center px-4">
      <div class="p-4 bg-gray-100 rounded-2xl mb-4"><Receipt class="w-10 h-10 text-gray-300" /></div>
      <p class="text-sm font-black text-gray-300">No Invoices Found</p>
      <p class="text-xs text-gray-300 mt-1">Try adjusting your filters</p>
    </div>

    <div v-else>
      <!-- Desktop header -->
      <div class="hidden sm:grid grid-cols-[1fr_1.4fr_0.8fr_0.8fr_0.8fr_0.6fr_auto_36px] gap-2 px-5 py-2.5
                  border-b border-gray-100 bg-gray-50/40 text-[10px] font-black text-gray-400 uppercase tracking-widest">
        <span>Invoice #</span><span>Customer</span><span>Date</span>
        <span class="text-right">Grand Total</span><span class="text-right">Outstanding</span>
        <span class="text-center">Status</span>
        <span class="text-center">Payment</span>
        <span />
      </div>

      <div class="divide-y divide-gray-100/80">
        <div v-for="row in filtered" :key="row.name">

          <!-- Row -->
          <div @click="toggleExpand(row.name)"
            :class="['grid gap-2 items-center px-3 sm:px-5 py-3 sm:py-3.5',
              'grid-cols-[1fr_auto_36px] sm:grid-cols-[1fr_1.4fr_0.8fr_0.8fr_0.8fr_0.6fr_auto_36px]',
              'hover:bg-gray-50/60 active:bg-gray-100/70 transition-colors cursor-pointer select-none',
              row.status === 'Overdue' ? 'bg-red-50/30' : '']">

            <!-- Mobile layout -->
            <div class="sm:hidden flex flex-col gap-0.5 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs font-black text-gray-900">{{ row.name }}</span>
                <span v-if="row.is_return" class="text-[9px] bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded-full font-bold">Return</span>
                <span :class="['inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold', themeClasses[getStatusInfo(row).theme]]">
                  <component :is="getStatusInfo(row).icon" class="w-2.5 h-2.5 flex-shrink-0" />
                  {{ getStatusInfo(row).label }}
                </span>
              </div>
              <span class="text-[10px] text-gray-500 font-medium truncate">{{ row.customer_name }}</span>
              <div class="flex items-center gap-3 flex-wrap mt-0.5">
                <span class="text-[9px] text-gray-400 flex items-center gap-0.5"><Calendar class="w-2.5 h-2.5" />{{ row.posting_date }}</span>
                <span class="text-[10px] font-black text-gray-900">{{ formatCurrency(row.grand_total, row.currency) }}</span>
                <span v-if="row.outstanding_amount > 0" class="text-[9px] font-bold text-red-500">Due: {{ formatCurrency(row.outstanding_amount, row.currency) }}</span>
              </div>
              <div v-if="row.docstatus === 1 && row.grand_total > 0" class="mt-1.5 w-full bg-gray-200 rounded-full h-1">
                <div :style="{ width: `${100 - outstandingPercent(row)}%` }"
                  :class="['h-1 rounded-full', row.status === 'Paid' ? 'bg-green-500' : row.status === 'Overdue' ? 'bg-red-400' : 'bg-blue-400']" />
              </div>
            </div>

            <!-- Desktop layout -->
            <div class="hidden sm:flex items-center gap-1.5 min-w-0">
              <span class="text-xs font-black text-gray-900 truncate">{{ row.name }}</span>
              <span v-if="row.is_return" class="text-[9px] bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded-full font-bold flex-shrink-0">Return</span>
            </div>
            <span class="hidden sm:block text-xs text-gray-600 font-medium truncate">{{ row.customer_name }}</span>
            <span class="hidden sm:flex items-center gap-1 text-xs text-gray-500">
              <Calendar class="w-3 h-3 flex-shrink-0 text-gray-400" />{{ row.posting_date }}
            </span>
            <span class="hidden sm:block text-xs font-black text-gray-900 text-right">{{ formatCurrency(row.grand_total, row.currency) }}</span>
            <div class="hidden sm:flex flex-col items-end gap-1">
              <span :class="['text-xs font-black', row.outstanding_amount > 0 ? 'text-red-600' : 'text-gray-400']">
                {{ row.outstanding_amount > 0 ? formatCurrency(row.outstanding_amount, row.currency) : '—' }}
              </span>
              <div v-if="row.docstatus === 1 && row.grand_total > 0" class="w-16 bg-gray-200 rounded-full h-1">
                <div :style="{ width: `${100 - outstandingPercent(row)}%` }"
                  :class="['h-1 rounded-full', row.status === 'Paid' ? 'bg-green-500' : row.status === 'Overdue' ? 'bg-red-400' : 'bg-blue-400']" />
              </div>
            </div>
            <span class="hidden sm:flex justify-center">
              <span :class="['inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold whitespace-nowrap', themeClasses[getStatusInfo(row).theme]]">
                <component :is="getStatusInfo(row).icon" class="w-2.5 h-2.5 flex-shrink-0" />
                {{ getStatusInfo(row).label }}
              </span>
            </span>

            <!-- Payment Received quick button -->
            <div class="flex justify-center" @click.stop>
              <button
                v-if="row.docstatus === 1 && row.outstanding_amount > 0"
                @click.stop="openPayRecvModal(row)"
                class="flex items-center gap-1 px-2 py-1.5 rounded-lg
                       bg-violet-600 hover:bg-violet-700 active:bg-violet-800
                       text-white text-[10px] font-black transition-colors
                       whitespace-nowrap shadow-sm"
                title="Record Payment"
              >
                <IndianRupee class="w-3 h-3 flex-shrink-0" />
                <span class="hidden sm:inline">Payment</span>
              </button>
              <span v-else class="w-6 sm:w-8" />
            </div>

            <div class="flex justify-center text-gray-400">
              <ChevronDown v-if="expandedRow === row.name" class="w-4 h-4 text-gray-700" />
              <ChevronRight v-else class="w-4 h-4" />
            </div>
          </div>

          <!-- Expanded panel -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out" enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0" leave-active-class="transition-all duration-150 ease-in"
            leave-from-class="opacity-100" leave-to-class="opacity-0"
          >
            <div v-if="expandedRow === row.name" class="border-t border-gray-100 bg-gray-50/70 px-3 sm:px-6 py-4">

              <div v-if="invDetail.loading && !detailData" class="space-y-2">
                <div v-for="i in 4" :key="i" class="h-8 bg-gray-200/60 rounded-lg animate-pulse" />
              </div>

              <div v-else-if="detailData && detailData.name === row.name" class="space-y-4">

                <!-- Meta cards -->
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Due Date</p>
                    <p :class="['text-xs font-black', detailData.status === 'Overdue' ? 'text-red-600' : 'text-gray-800']">{{ detailData.due_date || '—' }}</p>
                  </div>
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Paid Amount</p>
                    <p class="text-xs font-black text-green-700">{{ formatCurrency(detailData.paid_amount || 0, detailData.currency) }}</p>
                  </div>
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Discount</p>
                    <p class="text-xs font-black text-gray-800">{{ formatCurrency(detailData.discount_amount || 0, detailData.currency) }}</p>
                  </div>
                  <div class="bg-white rounded-xl p-3 border border-gray-100">
                    <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wide mb-1">Tax Template</p>
                    <p class="text-xs font-black text-gray-800 truncate">{{ detailData.taxes_and_charges || '—' }}</p>
                  </div>
                </div>

                <!-- Items table -->
                <div v-if="detailData.items?.length" class="bg-white border border-gray-100 rounded-xl overflow-hidden">
                  <div class="grid grid-cols-[1fr_0.5fr_0.5fr_0.7fr] gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-100 text-[9px] sm:text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    <span>Item</span><span class="text-center">Qty</span><span class="text-center">Rate</span><span class="text-right">Amount</span>
                  </div>
                  <div class="divide-y divide-gray-100/80 max-h-52 overflow-y-auto overscroll-contain">
                    <div v-for="item in detailData.items" :key="item.name"
                      class="grid grid-cols-[1fr_0.5fr_0.5fr_0.7fr] gap-2 px-4 py-2.5 items-center">
                      <div class="min-w-0">
                        <p class="text-xs font-semibold text-gray-800 truncate">{{ item.item_name }}</p>
                        <p class="text-[9px] text-gray-400 truncate">{{ item.item_code }}</p>
                        <p v-if="item.delivery_note" class="text-[9px] text-blue-500 font-semibold truncate">DN: {{ item.delivery_note }}</p>
                      </div>
                      <span class="text-xs text-gray-600 text-center font-medium">{{ item.qty }} {{ item.uom }}</span>
                      <span class="text-xs text-gray-600 text-center">{{ formatCurrency(item.rate, detailData.currency) }}</span>
                      <span class="text-xs font-black text-gray-900 text-right">{{ formatCurrency(item.amount, detailData.currency) }}</span>
                    </div>
                  </div>
                  <div class="border-t border-gray-200 px-4 py-3 space-y-1.5">
                    <div v-if="detailData.total_taxes_and_charges" class="flex justify-between text-xs text-gray-500">
                      <span>Taxes</span><span>{{ formatCurrency(detailData.total_taxes_and_charges, detailData.currency) }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-xs font-black text-gray-500 uppercase tracking-wide">Grand Total</span>
                      <span class="text-sm font-black text-gray-900">{{ formatCurrency(detailData.grand_total, detailData.currency) }}</span>
                    </div>
                    <div v-if="detailData.outstanding_amount > 0" class="flex justify-between items-center">
                      <span class="text-xs font-bold text-red-500 uppercase tracking-wide">Outstanding</span>
                      <span class="text-sm font-black text-red-600">{{ formatCurrency(detailData.outstanding_amount, detailData.currency) }}</span>
                    </div>
                  </div>
                </div>

                <!-- Payment schedule -->
                <div v-if="detailData.payment_schedule?.length" class="bg-white border border-gray-100 rounded-xl overflow-hidden">
                  <div class="px-4 py-2.5 bg-gray-50 border-b border-gray-100 text-[10px] font-black text-gray-500 uppercase tracking-widest">Payment Schedule</div>
                  <div class="divide-y divide-gray-100 max-h-36 overflow-y-auto">
                    <div v-for="ps in detailData.payment_schedule" :key="ps.name"
                      class="flex items-center justify-between gap-2 px-4 py-2.5">
                      <span class="text-xs text-gray-600 flex-shrink-0">{{ ps.due_date }}</span>
                      <span class="text-xs font-bold text-gray-500 truncate">{{ ps.payment_term }}</span>
                      <span class="text-xs font-black text-gray-900 flex-shrink-0">{{ formatCurrency(ps.payment_amount, detailData.currency) }}</span>
                      <span :class="['text-[9px] font-bold px-1.5 py-0.5 rounded-full flex-shrink-0', ps.outstanding > 0 ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600']">
                        {{ ps.outstanding > 0 ? 'Due' : 'Paid' }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- ══ ACTION BUTTONS ══ -->
                <div class="flex flex-wrap gap-2 justify-end pt-1">

                  <!-- Print -->
                  <button @click.stop="openPrint(row.name)"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gray-900
                           hover:bg-gray-700 text-white text-xs font-bold transition-colors shadow-sm">
                    <Printer class="w-3.5 h-3.5" />Print / PDF
                  </button>

                  <!-- Payment Received (in expanded panel too) -->
                  <button
                    v-if="detailData.docstatus === 1 && detailData.outstanding_amount > 0"
                    @click.stop="openPayRecvModal(detailData)"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-violet-600
                           hover:bg-violet-700 text-white text-xs font-bold transition-colors shadow-sm"
                  >
                    <IndianRupee class="w-3.5 h-3.5" />
                    Payment Received
                  </button>

                  <!-- Send Payment Request -->
                  <button
                    v-if="detailData.docstatus === 1 && detailData.outstanding_amount > 0"
                    @click.stop="openPaymentModal(row.name)"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-green-600
                           hover:bg-green-700 text-white text-xs font-bold transition-colors shadow-sm"
                  >
                    <Mail class="w-3.5 h-3.5" />
                    Send Payment Request
                  </button>

                  <!-- Submit (draft) -->
                  <button v-if="detailData.docstatus === 0" @click.stop="handleSubmit(row.name)" :disabled="processingId === row.name"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-bold transition-colors">
                    <RefreshCcw v-if="processingId === row.name && processingAction === 'submit'" class="w-3.5 h-3.5 animate-spin" />
                    <Send v-else class="w-3.5 h-3.5" />Submit
                  </button>

                  <!-- Delete (draft) -->
                  <button v-if="detailData.docstatus === 0" @click.stop="handleDelete(row.name)" :disabled="processingId === row.name"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-50 hover:bg-red-100 disabled:opacity-60 text-red-600 text-xs font-bold border border-red-200 transition-colors">
                    <RefreshCcw v-if="processingId === row.name && processingAction === 'delete'" class="w-3.5 h-3.5 animate-spin" />
                    <Trash2 v-else class="w-3.5 h-3.5" />Delete
                  </button>

                  <!-- Cancel (submitted) -->
                  <button v-if="detailData.docstatus === 1" @click.stop="handleCancel(row.name)" :disabled="processingId === row.name"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-orange-50 hover:bg-orange-100 disabled:opacity-60 text-orange-600 text-xs font-bold border border-orange-200 transition-colors">
                    <RefreshCcw v-if="processingId === row.name && processingAction === 'cancel'" class="w-3.5 h-3.5 animate-spin" />
                    <Ban v-else class="w-3.5 h-3.5" />Cancel
                  </button>

                  <!-- Delete (cancelled) -->
                  <button v-if="detailData.docstatus === 2" @click.stop="handleDelete(row.name)" :disabled="processingId === row.name"
                    class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-50 hover:bg-red-100 disabled:opacity-60 text-red-600 text-xs font-bold border border-red-200 transition-colors">
                    <RefreshCcw v-if="processingId === row.name && processingAction === 'delete'" class="w-3.5 h-3.5 animate-spin" />
                    <Trash2 v-else class="w-3.5 h-3.5" />Delete
                  </button>
                </div>
              </div>

              <div v-else class="space-y-2">
                <div v-for="i in 3" :key="i" class="h-8 bg-gray-200/60 rounded-lg animate-pulse" />
              </div>

            </div>
          </Transition>

        </div>
      </div>

      <div v-if="isLoading && hasData" class="flex justify-center py-4">
        <RefreshCcw class="w-5 h-5 text-gray-400 animate-spin" />
      </div>
    </div>
  </div>
</template>
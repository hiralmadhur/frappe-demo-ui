<script setup lang="ts">
/**
 * PaymentRequestModal — Reusable component
 * Props: invoiceName, show
 * Events: @close, @sent
 *
 * Features:
 * - First send: "Send Email" button
 * - After success: "Resend Email" + send count tracking
 * - No debug button — errors shown inline with clear messages
 * - Fully responsive modal
 */

import { ref, computed, watch } from 'vue'
import { createResource } from 'frappe-ui'
import {
  Mail, X, Send, Loader2, ShieldAlert,
  CheckCheck, RefreshCcw, AlertTriangle, Receipt,
  RotateCcw,
} from 'lucide-vue-next'

const props = defineProps<{
  invoiceName: string
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'sent', result: any): void
}>()

// ─── STATE ────────────────────────────────────────────────────────────────────
const loading    = ref(false)
const result     = ref<any | null>(null)
const error      = ref('')
const sendCount  = ref(0)   // how many times sent this session

// Reset when modal opens with new invoice
watch(() => [props.show, props.invoiceName], ([show]) => {
  if (show) {
    loading.value   = false
    result.value    = null
    error.value     = ''
    sendCount.value = 0
  }
})

// ─── API ──────────────────────────────────────────────────────────────────────
const sendReq = createResource({
  url: 'my_frappe_app.payment_utils.api_send_payment_request',
  onSuccess(data: any) {
    loading.value = false
    result.value  = data
    error.value   = ''
    sendCount.value++
    emit('sent', data)
  },
  onError(err: any) {
    loading.value = false
    error.value   = parseError(err)
  },
})

// ─── ACTIONS ──────────────────────────────────────────────────────────────────
function doSend() {
  loading.value = true
  error.value   = ''
  sendReq.fetch({
    invoice_name: props.invoiceName,
    send_count:   sendCount.value + 1,   // backend shows REMINDER badge if > 1
  })
}

function close() { emit('close') }

// ─── COMPUTED ─────────────────────────────────────────────────────────────────
const hasSentOnce  = computed(() => result.value?.status === 'success')
const isReminder   = computed(() => sendCount.value >= 1)

const sendBtnLabel = computed(() => {
  if (loading.value) return 'Sending…'
  if (hasSentOnce.value) return 'Resend Email'
  return 'Send Email'
})

const sendBtnIcon = computed(() =>
  loading.value ? Loader2 : hasSentOnce.value ? RotateCcw : Send
)

// ─── ERROR PARSER ─────────────────────────────────────────────────────────────
function parseError(err: any): string {
  if (!err) return 'Unknown error'
  let msg = err?.message || err?.exc || ''
  msg = msg.replace(/<[^>]*>/g, '').trim()

  // Extract last meaningful line from Python traceback
  if (msg.includes('Traceback') || msg.includes('\\n')) {
    const lines = msg.split('\\n')
      .map((l: string) => l.trim())
      .filter((l: string) =>
        l.length > 0 &&
        !l.startsWith('Traceback') &&
        !l.startsWith('File "') &&
        !l.startsWith('During handling') &&
        !/^\\s{2,}/.test(l),
      )
    msg = lines[lines.length - 1] || msg.split('\\n')[0]
  }

  // Map common errors to friendly messages
  if (msg.includes('does not exist')) return 'Invoice not found. Please refresh and try again.'
  if (msg.includes('not submitted')) return 'Invoice must be submitted before sending payment request.'
  if (msg.includes('fully paid')) return 'This invoice is already fully paid.'
  if (msg.includes('No email found')) return msg
  if (msg.includes('wkhtmltopdf') || msg.includes('PDF')) return 'PDF generation failed. Please check server configuration.'
  if (msg.includes('SMTP') || msg.includes('smtp') || msg.includes('sendmail')) return 'Email sending failed. Check outgoing email configuration in ERPNext.'

  return msg || 'Something went wrong. Check ERPNext Error Log for details.'
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition-all duration-150"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="show"
        class="fixed inset-0 z-[999] flex items-end sm:items-center justify-center
               sm:p-4 bg-black/50 backdrop-blur-sm"
        @click.self="close"
      >
        <!-- Sheet on mobile, centered modal on desktop -->
        <div class="bg-white w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl
                    shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

          <!-- ── Header ── -->
          <div class="flex items-center justify-between px-5 py-4
                      border-b border-gray-100 flex-shrink-0">
            <div class="flex items-center gap-3 min-w-0">
              <div class="p-2 bg-green-50 rounded-xl flex-shrink-0">
                <Mail class="w-4 h-4 text-green-600" />
              </div>
              <div class="min-w-0">
                <h3 class="text-sm font-black text-gray-900">
                  {{ hasSentOnce ? 'Resend Payment Request' : 'Payment Request Email' }}
                </h3>
                <p class="text-[10px] text-gray-400 font-medium mt-0.5 truncate">
                  {{ invoiceName }}
                  <span v-if="hasSentOnce && sendCount > 0"
                    class="ml-1.5 bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full text-[9px] font-bold">
                    Sent {{ sendCount }}x
                  </span>
                </p>
              </div>
            </div>
            <button @click="close"
              class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400
                     transition-colors flex-shrink-0 ml-2">
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- ── Body ── -->
          <div class="px-5 py-4 space-y-4 overflow-y-auto flex-1">

            <!-- Info banner — changes after first send -->
            <div v-if="!hasSentOnce"
              class="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
              <p class="text-xs text-blue-700 leading-relaxed">
                The invoice PDF will be emailed to the customer with a
                <strong>UPI QR Code</strong> for instant payment via GPay,
                PhonePe, or any UPI app.
              </p>
            </div>

            <!-- Reminder info banner -->
            <div v-if="hasSentOnce && !error"
              class="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
              <p class="text-xs text-amber-700 leading-relaxed">
                <strong>Resend</strong> will send a
                <span class="bg-amber-200 text-amber-800 px-1.5 py-0.5 rounded font-bold text-[10px]">
                  PAYMENT REMINDER
                </span>
                email with the same invoice PDF. The customer will see it marked
                as a reminder.
              </p>
            </div>

            <!-- ── Error block ── -->
            <div v-if="error"
              class="flex items-start gap-3 bg-red-50 border border-red-200
                     rounded-xl px-4 py-3">
              <ShieldAlert class="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <div class="flex-1 min-w-0">
                <p class="text-xs font-black text-red-700 mb-1.5">
                  Failed to send email
                </p>
                <p class="text-xs text-red-600 leading-relaxed break-words">
                  {{ error }}
                </p>
                <div class="mt-2 pt-2 border-t border-red-100">
                  <p class="text-[10px] text-red-400">
                    &#128196; Check: ERPNext &#8594; Error Log &#8594; search "PaymentRequest"
                  </p>
                </div>
              </div>
            </div>

            <!-- ── Success block ── -->
            <div v-if="hasSentOnce" class="space-y-3">

              <!-- Success banner -->
              <div class="flex items-center gap-3 bg-green-50 border border-green-200
                          rounded-xl px-4 py-3">
                <div class="p-1.5 bg-green-100 rounded-lg flex-shrink-0">
                  <CheckCheck class="w-4 h-4 text-green-600" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-black text-green-800">
                    Email sent successfully!
                  </p>
                  <p class="text-[10px] text-green-600 mt-0.5">
                    {{ result.customer }}
                  </p>
                </div>
              </div>

              <!-- Details card -->
              <div class="bg-gray-50 rounded-xl border border-gray-100 overflow-hidden">
                <div class="divide-y divide-gray-100">

                  <div class="flex items-center gap-3 px-4 py-3">
                    <Mail class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    <div class="flex-1 min-w-0">
                      <p class="text-[10px] font-bold text-gray-500 uppercase tracking-wide">
                        Sent to
                      </p>
                      <p class="text-xs text-gray-700 mt-0.5 break-all">
                        {{ result.email }}
                      </p>
                    </div>
                    <span class="text-[9px] font-black px-2 py-0.5 rounded-full
                                 bg-green-50 text-green-600 flex-shrink-0">
                      ✓ Delivered
                    </span>
                  </div>

                  <div class="flex items-center gap-3 px-4 py-3">
                    <Receipt class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    <div class="flex-1 min-w-0">
                      <p class="text-[10px] font-bold text-gray-500 uppercase tracking-wide">
                        PDF Attached
                      </p>
                      <p class="text-xs text-gray-600 mt-0.5">
                        Invoice_{{ result.invoice }}.pdf
                        <span class="text-gray-400">— {{ result.pdf_kb }} KB</span>
                      </p>
                    </div>
                    <CheckCheck class="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                  </div>

                  <div v-if="result.is_reminder"
                    class="flex items-center gap-3 px-4 py-3 bg-amber-50/50">
                    <AlertTriangle class="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                    <p class="text-[10px] text-amber-700 font-medium">
                      Sent as Reminder #{{ result.send_count }}
                    </p>
                  </div>

                </div>
              </div>
            </div>

          </div>

          <!-- ── Footer ── -->
          <div class="flex items-center gap-2 px-5 py-4 border-t border-gray-100
                      bg-gray-50/80 flex-shrink-0">

            <button
              @click="close"
              :disabled="loading"
              class="px-4 py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200
                     disabled:opacity-50 text-xs font-bold text-gray-600
                     transition-colors"
            >
              {{ hasSentOnce ? 'Done' : 'Cancel' }}
            </button>

            <div class="flex-1" />

            <!-- Send / Resend button -->
            <button
              @click="doSend"
              :disabled="loading"
              :class="[
                'flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold',
                'transition-all shadow-sm disabled:opacity-50',
                hasSentOnce
                  ? 'bg-amber-500 hover:bg-amber-600 text-white'
                  : 'bg-green-600 hover:bg-green-700 text-white',
              ]"
            >
              <component
                :is="sendBtnIcon"
                :class="['w-3.5 h-3.5', loading ? 'animate-spin' : '']"
              />
              {{ sendBtnLabel }}
            </button>

          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>
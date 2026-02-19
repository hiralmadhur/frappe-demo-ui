<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { Newspaper, Hourglass, CheckCircle } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: boolean
  item: any | null
  allItems: any[]
  subscriptionItems: any[]
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'submit', payload: any): void
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

// ── INTERNAL FORM STATE ──
const startDate       = ref(new Date().toISOString().split('T')[0])
const months          = ref(1)
const schedule        = ref<Record<string, Record<string, number>>>({})
const additionalItems = ref<string[]>([])
const localError      = ref('')

// Reset on open
const open = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const initForm = () => {
  if (!props.item) return
  startDate.value       = new Date().toISOString().split('T')[0]
  months.value          = 1
  additionalItems.value = []
  localError.value      = ''
  schedule.value = {
    [props.item.item_code]: {
      Monday: 1, Tuesday: 1, Wednesday: 1, Thursday: 1, Friday: 1, Saturday: 1, Sunday: 1
    }
  }
}

// Watch open to init
import { watch } from 'vue'
watch(() => props.modelValue, (v) => { if (v) initForm() })

// ── HELPERS ──
const getDayQty = (itemCode: string, day: string) => schedule.value[itemCode]?.[day] ?? 0

const setDayQty = (itemCode: string, day: string, qty: number) => {
  if (!schedule.value[itemCode]) schedule.value[itemCode] = {}
  schedule.value[itemCode][day] = Math.max(0, Math.min(qty, 99))
}

const toggleDay = (itemCode: string, day: string) => {
  const cur = getDayQty(itemCode, day)
  setDayQty(itemCode, day, cur > 0 ? 0 : 1)
}

const isDayActive = (itemCode: string, day: string) => getDayQty(itemCode, day) > 0

const getDayPrice = (item: any, day: string): number => item.day_prices?.[day] ?? 0

const formatPrice = (val: number) =>
  val > 0 ? `₹${val}` : '—'

// Additional items (subscription items except primary)
const availableAdditional = computed(() =>
  props.subscriptionItems.filter((i: any) => i.item_code !== props.item?.item_code)
)

const isAdditionalSelected = (itemCode: string) => additionalItems.value.includes(itemCode)

const toggleAdditional = (item: any) => {
  const idx = additionalItems.value.indexOf(item.item_code)
  if (idx === -1) {
    additionalItems.value.push(item.item_code)
    if (!schedule.value[item.item_code]) {
      schedule.value[item.item_code] = {
        Monday: 0, Tuesday: 0, Wednesday: 0, Thursday: 0, Friday: 0, Saturday: 0, Sunday: 0
      }
    }
  } else {
    additionalItems.value.splice(idx, 1)
    delete schedule.value[item.item_code]
  }
}

// Weekly cost estimate
const weeklyEstimate = computed(() => {
  if (!props.item) return 0
  let total = 0
  const allCodes = [props.item.item_code, ...additionalItems.value]
  for (const ic of allCodes) {
    const sched = schedule.value[ic] || {}
    const itemObj = props.allItems.find((i: any) => i.item_code === ic)
    if (!itemObj) continue
    for (const day of ALL_DAYS) {
      total += (sched[day] || 0) * (getDayPrice(itemObj, day))
    }
  }
  return total
})

// ── SUBMIT ──
const handleSubmit = () => {
  if (!props.item) return
  const primaryCode  = props.item.item_code
  const allCodes     = [primaryCode, ...additionalItems.value]
  const scheduleItems = allCodes.map((ic) => {
    const sched = schedule.value[ic] || {}
    return {
      item_code:        ic,
      is_primary_item:  ic === primaryCode ? 1 : 0,
      monday_qty:    sched['Monday']    || 0,
      tuesday_qty:   sched['Tuesday']   || 0,
      wednesday_qty: sched['Wednesday'] || 0,
      thursday_qty:  sched['Thursday']  || 0,
      friday_qty:    sched['Friday']    || 0,
      saturday_qty:  sched['Saturday']  || 0,
      sunday_qty:    sched['Sunday']    || 0,
    }
  })

  const primarySched = scheduleItems.find(s => s.is_primary_item)
  const hasAnyDay = primarySched && ALL_DAYS.some(d => (primarySched as any)[DAY_QTY_FIELD[d]] > 0)
  if (!hasAnyDay) {
    localError.value = 'Please select at least one day for the primary item.'
    return
  }

  localError.value = ''
  emit('submit', {
    schedule_items: JSON.stringify(scheduleItems),
    start_date:     startDate.value,
    months:         months.value
  })
}

const displayError = computed(() => localError.value || props.error)
</script>

<template>
  <Dialog v-model="open" :options="{ title: 'Create Subscription Plan', size: 'lg' }">
    <template #body-content>
      <div class="space-y-5">

        <!-- How it works -->
        <div class="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
          <Hourglass class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
          <div>
            <p class="font-semibold text-sm text-amber-800">How it works</p>
            <p class="text-xs text-amber-700 mt-1">
              After you send the request, seller will review it. Once accepted, daily delivery starts from the next day automatically.
            </p>
          </div>
        </div>

        <!-- Primary item -->
        <div class="flex items-start gap-3 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
          <Newspaper class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div class="flex-1">
            <p class="font-semibold text-sm text-blue-900">{{ item?.item_name }}</p>
            <p class="text-xs text-blue-600 mt-0.5">Primary item — configure day-wise delivery below</p>
          </div>
        </div>

        <!-- PRIMARY — day-wise schedule table -->
        <div v-if="item">
          <label class="text-xs font-bold text-gray-700 mb-2 block uppercase tracking-wide">
            📅 Day-wise Delivery Schedule — {{ item.item_name }}
          </label>
          <div class="border border-gray-200 rounded-xl overflow-hidden">
            <table class="w-full text-xs">
              <thead class="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th class="px-3 py-2 text-left font-bold text-gray-500 uppercase">Day</th>
                  <th class="px-3 py-2 text-center font-bold text-gray-500 uppercase">Deliver?</th>
                  <th class="px-3 py-2 text-center font-bold text-gray-500 uppercase">Qty</th>
                  <th class="px-3 py-2 text-right font-bold text-gray-500 uppercase">Price/copy</th>
                  <th class="px-3 py-2 text-right font-bold text-gray-500 uppercase">Day Cost</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="day in ALL_DAYS" :key="day"
                  :class="isDayActive(item.item_code, day) ? 'bg-blue-50/50' : 'bg-white'">
                  <td class="px-3 py-2 font-semibold text-gray-700">{{ day }}</td>
                  <td class="px-3 py-2 text-center">
                    <button @click="toggleDay(item.item_code, day)" :class="[
                      'w-8 h-5 rounded-full transition-colors relative',
                      isDayActive(item.item_code, day) ? 'bg-blue-600' : 'bg-gray-200'
                    ]">
                      <span :class="[
                        'absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform',
                        isDayActive(item.item_code, day) ? 'translate-x-3' : 'translate-x-0.5'
                      ]" />
                    </button>
                  </td>
                  <td class="px-3 py-2">
                    <div v-if="isDayActive(item.item_code, day)" class="flex items-center justify-center gap-1">
                      <button @click="setDayQty(item.item_code, day, getDayQty(item.item_code, day) - 1)"
                        :disabled="getDayQty(item.item_code, day) <= 1"
                        class="w-5 h-5 rounded bg-gray-100 hover:bg-gray-200 flex items-center justify-center disabled:opacity-30 text-xs font-bold">−</button>
                      <span class="w-5 text-center font-black text-blue-600 text-sm">{{ getDayQty(item.item_code, day) }}</span>
                      <button @click="setDayQty(item.item_code, day, getDayQty(item.item_code, day) + 1)"
                        :disabled="getDayQty(item.item_code, day) >= 99"
                        class="w-5 h-5 rounded bg-gray-100 hover:bg-gray-200 flex items-center justify-center disabled:opacity-30 text-xs font-bold">+</button>
                    </div>
                    <span v-else class="block text-center text-gray-300 font-bold">—</span>
                  </td>
                  <td class="px-3 py-2 text-right text-gray-500">
                    <span v-if="getDayPrice(item, day) > 0">₹{{ getDayPrice(item, day) }}</span>
                    <span v-else class="text-red-400 text-[10px]">No price</span>
                  </td>
                  <td class="px-3 py-2 text-right font-bold"
                    :class="isDayActive(item.item_code, day) ? 'text-gray-800' : 'text-gray-300'">
                    <span v-if="isDayActive(item.item_code, day) && getDayPrice(item, day) > 0">
                      ₹{{ (getDayQty(item.item_code, day) * getDayPrice(item, day)).toFixed(2) }}
                    </span>
                    <span v-else>—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Additional items -->
        <div v-if="availableAdditional.length > 0">
          <label class="text-xs font-bold text-gray-700 mb-2 block uppercase tracking-wide">
            ➕ Add More Items (Optional)
          </label>
          <div class="space-y-3">
            <div v-for="aitem in availableAdditional" :key="aitem.item_code">
              <div @click="toggleAdditional(aitem)" :class="[
                'flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all',
                isAdditionalSelected(aitem.item_code)
                  ? 'border-purple-300 bg-purple-50' : 'border-gray-200 bg-gray-50 hover:border-gray-300'
              ]">
                <div class="flex items-center gap-2">
                  <div :class="['w-4 h-4 rounded border-2 flex items-center justify-center',
                    isAdditionalSelected(aitem.item_code) ? 'border-purple-500 bg-purple-500' : 'border-gray-300']">
                    <CheckCircle v-if="isAdditionalSelected(aitem.item_code)" class="w-3 h-3 text-white" />
                  </div>
                  <span class="text-xs font-semibold text-gray-700">{{ aitem.item_name }}</span>
                </div>
                <span class="text-[10px] text-gray-500">Today: {{ aitem.formatted_price }}</span>
              </div>

              <!-- Additional item day schedule -->
              <div v-if="isAdditionalSelected(aitem.item_code)"
                class="mt-2 ml-2 border border-purple-200 rounded-xl overflow-hidden">
                <table class="w-full text-xs">
                  <thead class="bg-purple-50 border-b border-purple-200">
                    <tr>
                      <th class="px-3 py-1.5 text-left font-bold text-purple-600">Day</th>
                      <th class="px-3 py-1.5 text-center font-bold text-purple-600">Deliver?</th>
                      <th class="px-3 py-1.5 text-center font-bold text-purple-600">Qty</th>
                      <th class="px-3 py-1.5 text-right font-bold text-purple-600">Price</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-purple-100">
                    <tr v-for="day in ALL_DAYS" :key="day"
                      :class="isDayActive(aitem.item_code, day) ? 'bg-purple-50/30' : 'bg-white'">
                      <td class="px-3 py-1.5 font-semibold text-gray-600">{{ DAY_SHORT[day] }}</td>
                      <td class="px-3 py-1.5 text-center">
                        <button @click="toggleDay(aitem.item_code, day)" :class="[
                          'w-7 h-4 rounded-full transition-colors relative',
                          isDayActive(aitem.item_code, day) ? 'bg-purple-500' : 'bg-gray-200'
                        ]">
                          <span :class="[
                            'absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform',
                            isDayActive(aitem.item_code, day) ? 'translate-x-3' : 'translate-x-0.5'
                          ]" />
                        </button>
                      </td>
                      <td class="px-3 py-1.5">
                        <div v-if="isDayActive(aitem.item_code, day)" class="flex items-center justify-center gap-1">
                          <button @click="setDayQty(aitem.item_code, day, getDayQty(aitem.item_code, day) - 1)"
                            :disabled="getDayQty(aitem.item_code, day) <= 1"
                            class="w-4 h-4 rounded bg-gray-100 hover:bg-gray-200 flex items-center justify-center font-bold disabled:opacity-30 text-xs">−</button>
                          <span class="w-4 text-center font-black text-purple-600">{{ getDayQty(aitem.item_code, day) }}</span>
                          <button @click="setDayQty(aitem.item_code, day, getDayQty(aitem.item_code, day) + 1)"
                            :disabled="getDayQty(aitem.item_code, day) >= 99"
                            class="w-4 h-4 rounded bg-gray-100 hover:bg-gray-200 flex items-center justify-center font-bold disabled:opacity-30 text-xs">+</button>
                        </div>
                        <span v-else class="block text-center text-gray-300">—</span>
                      </td>
                      <td class="px-3 py-1.5 text-right text-gray-500">
                        <span v-if="getDayPrice(aitem, day) > 0">₹{{ getDayPrice(aitem, day) }}</span>
                        <span v-else class="text-red-400 text-[9px]">No price</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Start date & duration -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-xs font-bold text-gray-700 mb-1.5 block">Start Date</label>
            <input type="date" v-model="startDate"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
          </div>
          <div>
            <label class="text-xs font-bold text-gray-700 mb-1.5 block">Duration</label>
            <select v-model="months"
              class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent">
              <option :value="1">1 Month</option>
              <option :value="3">3 Months</option>
              <option :value="6">6 Months</option>
              <option :value="12">12 Months</option>
            </select>
          </div>
        </div>

        <!-- Error -->
        <div v-if="displayError" class="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
          <p class="text-xs text-red-700">{{ displayError }}</p>
        </div>
      </div>
    </template>

    <template #actions>
      <div class="flex gap-2 w-full">
        <Button variant="outline" class="flex-1" @click="open = false">Cancel</Button>
        <Button variant="solid" theme="blue" class="flex-1" :loading="loading" @click="handleSubmit">
          <template #prefix>
            <CheckCircle v-if="!loading" class="w-4 h-4" />
          </template>
          Send Subscription Request
        </Button>
      </div>
    </template>
  </Dialog>
</template>
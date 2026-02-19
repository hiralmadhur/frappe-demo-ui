<script setup lang="ts">
import { computed } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { Package, MapPin, Minus, Plus, Trash2, CheckCircle } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: boolean
  cartItems: any[]
  cartTotal: number
  totalCartItems: number
  filters: { pincode?: string; society?: string }
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'update-cart', itemName: string, delta: number): void
  (e: 'remove-from-cart', itemName: string): void
  (e: 'place-order'): void
}>()

const open = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val)
</script>

<template>
  <Dialog v-model="open" :options="{ title: 'Order Summary', size: 'lg' }">
    <template #body-content>
      <div class="space-y-4">

        <!-- Delivery info -->
        <div v-if="filters.pincode || filters.society"
          class="flex items-start gap-2 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
          <MapPin class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
          <p class="text-xs text-blue-700">
            <span class="font-semibold">Delivery to: </span>
            <span v-if="filters.society">{{ filters.society }}</span>
            <span v-if="filters.society && filters.pincode"> · </span>
            <span v-if="filters.pincode">PIN {{ filters.pincode }}</span>
          </p>
        </div>

        <!-- Cart items -->
        <div class="space-y-2 max-h-72 overflow-y-auto pr-1">
          <div
            v-for="item in cartItems" :key="item.name"
            class="flex items-center gap-3 bg-gray-50 rounded-xl p-3 border border-gray-100"
          >
            <div class="w-11 h-11 rounded-lg overflow-hidden bg-white border border-gray-100 flex-shrink-0 flex items-center justify-center">
              <img v-if="item.image" :src="item.image" class="w-full h-full object-cover" />
              <Package v-else class="w-5 h-5 text-gray-200" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-gray-800 text-sm line-clamp-1">{{ item.item_name }}</p>
              <p class="text-xs text-gray-400">{{ item.formatted_price }} / {{ item.stock_uom }}</p>
              <div class="flex items-center gap-1 mt-1.5 bg-white rounded-lg border border-gray-200 w-fit p-0.5">
                <Button variant="ghost" size="sm" @click="emit('update-cart', item.name, -1)">
                  <template #icon><Minus class="w-3 h-3" /></template>
                </Button>
                <span class="font-bold text-sm text-blue-600 w-5 text-center">{{ item.qty }}</span>
                <Button variant="ghost" size="sm" @click="emit('update-cart', item.name, 1)">
                  <template #icon><Plus class="w-3 h-3" /></template>
                </Button>
              </div>
            </div>
            <div class="flex flex-col items-end gap-2 flex-shrink-0">
              <span class="font-bold text-sm text-gray-900">{{ formatCurrency(item.subtotal) }}</span>
              <Button variant="ghost" size="sm" theme="red" @click="emit('remove-from-cart', item.name)">
                <template #icon><Trash2 class="w-3 h-3" /></template>
              </Button>
            </div>
          </div>
        </div>

        <!-- Totals -->
        <div class="border-t border-gray-100 pt-3 space-y-1.5 text-sm">
          <div class="flex justify-between text-gray-500">
            <span>Subtotal ({{ totalCartItems }} items)</span>
            <span>{{ formatCurrency(cartTotal) }}</span>
          </div>
          <div class="flex justify-between text-gray-500">
            <span>Delivery</span>
            <span class="text-green-600 font-semibold">Free</span>
          </div>
          <div class="flex justify-between font-black text-gray-900 pt-2 border-t border-gray-100">
            <span>Total</span>
            <span>{{ formatCurrency(cartTotal) }}</span>
          </div>
        </div>

        <!-- Error -->
        <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl px-4 py-3">
          {{ error }}
        </div>
      </div>
    </template>

    <template #actions>
      <div class="flex gap-2 w-full">
        <Button variant="outline" class="flex-1" @click="open = false">Cancel</Button>
        <Button variant="solid" theme="blue" class="flex-1"
          :loading="loading" :disabled="loading || cartItems.length === 0"
          @click="emit('place-order')">
          <template #prefix>
            <CheckCircle v-if="!loading" class="w-4 h-4" />
          </template>
          {{ loading ? 'Placing Order...' : 'Place Order' }}
        </Button>
      </div>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { createResource, FormControl, LoadingIndicator, Avatar, Button } from 'frappe-ui'
import { MapPin, Building, Layers, Store, FilterX } from 'lucide-vue-next'

// --- TYPES ---
interface Option {
  label: string
  value: string
}

interface SidebarData {
  customer: { name: string; customer_name: string } | null
  pincode_list: Option[]
  pincode_map: Record<string, { societies: Option[], sellers: Option[] }>
  all_categories: Option[]
}

const emit = defineEmits(['update:filters'])

// --- STATE ---
const selectedPincode = ref('')
const selectedSociety = ref('')
const selectedCategory = ref('')
const selectedSeller = ref('')

// --- MAIN RESOURCE ---
const sidebarData = createResource({
  url: 'my_frappe_app.api.get_customer_sidebar_data',
  auto: true,
  onSuccess(data: SidebarData) {
    if (data.pincode_list?.length > 0) {
      selectedPincode.value = data.pincode_list[0].value
    }
  }
})

// --- COMPUTED ---
const pincodeOptions = computed(() => (sidebarData.data as SidebarData)?.pincode_list || [])

const societyOptions = computed(() => {
  const pin = selectedPincode.value
  const map = (sidebarData.data as SidebarData)?.pincode_map
  return map?.[pin]?.societies || []
})

const sellerOptions = computed(() => {
  const pin = selectedPincode.value
  const map = (sidebarData.data as SidebarData)?.pincode_map
  return map?.[pin]?.sellers || []
})

const categoryOptions = computed(() => (sidebarData.data as SidebarData)?.all_categories || [])

// Helper to emit all filters including customer
const emitFilters = () => {
  const customer = (sidebarData.data as SidebarData)?.customer
  emit('update:filters', {
    pincode: selectedPincode.value,
    society: selectedSociety.value,
    category: selectedCategory.value,
    seller: selectedSeller.value,
    customer: customer?.name || ''        // ← FIX: customer.name now included
  })
}

// --- WATCHERS ---
watch(selectedPincode, () => {
  selectedSociety.value = ''
  selectedSeller.value = ''
  selectedCategory.value = ''
})

watch([selectedPincode, selectedSociety, selectedCategory, selectedSeller], () => {
  emitFilters()
})

// Also emit when sidebarData loads (so customer is available immediately)
watch(() => sidebarData.data, () => {
  emitFilters()
})

const resetFilters = () => {
  const data = sidebarData.data as SidebarData
  selectedPincode.value = data?.pincode_list[0]?.value || ''
  selectedSociety.value = ''
  selectedCategory.value = ''
  selectedSeller.value = ''
}
</script>

<template>
  <div class="flex flex-col h-screen bg-white border-r border-gray-100 w-72 flex-shrink-0 sticky top-0">

    <div class="p-6 border-b border-gray-100 bg-gray-50/50">
      <div class="flex items-center gap-3">
        <Avatar
          :label="(sidebarData.data as SidebarData)?.customer?.customer_name || 'C'"
          size="lg" shape="square" class="ring-2 ring-white shadow-sm"
        />
        <div class="overflow-hidden">
          <h3 class="font-black text-gray-900 truncate text-sm">
            {{ (sidebarData.data as SidebarData)?.customer?.customer_name || 'User' }}
          </h3>
          <p class="text-xs text-gray-500 font-medium">Customer Dashboard</p>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar">
      <div v-if="sidebarData.loading" class="flex justify-center py-10"><LoadingIndicator /></div>

      <div v-else class="space-y-6">
        <div class="space-y-2">
          <label class="flex items-center gap-2 text-gray-400">
            <MapPin class="w-3 h-3" /><span class="text-[10px] font-bold uppercase">Pincode</span>
          </label>
          <FormControl type="select" v-model="selectedPincode" :options="pincodeOptions" variant="subtle" />
        </div>

        <div class="space-y-2">
          <label class="flex items-center gap-2 text-gray-400">
            <Building class="w-3 h-3" /><span class="text-[10px] font-bold uppercase">Society</span>
          </label>
          <FormControl type="select" v-model="selectedSociety" :options="societyOptions" :disabled="!selectedPincode" variant="subtle" />
        </div>

        <div class="h-px bg-gray-100"></div>

        <div class="space-y-2">
          <label class="flex items-center gap-2 text-gray-400">
            <Layers class="w-3 h-3" /><span class="text-[10px] font-bold uppercase">Category</span>
          </label>
          <FormControl type="select" v-model="selectedCategory" :options="categoryOptions" variant="subtle" />
        </div>

        <div class="space-y-2">
          <label class="flex items-center gap-2 text-gray-400">
            <Store class="w-3 h-3" /><span class="text-[10px] font-bold uppercase">Seller</span>
          </label>
          <FormControl type="select" v-model="selectedSeller" :options="sellerOptions" :disabled="!selectedPincode" variant="outline" />
        </div>
      </div>
    </div>

    <div class="p-4 border-t border-gray-100 bg-gray-50/30">
      <Button v-if="selectedSeller || selectedCategory || selectedSociety" variant="subtle" theme="gray" class="w-full" @click="resetFilters">
        <template #prefix><FilterX class="w-4 h-4" /></template>Clear Filters
      </Button>
      <p v-else class="text-center text-[10px] text-gray-400 font-medium">Customer App v1.0</p>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #f3f4f6; border-radius: 10px; }
</style>
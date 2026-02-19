<script setup lang="ts">
import { ref, computed } from 'vue'
import { createResource, LoadingIndicator, Avatar, Button } from 'frappe-ui'
import { MapPin, Building, Layers, Store, FilterX, ChevronRight, ChevronDown, X } from 'lucide-vue-next'

interface Option { label: string; value: string }
interface SidebarData {
  customer: { name: string; customer_name: string } | null
  pincode_list: Option[]
  pincode_map: Record<string, { societies: Option[], sellers: Option[] }>
  all_categories: Option[]
}

const props = defineProps<{ isOpen?: boolean }>()
const emit = defineEmits(['update:filters', 'close'])

// Tree expansion state
const expandedPincode  = ref<string>('')
const expandedSociety  = ref<string>('')
const expandedCategory = ref<string>('')
const selectedSeller   = ref<string>('')

const sidebarData = createResource({
  url: 'my_frappe_app.api.get_customer_sidebar_data',
  auto: true,
  onSuccess(data: SidebarData) {
    if (data.pincode_list?.length > 0) {
      expandedPincode.value = data.pincode_list[0].value
    }
  }
})

const pincodeOptions  = computed(() => (sidebarData.data as SidebarData)?.pincode_list    || [])
const categoryOptions = computed(() => (sidebarData.data as SidebarData)?.all_categories  || [])

const societyOptions = computed(() => {
  const map = (sidebarData.data as SidebarData)?.pincode_map
  return map?.[expandedPincode.value]?.societies || []
})

const sellerOptions = computed(() => {
  const map = (sidebarData.data as SidebarData)?.pincode_map
  return map?.[expandedPincode.value]?.sellers || []
})

// ── Emit filters to parent ──
const emitFilters = (sellerId: string, catValue: string) => {
  selectedSeller.value = sellerId
  emit('update:filters', {
    pincode:  expandedPincode.value,
    society:  expandedSociety.value,
    category: catValue,
    seller:   sellerId,
    customer: (sidebarData.data as SidebarData)?.customer?.name || ''
  })
  if (window.innerWidth < 768) emit('close')
}

// ── Category click: toggle expand and emit if seller selected ──
const selectCategory = (catValue: string) => {
  expandedCategory.value = expandedCategory.value === catValue ? '' : catValue
  if (selectedSeller.value) {
    emitFilters(selectedSeller.value, expandedCategory.value)
  }
}

// ── Seller click: emit with current category ──
const selectSeller = (sellerId: string) => {
  emitFilters(sellerId, expandedCategory.value)
}

const resetSelection = () => {
  expandedSociety.value  = ''
  expandedCategory.value = ''
  selectedSeller.value   = ''
  emit('update:filters', {
    pincode: expandedPincode.value, society: '', category: '', seller: '',
    customer: (sidebarData.data as SidebarData)?.customer?.name || ''
  })
}
</script>

<template>
  <!-- Mobile overlay -->
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden"
    @click="emit('close')"
  />

  <div
    :class="[
      'flex flex-col bg-white w-72 h-full border-r border-gray-100 transition-transform duration-300 z-50',
      'fixed inset-y-0 left-0 md:sticky md:top-0',
      isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
    ]"
  >
    <!-- ─── HEADER ─── -->
    <div class="p-4 md:p-6 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
      <div class="flex items-center gap-3">
        <Avatar
          :label="(sidebarData.data as SidebarData)?.customer?.customer_name || 'C'"
          size="lg" shape="square" class="ring-2 ring-white shadow-sm"
        />
        <div class="overflow-hidden">
          <h3 class="font-black text-gray-900 truncate text-sm">
            {{ (sidebarData.data as SidebarData)?.customer?.customer_name || 'User' }}
          </h3>
          <p class="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Shopping Portal</p>
        </div>
      </div>
      <button @click="emit('close')" class="md:hidden p-2 text-gray-400 hover:text-gray-600">
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- ─── HOW TO USE HINT ─── -->
    <div v-if="!selectedSeller && !sidebarData.loading" class="mx-4 mt-3 bg-blue-50 border border-blue-100 rounded-xl px-3 py-2">
      <p class="text-[10px] text-blue-600 font-medium leading-relaxed">
        📍 Pincode → 🏢 Society → 📂 Category → 🏪 Seller
        <br/>select karo items dekhne ke liye
      </p>
    </div>

    <!-- ─── TREE NAV ─── -->
    <div class="flex-1 overflow-y-auto p-3 custom-scrollbar">
      <div v-if="sidebarData.loading" class="flex justify-center py-10">
        <LoadingIndicator />
      </div>

      <div v-else class="space-y-0.5">

        <!-- ── PINCODE LEVEL ── -->
        <div v-for="pin in pincodeOptions" :key="pin.value">
          <button
            @click="expandedPincode = expandedPincode === pin.value ? '' : pin.value"
            class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 transition-all text-sm font-bold"
            :class="expandedPincode === pin.value ? 'bg-gray-50 text-blue-600' : 'text-gray-700'"
          >
            <component :is="expandedPincode === pin.value ? ChevronDown : ChevronRight" class="w-4 h-4 flex-shrink-0" />
            <MapPin class="w-4 h-4 flex-shrink-0" />
            <span class="truncate">{{ pin.label }}</span>
          </button>

          <!-- ── SOCIETY LEVEL ── -->
          <div v-if="expandedPincode === pin.value" class="ml-3 pl-3 border-l-2 border-gray-100 space-y-0.5 my-0.5">

            <!-- No societies: skip to category directly -->
            <template v-if="societyOptions.length === 0">
              <!-- ── CATEGORY LEVEL (no society) ── -->
              <div v-for="cat in categoryOptions" :key="cat.value">
                <button
                  @click="selectCategory(cat.value)"
                  class="w-full text-left flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-50 text-xs font-semibold transition-all"
                  :class="expandedCategory === cat.value ? 'text-blue-600 bg-blue-50' : 'text-gray-500'"
                >
                  <component :is="expandedCategory === cat.value ? ChevronDown : ChevronRight" class="w-3.5 h-3.5 flex-shrink-0" />
                  <Layers class="w-3.5 h-3.5 flex-shrink-0" />
                  <span class="truncate">{{ cat.label }}</span>
                </button>

                <!-- ── SELLER LEVEL ── -->
                <div v-if="expandedCategory === cat.value" class="ml-3 pl-2 border-l-2 border-blue-100 space-y-0.5 my-0.5">
                  <button
                    v-for="sel in sellerOptions" :key="sel.value"
                    @click="selectSeller(sel.value)"
                    class="w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all font-semibold"
                    :class="selectedSeller === sel.value && expandedCategory === cat.value
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'hover:bg-gray-50 text-gray-500'"
                  >
                    <Store class="w-3.5 h-3.5 flex-shrink-0" />
                    <span class="truncate">{{ sel.label }}</span>
                  </button>
                  <p v-if="sellerOptions.length === 0" class="text-[10px] text-gray-400 px-3 py-1">
                    No sellers in this pincode
                  </p>
                </div>
              </div>
            </template>

            <!-- With societies -->
            <template v-else>
              <div v-for="soc in societyOptions" :key="soc.value">
                <button
                  @click="expandedSociety = expandedSociety === soc.value ? '' : soc.value"
                  class="w-full text-left flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-50 text-xs font-semibold transition-all"
                  :class="expandedSociety === soc.value ? 'bg-gray-50 text-gray-900' : 'text-gray-500'"
                >
                  <component :is="expandedSociety === soc.value ? ChevronDown : ChevronRight" class="w-3.5 h-3.5 flex-shrink-0" />
                  <Building class="w-3.5 h-3.5 flex-shrink-0" />
                  <span class="truncate">{{ soc.label }}</span>
                </button>

                <!-- ── CATEGORY LEVEL ── -->
                <div v-if="expandedSociety === soc.value" class="ml-3 pl-2 border-l-2 border-gray-100 space-y-0.5 my-0.5">
                  <div v-for="cat in categoryOptions" :key="cat.value">
                    <button
                      @click="selectCategory(cat.value)"
                      class="w-full text-left flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-50 text-[11px] font-semibold transition-all"
                      :class="expandedCategory === cat.value ? 'text-blue-600 bg-blue-50' : 'text-gray-400'"
                    >
                      <component :is="expandedCategory === cat.value ? ChevronDown : ChevronRight" class="w-3 h-3 flex-shrink-0" />
                      <Layers class="w-3.5 h-3.5 flex-shrink-0" />
                      <span class="truncate">{{ cat.label }}</span>
                    </button>

                    <!-- ── SELLER LEVEL ── -->
                    <div v-if="expandedCategory === cat.value" class="ml-3 pl-2 border-l-2 border-blue-100 space-y-0.5 my-0.5">
                      <button
                        v-for="sel in sellerOptions" :key="sel.value"
                        @click="selectSeller(sel.value)"
                        class="w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] transition-all font-semibold"
                        :class="selectedSeller === sel.value && expandedCategory === cat.value
                          ? 'bg-blue-600 text-white shadow-md'
                          : 'hover:bg-gray-50 text-gray-500'"
                      >
                        <Store class="w-3 h-3 flex-shrink-0" />
                        <span class="truncate">{{ sel.label }}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="pincodeOptions.length === 0" class="text-center py-10 text-gray-400">
          <MapPin class="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p class="text-xs">No pincode found for your account</p>
        </div>

      </div>
    </div>

    <!-- ─── FOOTER ─── -->
    <div class="p-4 border-t border-gray-100 bg-gray-50/30">
      <Button
        v-if="selectedSeller"
        variant="subtle" theme="gray"
        class="w-full flex justify-center"
        @click="resetSelection"
      >
        <template #prefix><FilterX class="w-4 h-4" /></template>
        Clear Filters
      </Button>
      <div v-else class="text-center">
        <p class="text-[10px] text-gray-400 font-medium">Customer App v2.0</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e5e7eb; border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #d1d5db; }
</style>
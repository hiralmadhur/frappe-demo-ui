<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  createResource,
  LoadingIndicator,
  Button
} from 'frappe-ui'
import {
  MapPin,
  Building,
  Layers,
  Users,
  FilterX,
  ChevronRight,
  ChevronDown,
  X
} from 'lucide-vue-next'

interface Option { label: string; value: string }
interface PincodeMapEntry {
  societies: Option[]
  customers: Option[]
}
interface SellerSidebarData {
  status: string
  seller: { name: string; company_name: string } | null
  pincode_list: Option[]
  pincode_map: Record<string, PincodeMapEntry>
  all_categories: Option[]
}

const props = defineProps<{
  isOpen?: boolean
  dialogOpen?: boolean    // NEW — when true, sidebar z-index drops below dialog
}>()
const emit = defineEmits(['update:filters', 'close'])

const expandedPincode  = ref<string>('')
const expandedSociety  = ref<string>('')
const expandedCategory = ref<string>('')
const selectedCustomer = ref<string>('')

const sidebarData = createResource({
  url: 'my_frappe_app.api.get_seller_sidebar_data',
  auto: true,
  onSuccess(data: SellerSidebarData) {
    if (data.pincode_list?.length > 0) {
      expandedPincode.value = data.pincode_list[0].value
    }
  }
})

const data            = computed(() => sidebarData.data as SellerSidebarData | null)
const pincodeOptions  = computed(() => data.value?.pincode_list || [])
const categoryOptions = computed(() => data.value?.all_categories || [])

const societyOptions  = computed(() =>
  data.value?.pincode_map?.[expandedPincode.value]?.societies || []
)
const customerOptions = computed(() =>
  data.value?.pincode_map?.[expandedPincode.value]?.customers || []
)

const togglePincode = (val: string) => {
  expandedPincode.value  = expandedPincode.value === val ? '' : val
  expandedSociety.value  = ''
  expandedCategory.value = ''
  selectedCustomer.value = ''
}
const toggleSociety = (val: string) => {
  expandedSociety.value  = expandedSociety.value === val ? '' : val
  expandedCategory.value = ''
  selectedCustomer.value = ''
}
const toggleCategory = (val: string) => {
  expandedCategory.value = expandedCategory.value === val ? '' : val
  selectedCustomer.value = ''
}

const selectCustomer = (customerId: string) => {
  selectedCustomer.value = customerId
  emit('update:filters', {
    pincode:  expandedPincode.value,
    society:  expandedSociety.value,
    category: expandedCategory.value,
    customer: customerId,
    seller:   data.value?.seller?.name || ''
  })
  if (window.innerWidth < 768) emit('close')
}

const resetSelection = () => {
  expandedSociety.value  = ''
  expandedCategory.value = ''
  selectedCustomer.value = ''
  emit('update:filters', {
    pincode:  expandedPincode.value,
    society:  '',
    category: '',
    customer: '',
    seller:   data.value?.seller?.name || ''
  })
}
</script>

<template>
  <!--
    Mobile overlay backdrop.
    Hidden when a dialog is open (dialog has its own backdrop at z-[9998])
    so we don't stack two dark overlays.
  -->
  <div
    v-if="isOpen && !dialogOpen"
    class="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden"
    @click="emit('close')"
  />

  <div
    :class="[
      'flex flex-col bg-white border-r border-gray-100 transition-transform duration-300',
      'fixed inset-y-0 left-0 md:sticky md:top-0',
      'w-[85vw] max-w-[300px] sm:w-72 h-full md:w-64 lg:w-72',
      /*
        z-index logic:
        - dialogOpen = true  → drop to z-[39] so dialog (z-9999) sits on top
        - dialogOpen = false → normal z-50
        On desktop (md+) sticky positioning means z-index rarely matters,
        but on mobile fixed sidebar MUST be below dialog backdrop.
      */
      dialogOpen ? 'z-[39]' : 'z-50',
      isOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0 md:shadow-none'
    ]"
  >
    <!-- ─── HEADER ─── -->
    <div class="p-3 sm:p-4 md:p-5 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
      <div class="flex items-center gap-2 sm:gap-3 min-w-0">
        <div
          class="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-gray-900 text-white flex items-center justify-center font-black text-sm shadow-sm flex-shrink-0"
        >
          {{ data?.seller?.company_name?.[0]?.toUpperCase() || 'S' }}
        </div>
        <div class="overflow-hidden min-w-0">
          <h3 class="font-black text-gray-900 truncate text-xs sm:text-sm">
            {{ data?.seller?.company_name || 'Seller' }}
          </h3>
          <p class="text-[9px] sm:text-[10px] text-gray-400 font-bold uppercase tracking-wider">
            Customer Explorer
          </p>
        </div>
      </div>
      <button
        @click="emit('close')"
        class="md:hidden p-1.5 sm:p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 flex-shrink-0"
      >
        <X class="w-4 h-4 sm:w-5 sm:h-5" />
      </button>
    </div>

    <!-- ─── TREE ─── -->
    <div class="flex-1 overflow-y-auto p-2 sm:p-3 custom-scrollbar">

      <div v-if="sidebarData.loading" class="flex justify-center py-10">
        <LoadingIndicator class="w-5 h-5 text-blue-500" />
      </div>

      <div v-else-if="pincodeOptions.length === 0"
        class="text-center py-10 text-gray-400 text-xs px-4">
        No pincodes found for this seller.
      </div>

      <!-- PINCODE LEVEL -->
      <div v-else class="space-y-1">
        <div v-for="pin in pincodeOptions" :key="pin.value" class="mb-1">

          <button
            @click="togglePincode(pin.value)"
            :class="[
              'w-full flex items-center gap-2 px-2.5 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all text-left',
              expandedPincode === pin.value
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-700 hover:bg-gray-50'
            ]"
          >
            <component :is="expandedPincode === pin.value ? ChevronDown : ChevronRight"
              class="w-3.5 h-3.5 sm:w-4 sm:h-4 flex-shrink-0" />
            <MapPin class="w-3.5 h-3.5 sm:w-4 sm:h-4 flex-shrink-0 text-blue-500" />
            <span class="truncate">{{ pin.label }}</span>
          </button>

          <!-- SOCIETY LEVEL -->
          <div v-if="expandedPincode === pin.value"
            class="ml-3 sm:ml-4 pl-2 sm:pl-3 border-l-2 border-gray-100 mt-1 space-y-1">

            <p v-if="societyOptions.length === 0"
              class="text-[10px] text-gray-400 px-2 py-1 italic">
              No societies in this pincode
            </p>

            <div v-for="soc in societyOptions" :key="soc.value">
              <button
                @click="toggleSociety(soc.value)"
                :class="[
                  'w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs font-medium transition-all text-left',
                  expandedSociety === soc.value
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-500 hover:bg-gray-50'
                ]"
              >
                <component :is="expandedSociety === soc.value ? ChevronDown : ChevronRight"
                  class="w-3 h-3 sm:w-3.5 sm:h-3.5 flex-shrink-0" />
                <Building class="w-3 h-3 sm:w-3.5 sm:h-3.5 flex-shrink-0 text-gray-400" />
                <span class="truncate text-[11px] sm:text-xs">{{ soc.label }}</span>
              </button>

              <!-- CATEGORY LEVEL -->
              <div v-if="expandedSociety === soc.value"
                class="ml-3 sm:ml-4 pl-2 sm:pl-3 border-l-2 border-gray-100 mt-1 space-y-1">

                <p v-if="categoryOptions.length === 0"
                  class="text-[10px] text-gray-400 px-2 py-1 italic">
                  No categories found
                </p>

                <div v-for="cat in categoryOptions" :key="cat.value">
                  <button
                    @click="toggleCategory(cat.value)"
                    :class="[
                      'w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-[11px] font-medium transition-all text-left',
                      expandedCategory === cat.value
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-400 hover:bg-gray-50'
                    ]"
                  >
                    <component :is="expandedCategory === cat.value ? ChevronDown : ChevronRight"
                      class="w-3 h-3 flex-shrink-0" />
                    <Layers class="w-3 h-3 sm:w-3.5 sm:h-3.5 flex-shrink-0" />
                    <span class="truncate">{{ cat.label }}</span>
                  </button>

                  <!-- CUSTOMER LEVEL -->
                  <div v-if="expandedCategory === cat.value"
                    class="ml-3 sm:ml-4 pl-2 border-l-2 border-gray-100 mt-1 space-y-1 pb-1">

                    <p v-if="customerOptions.length === 0"
                      class="text-[10px] text-gray-400 px-2 py-1 italic">
                      No customers in this pincode
                    </p>

                    <button
                      v-for="cus in customerOptions"
                      :key="cus.value"
                      @click="selectCustomer(cus.value)"
                      :class="[
                        'w-full flex items-center gap-2 px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-lg text-[11px] transition-all text-left',
                        selectedCustomer === cus.value
                          ? 'bg-blue-600 text-white font-bold shadow-sm'
                          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                      ]"
                    >
                      <Users class="w-3 h-3 flex-shrink-0" />
                      <span class="truncate">{{ cus.label }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ─── FOOTER ─── -->
    <div class="p-3 sm:p-4 border-t border-gray-100 bg-gray-50/30">
      <Button
        v-if="selectedCustomer"
        variant="subtle" theme="gray"
        class="w-full flex justify-center hover:text-red-600 text-xs sm:text-sm"
        @click="resetSelection"
      >
        <template #prefix>
          <FilterX class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </template>
        Clear Selection
      </Button>
      <p v-else class="text-center text-[9px] sm:text-[10px] text-gray-400 font-medium">
        Pincode → Society → Category → Customer
      </p>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #f3f4f6;
  border-radius: 10px;
}
</style>
<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { createResource, FormControl, LoadingIndicator, Avatar, Button } from 'frappe-ui'
import { 
  MapPin, 
  Building, 
  Layers, 
  Users, 
  FilterX, 
  Store 
} from 'lucide-vue-next'

const emit = defineEmits(['update:filters'])

// --- STATE ---
const selectedPincode = ref('')
const selectedSociety = ref('')
const selectedCategory = ref('')
const selectedCustomer = ref('')

// --- RESOURCES ---

// 1. Seller Context (Company Name & Pincodes)
const context = createResource({
  url: 'my_frappe_app.api.get_seller_context',
  auto: true
})

// 2. Filter Options (Societies & Customers based on Pincode)
const options = createResource({
  url: 'my_frappe_app.api.get_filtered_options',
  makeParams() { return { pincode: selectedPincode.value } }
})

// 3. Item Categories
const categories = createResource({
  url: 'frappe.client.get_list',
  params: { 
    doctype: 'Item Group', 
    fields: ['name as value', 'item_group_name as label'],
    filters: { is_group: 0 } // Optional: Only show leaf groups
  },
  auto: true
})

// --- WATCHERS ---

// Pincode change par Society/Category/Customer reset karein
watch(selectedPincode, (val) => {
  if (val) {
    options.fetch()
    selectedSociety.value = ''
    selectedCategory.value = ''
    selectedCustomer.value = ''
  }
})

// Customer select hone par Parent ko emit karein
watch(selectedCustomer, (val) => {
  emit('update:filters', { customer: val })
})

// --- ACTIONS ---
const resetFilters = () => {
  selectedPincode.value = ''
  selectedSociety.value = ''
  selectedCategory.value = ''
  selectedCustomer.value = ''
  emit('update:filters', { customer: '' })
}

// Helper for Options Formatting
const pincodeOptions = computed(() => context.data?.pincodes || [])
const societyOptions = computed(() => options.data?.societies || [])
const customerOptions = computed(() => options.data?.customers || [])
const categoryOptions = computed(() => categories.data || [])

</script>

<template>
  <div class="flex flex-col h-screen bg-white border-r border-gray-100 w-72 flex-shrink-0 sticky top-0">
    
    <div class="p-6 border-b border-gray-100 bg-gray-50/50">
      <div class="flex items-center gap-3">
        <Avatar 
          :label="context.data?.company?.company_name || 'S'" 
          size="lg" 
          shape="square"
          image="" 
          class="ring-2 ring-white shadow-sm"
        />
        <div class="overflow-hidden">
          <h3 class="font-black text-gray-900 truncate text-sm">
            {{ context.data?.company?.company_name || 'Seller Portal' }}
          </h3>
          <p class="text-xs text-gray-500 font-medium truncate">Dashboard</p>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-5 space-y-8 custom-scrollbar">
      
      <div v-if="context.loading" class="flex justify-center py-4">
        <LoadingIndicator />
      </div>

      <div v-else>
        <div class="space-y-4">
          <div class="flex items-center gap-2 text-gray-400 mb-2">
            <MapPin class="w-3 h-3" />
            <span class="text-[10px] font-bold uppercase tracking-widest">Location</span>
          </div>

          <FormControl
            type="select"
            v-model="selectedPincode"
            :options="pincodeOptions"
            placeholder="Select Pincode"
            variant="subtle"
            size="sm"
          />

          <FormControl
            type="select"
            v-model="selectedSociety"
            :options="societyOptions"
            :disabled="!selectedPincode"
            placeholder="Select Society"
            variant="subtle"
            size="sm"
          >
             <template #prefix><Building class="w-4 h-4 text-gray-400"/></template>
          </FormControl>
        </div>

        <div class="h-px bg-gray-100 my-6"></div>

        <div class="space-y-4">
          <div class="flex items-center gap-2 text-gray-400 mb-2">
            <FilterX class="w-3 h-3" />
            <span class="text-[10px] font-bold uppercase tracking-widest">Filtering</span>
          </div>

          <FormControl
            type="select"
            v-model="selectedCategory"
            :options="categoryOptions"
            :disabled="!selectedSociety"
            placeholder="Item Category"
            variant="subtle"
            size="sm"
          >
            <template #prefix><Layers class="w-4 h-4 text-gray-400"/></template>
          </FormControl>

          <div :class="{'opacity-50': !selectedCategory}">
             <label class="text-xs font-medium text-gray-600 mb-1.5 block">Customer</label>
             <FormControl
               type="select"
               v-model="selectedCustomer"
               :options="customerOptions"
               :disabled="!selectedCategory"
               placeholder="Select Customer"
               variant="outline"
               size="md"
             >
                <template #prefix><Users class="w-4 h-4 text-gray-500"/></template>
             </FormControl>
          </div>
        </div>

        <div v-if="options.loading" class="mt-4 p-3 bg-blue-50 rounded-lg flex items-center gap-2 text-blue-600 text-xs font-medium animate-pulse">
           <LoadingIndicator size="sm" />
           <span>Fetching data...</span>
        </div>
      </div>
    </div>

    <div class="p-4 border-t border-gray-100 bg-gray-50/30">
      <Button 
        v-if="selectedPincode || selectedCustomer"
        variant="subtle" 
        theme="gray" 
        class="w-full justify-center text-gray-500 hover:text-red-500 hover:bg-red-50"
        @click="resetFilters"
      >
        <template #prefix><FilterX class="w-4 h-4" /></template>
        Reset Filters
      </Button>
      
      <div v-else class="text-center">
         <p class="text-[10px] text-gray-300 font-medium">v1.0.0 • Seller App</p>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Optional: Custom scrollbar for webkit browsers to make it look cleaner */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #f3f4f6;
  border-radius: 20px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
}
</style>
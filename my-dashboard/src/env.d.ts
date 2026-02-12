/// <reference types="vite/client" />

interface Window {
  frappe: any;
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
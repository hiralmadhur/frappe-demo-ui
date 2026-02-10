import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import frappeui from 'frappe-ui/vite';
import Icons from 'unplugin-icons/vite';

export default defineConfig({
  plugins: [
    vue(),
    frappeui({
      source: 'src/main.ts',
    }),
    Icons({
      compiler: 'vue3',
      autoInstall: true
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    include: [
      'frappe-ui > feather-icons',
      'showdown',
      'engine.io-client',
      'interactjs', // <--- Ye wo white screen/console error fix karega
    ],
  },
});
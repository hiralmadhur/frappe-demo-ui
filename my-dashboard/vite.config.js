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
  build: {
    // Ye line files ko Frappe ke public folder mein bhejegi
    outDir: path.resolve(__dirname, '../my_frappe_app/public/dashboard'),
    emptyOutDir: true,
    target: 'es2015',
    rollupOptions: {
      output: {
        // Isse hashed names (index-BtbXTCZ.js) nahi banenge
        entryFileNames: `[name].js`,
        chunkFileNames: `[name].js`,
        assetFileNames: `[name].[ext]`
      }
    }
  },
  optimizeDeps: {
    include: [
      'debug',
      "frappe-ui > feather-icons",
      "showdown",
      "engine.io-client",
      "interactjs",
      "highlight.js/lib/core",
    ],
  },
});
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
  // 👇 Ye server block add karein
  server: {
    port: 5173,
    proxy: {
      '^/(app|api|login|logout|assets|files)': {
        target: 'http://127.0.0.1:8000', // Aapka Frappe port (default 8000)
        changeOrigin: true,
        secure: false,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../my_frappe_app/public/frontend'),
    emptyOutDir: true,
    target: 'es2015',
    rollupOptions: {
      output: {
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
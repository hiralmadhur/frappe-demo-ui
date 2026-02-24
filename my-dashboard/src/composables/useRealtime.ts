import { onUnmounted } from 'vue'

interface RealtimeOptions {
  onOrderUpdate?: () => void
  onSubscriptionUpdate?: () => void
  onNotification?: (msg: string) => void
}

export function useCustomerRealtime(
  customerEmail: string,
  options: RealtimeOptions
) {
  const frappe = (window as any).frappe

  if (!frappe?.realtime) {
    console.warn('[Realtime] Frappe realtime not available')
    return { disconnect: () => {} }
  }

  // Order update event
  const handleOrderUpdate = (data: any) => {
    if (!data?.customer || data.customer === customerEmail) {
      options.onOrderUpdate?.()
    }
  }

  // Subscription update event
  const handleSubscriptionUpdate = (data: any) => {
    if (!data?.customer || data.customer === customerEmail) {
      options.onSubscriptionUpdate?.()
    }
  }

  // Frappe's built-in msgprint (already used in _notify_customer_subscription)
  const handleMsgprint = (data: any) => {
    if (typeof data === 'string') {
      options.onNotification?.(data)
    }
    // Yeh event aane par orders aur subs refresh karo
    options.onOrderUpdate?.()
    options.onSubscriptionUpdate?.()
  }

  // Subscribe
  frappe.realtime.on('order_update', handleOrderUpdate)
  frappe.realtime.on('subscription_update', handleSubscriptionUpdate)
  frappe.realtime.on('msgprint', handleMsgprint)

  console.log('[Realtime] Connected for:', customerEmail)

  // Disconnect function
  const disconnect = () => {
    frappe.realtime.off('order_update', handleOrderUpdate)
    frappe.realtime.off('subscription_update', handleSubscriptionUpdate)
    frappe.realtime.off('msgprint', handleMsgprint)
    console.log('[Realtime] Disconnected')
  }

  // Auto cleanup on component unmount
  onUnmounted(disconnect)

  return { disconnect }
}
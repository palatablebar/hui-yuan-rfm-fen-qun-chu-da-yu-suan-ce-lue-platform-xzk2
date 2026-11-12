import { ref } from 'vue'

export interface ToastState {
  message: string
  tone: 'info' | 'warn' | 'danger'
}

export function useToast(timeout = 4200) {
  const toast = ref<ToastState | null>(null)
  let timer: number | null = null

  function show(message: string, tone: ToastState['tone'] = 'info') {
    toast.value = { message, tone }
    if (timer !== null) window.clearTimeout(timer)
    timer = window.setTimeout(() => {
      toast.value = null
      timer = null
    }, timeout)
  }

  function clear() {
    if (timer !== null) window.clearTimeout(timer)
    timer = null
    toast.value = null
  }

  return { toast, show, clear }
}

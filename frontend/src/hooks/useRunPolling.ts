import { onBeforeUnmount, watch } from 'vue'
import { useSegmentStore } from '../stores/segmentStore'
import { TERMINAL_STATUSES } from '../constants/segmentStatus'

/** 分群批次未完成时轮询详情；完成/失败/卸载自动停止。 */
export function useRunPolling(runId: () => number | null, intervalMs = 1200) {
  const store = useSegmentStore()
  let timer: number | null = null

  function stop() {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  function tick() {
    const id = runId()
    if (!id) {
      stop()
      return
    }
    const run = store.current
    if (!run || run.id !== id || TERMINAL_STATUSES.includes(run.status)) {
      stop()
      return
    }
    store.loadRun(id).catch(() => stop())
  }

  function start() {
    stop()
    timer = window.setInterval(tick, intervalMs)
  }

  watch(
    () => [runId(), store.current?.status] as const,
    () => {
      const id = runId()
      const run = store.current
      if (id && run && !TERMINAL_STATUSES.includes(run.status)) start()
      else stop()
    },
    { immediate: true },
  )

  onBeforeUnmount(stop)
  return { start, stop }
}

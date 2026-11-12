<template>
  <label class="run-selector">
    <span class="eyebrow">分群批次</span>
    <select
      class="select"
      :value="modelValue ?? ''"
      :disabled="disabled"
      @change="onChange"
    >
      <option v-if="!runs.length" value="">暂无批次</option>
      <option v-for="run in runs" :key="run.id" :value="run.id">
        {{ run.run_no }} · {{ statusLabel(run.status) }} · k={{ run.selected_k ?? run.k_requested }}
      </option>
    </select>
  </label>
</template>

<script setup lang="ts">
import { SEGMENT_STATUS_META } from '../../constants/segmentStatus'
import type { RunSummary } from '../../types/segment'

withDefaults(
  defineProps<{
    runs: RunSummary[]
    modelValue: number | null
    disabled?: boolean
  }>(),
  { disabled: false },
)

const emit = defineEmits<{ 'update:modelValue': [value: number] }>()

function statusLabel(status: RunSummary['status']): string {
  return SEGMENT_STATUS_META[status]?.label ?? status
}

function onChange(event: Event) {
  const value = Number((event.target as HTMLSelectElement).value)
  if (Number.isFinite(value) && value > 0) emit('update:modelValue', value)
}
</script>

<style scoped>
.run-selector {
  display: flex;
  align-items: center;
  gap: 10px;
}
.run-selector .select {
  min-width: 280px;
}
</style>

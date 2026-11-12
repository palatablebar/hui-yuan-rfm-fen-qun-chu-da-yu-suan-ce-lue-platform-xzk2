<template>
  <div class="notice" role="alert">
    <span class="eyebrow" style="color: var(--danger)">error</span>
    <span>{{ message }}</span>
    <button v-if="retryable" class="btn btn-sm" type="button" @click="$emit('retry')">
      {{ retryLabel }}
    </button>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    message: string
    retryable?: boolean
    retryLabel?: string
  }>(),
  { retryable: true, retryLabel: '重试' },
)
defineEmits<{ retry: [] }>()
</script>

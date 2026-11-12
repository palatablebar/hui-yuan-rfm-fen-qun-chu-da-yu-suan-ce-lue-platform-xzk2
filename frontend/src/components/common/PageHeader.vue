<template>
  <header class="page-head">
    <div class="page-head-main">
      <div class="eyebrow">{{ eyebrow }}</div>
      <h1>{{ title }}</h1>
      <p v-if="lede" class="lede">{{ lede }}</p>
    </div>
    <div class="page-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    eyebrow: string
    title: string
    lede?: string
  }>(),
  { lede: '' },
)
</script>

<template>
  <div class="empty-state">
    <span class="eyebrow">stratum missing</span>
    <h3>{{ title }}</h3>
    <p>{{ text }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; text: string }>()
</script>

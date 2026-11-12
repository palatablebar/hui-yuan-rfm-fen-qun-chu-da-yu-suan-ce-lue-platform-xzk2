<template>
  <section class="panel">
    <header class="panel-head">
      <span class="eyebrow">{{ eyebrow }}</span>
      <div class="panel-meta">
        <slot name="meta" />
      </div>
    </header>
    <div class="panel-body" :class="{ tight }">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    eyebrow: string
    tight?: boolean
  }>(),
  { tight: false },
)
</script>

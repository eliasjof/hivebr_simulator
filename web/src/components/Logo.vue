<script setup>
defineProps({ size: { type: Number, default: 22 } })
</script>
<template>
  <svg :width="size" :height="size" viewBox="0 0 32 32" aria-hidden="true">
    <path d="M16 2l11.4 6.5v13L16 28 4.6 21.5v-13z" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" />
    <path d="M16 9l5.2 3v6L16 21l-5.2-3v-6z" fill="var(--accent)" />
  </svg>
</template>

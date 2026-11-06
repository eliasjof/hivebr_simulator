<script setup>
import FloatingWindow from './FloatingWindow.vue'
import RobotsPanel from './RobotsPanel.vue'
</script>
<template>
  <FloatingWindow id="robots" :min-w="260" :min-h="200"><RobotsPanel /></FloatingWindow>
</template>

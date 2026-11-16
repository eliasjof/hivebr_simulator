<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import { store } from '../state/store.js'
import { t } from '../i18n/index.js'
import { student } from '../learning/identity.js'

const name = computed(() => student.name || '')
const group = computed(() => student.group || '')
const label = computed(() => name.value || t('student.chip_empty'))
const tip = computed(() => t('student.chip_tip', { id: student.id || '—' }))
</script>
<template>
  <button class="chip" :class="{ empty: !name }" :title="tip" aria-haspopup="dialog" @click="store.modals.profile = true">
    <Icon name="user" :size="13" />
    <b>{{ label }}</b>
    <span v-if="group" class="grp">· {{ group }}</span>
  </button>
</template>
<style scoped>
.chip {
  display: inline-flex; align-items: center; gap: var(--sp-2); max-width: 260px; height: var(--h-md);
  padding: 0 10px; border: 1px solid var(--topbar-hover); border-radius: var(--radius-pill);
  background: none; color: var(--topbar-text); font-size: var(--fs-xs); white-space: nowrap;
}
.chip:hover { background: var(--topbar-hover); }
.chip.empty { color: var(--topbar-muted); border-style: dashed; }
.chip b { font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
.grp { color: var(--topbar-muted); overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 900px) { .chip .grp { display: none; } }
</style>

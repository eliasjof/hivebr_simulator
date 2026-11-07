<script setup>
import { ref, computed, watch } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import { store, catalog, loadExample, runDemo } from '../state/store.js'
import { t, locale } from '../i18n/index.js'

const q = ref('')
const tag = ref(null)
watch(locale, () => { tag.value = null })
const tags = computed(() => [...new Set(catalog.value.flatMap((e) => e.tags || []))].sort((a, b) => a.localeCompare(b, locale.value)))
const list = computed(() => {
  const s = q.value.trim().toLowerCase()
  return catalog.value.filter((e) => (!tag.value || (e.tags || []).includes(tag.value))
    && (!s || `${e.title} ${e.description} ${(e.tags || []).join(' ')}`.toLowerCase().includes(s)))
})
async function demo() { store.modals.examples = false; runDemo() }
</script>
<template>
  <Modal :title="t('examples.title')" :width="860" @close="store.modals.examples = false">
    <div class="bar">
      <div class="search"><Icon name="search" :size="14" /><input v-model="q" class="input" type="search" :placeholder="t('examples.search')" :aria-label="t('examples.search_aria')" data-autofocus /></div>
      <div class="tags" role="group" :aria-label="t('examples.filter')">
        <button class="tagb" :class="{ on: !tag }" @click="tag = null">{{ t('examples.all') }}</button>
        <button v-for="tg in tags" :key="tg" class="tagb" :class="{ on: tag === tg }" :aria-pressed="tag === tg" @click="tag = tag === tg ? null : tg">{{ tg }}</button>
      </div>
    </div>
    <div class="grid">
      <article v-for="e in list" :key="e.id" class="card">
        <h3>{{ e.title }}</h3>
        <p>{{ e.description }}</p>
        <div class="meta"><span v-for="tg in e.tags || []" :key="tg" class="tag">{{ tg }}</span><span v-if="e.robots" class="tag mono">{{ e.robots }}</span></div>
        <p v-if="e.notes" class="notes">{{ e.notes }}</p>
        <div class="act">
          <button class="btn primary sm" @click="loadExample(e)">{{ t('examples.load') }}</button>
          <button v-if="e.id === 'demonstracao'" class="btn sm" @click="demo"><Icon name="demo" :size="13" />{{ t('examples.run_demo') }}</button>
        </div>
      </article>
      <p v-if="!list.length" class="muted">{{ t('examples.none') }}</p>
    </div>
  </Modal>
</template>
<style scoped>
.bar { display: flex; flex-direction: column; gap: var(--sp-4); margin-bottom: var(--sp-5); }
.search { position: relative; } .search svg { position: absolute; left: var(--sp-4); top: 7px; color: var(--text-muted); } .search .input { padding-left: 28px; }
.tags { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.tagb { border: 1px solid var(--border); background: var(--surface); border-radius: var(--radius-pill); padding: var(--sp-1) 10px; font-size: var(--fs-sm); color: var(--text-muted); }
.tagb:hover { background: var(--surface-3); } .tagb.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.card { border: 1px solid var(--border); border-radius: var(--radius); padding: var(--sp-5); display: flex; flex-direction: column; gap: var(--sp-4); background: var(--surface-2); min-width: 0; }
.card h3 { font-size: var(--fs-md); } .card p { margin: 0; color: var(--text-muted); line-height: 1.45; font-size: var(--fs-sm); }
.meta { display: flex; flex-wrap: wrap; gap: var(--sp-2); } .notes { font-size: var(--fs-xs) !important; }
.act { margin-top: auto; display: flex; gap: var(--sp-3); flex-wrap: wrap; }
</style>

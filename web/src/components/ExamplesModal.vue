<script setup>
import { ref, computed, watch } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import { store, catalog, loadExample, runDemo } from '../state/store.js'
import { CATEGORY_IDS, LEVEL_IDS } from '../examples/catalog.js'
import { t, locale } from '../i18n/index.js'

const q = ref('')
const tag = ref(null)
const category = ref(null)
const level = ref(null)
watch(locale, () => { tag.value = null })

const CATEGORY_KEY = {
  fundamentos: 'examples.category.fundamentos',
  percepcao: 'examples.category.percepcao',
  linha: 'examples.category.linha',
  locomocao: 'examples.category.locomocao',
  controle: 'examples.category.controle',
  multirobo: 'examples.category.multirobo',
}
function categoryLabel(id) {
  return CATEGORY_KEY[id] ? t(CATEGORY_KEY[id]) : t('examples.category.outros')
}

const categories = computed(() => CATEGORY_IDS.filter((id) => catalog.value.some((e) => e.category === id)))
const levels = computed(() => LEVEL_IDS.filter((n) => catalog.value.some((e) => e.level === n)))
const tags = computed(() => [...new Set(catalog.value.flatMap((e) => e.tags || []))].sort((a, b) => a.localeCompare(b, locale.value)))

const list = computed(() => {
  const s = q.value.trim().toLowerCase()
  return catalog.value.filter((e) => {
    if (tag.value && !(e.tags || []).includes(tag.value)) return false
    if (category.value && e.category !== category.value) return false
    if (level.value && e.level !== level.value) return false
    if (!s) return true
    const haystack = `${e.title} ${e.description} ${(e.tags || []).join(' ')} ${categoryLabel(e.category)}`
    return haystack.toLowerCase().includes(s)
  })
})

const groups = computed(() => {
  const out = []
  for (const id of CATEGORY_IDS) {
    const items = list.value
      .filter((e) => e.category === id)
      .sort((a, b) => (a.level - b.level) || (a.order - b.order) || a.title.localeCompare(b.title, locale.value))
    if (items.length) out.push({ id, items })
  }
  const rest = list.value.filter((e) => !CATEGORY_IDS.includes(e.category))
  if (rest.length) out.push({ id: 'outros', items: rest })
  return out
})

async function demo() { store.modals.examples = false; runDemo() }
</script>
<template>
  <Modal :title="t('examples.title')" :width="900" @close="store.modals.examples = false">
    <div class="bar">
      <div class="search"><Icon name="search" :size="14" /><input v-model="q" class="input" type="search" :placeholder="t('examples.search')" :aria-label="t('examples.search_aria')" data-autofocus /></div>
      <div class="filters" role="group" :aria-label="t('examples.category')">
        <span class="filter-label">{{ t('examples.category') }}</span>
        <button class="tagb" :class="{ on: !category }" :aria-pressed="!category" @click="category = null">{{ t('examples.category.all') }}</button>
        <button v-for="c in categories" :key="c" class="tagb" :class="{ on: category === c }" :aria-pressed="category === c" @click="category = category === c ? null : c">{{ categoryLabel(c) }}</button>
      </div>
      <div class="filters" role="group" :aria-label="t('examples.level')">
        <span class="filter-label">{{ t('examples.level') }}</span>
        <button class="tagb" :class="{ on: !level }" :aria-pressed="!level" @click="level = null">{{ t('examples.level.all') }}</button>
        <button v-for="n in levels" :key="n" class="tagb" :class="{ on: level === n }" :aria-pressed="level === n" @click="level = level === n ? null : n">{{ t('examples.level.n', { n }) }}</button>
      </div>
      <div class="filters" role="group" :aria-label="t('examples.filter')">
        <span class="filter-label">{{ t('examples.filter') }}</span>
        <button class="tagb" :class="{ on: !tag }" :aria-pressed="!tag" @click="tag = null">{{ t('examples.all') }}</button>
        <button v-for="tg in tags" :key="tg" class="tagb" :class="{ on: tag === tg }" :aria-pressed="tag === tg" @click="tag = tag === tg ? null : tg">{{ tg }}</button>
      </div>
    </div>
    <div class="groups">
      <section v-for="g in groups" :key="g.id" class="group">
        <h3 class="group-h">{{ categoryLabel(g.id) }} <span class="count">{{ g.items.length }}</span></h3>
        <div class="grid">
          <article v-for="e in g.items" :key="e.id" class="card">
            <h3>{{ e.title }}</h3>
            <p>{{ e.description }}</p>
            <div class="meta">
              <span class="tag lvl">{{ t('examples.level.n', { n: e.level }) }}</span>
              <span v-for="tg in e.tags || []" :key="tg" class="tag">{{ tg }}</span>
              <span v-if="e.robots" class="tag mono">{{ e.robots }}</span>
            </div>
            <p v-if="e.notes" class="notes">{{ e.notes }}</p>
            <div class="act">
              <button class="btn primary sm" @click="loadExample(e)">{{ t('examples.load') }}</button>
              <button v-if="e.id === 'demonstracao'" class="btn sm" @click="demo"><Icon name="demo" :size="13" />{{ t('examples.run_demo') }}</button>
            </div>
          </article>
        </div>
      </section>
      <p v-if="!list.length" class="muted">{{ t('examples.none') }}</p>
    </div>
  </Modal>
</template>
<style scoped>
.bar { display: flex; flex-direction: column; gap: var(--sp-3); margin-bottom: var(--sp-5); }
.search { position: relative; }
.search svg { position: absolute; left: var(--sp-4); top: 7px; color: var(--text-muted); }
.search .input { padding-left: 28px; }
.filters { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-2); }
.filter-label { min-width: 82px; font-size: var(--fs-sm); color: var(--text-muted); }
.tagb { border: 1px solid var(--border); background: var(--surface); border-radius: var(--radius-pill); padding: var(--sp-1) 10px; font-size: var(--fs-sm); color: var(--text-muted); }
.tagb:hover { background: var(--surface-3); }
.tagb.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.groups { display: flex; flex-direction: column; gap: var(--sp-6); }
.group-h { display: flex; align-items: center; gap: var(--sp-3); margin: 0 0 var(--sp-4); font-size: var(--fs-md); }
.group-h .count { display: inline-grid; place-items: center; min-width: 22px; height: 22px; padding: 0 6px; border-radius: var(--radius-pill); background: var(--surface-3); color: var(--text-muted); font-size: var(--fs-xs); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.card { border: 1px solid var(--border); border-radius: var(--radius); padding: var(--sp-5); display: flex; flex-direction: column; gap: var(--sp-4); background: var(--surface-2); min-width: 0; }
.card h3 { font-size: var(--fs-md); }
.card p { margin: 0; color: var(--text-muted); line-height: 1.45; font-size: var(--fs-sm); }
.meta { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.tag.lvl { border-color: var(--accent); color: var(--accent); }
.notes { font-size: var(--fs-xs) !important; }
.act { margin-top: auto; display: flex; gap: var(--sp-3); flex-wrap: wrap; }
</style>

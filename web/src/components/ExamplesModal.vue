<script setup>
import { ref, computed } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import { store, CATALOGREF, loadExample, runDemo } from '../state/store.js'

const q = ref('')
const tag = ref(null)
const tags = computed(() => [...new Set(CATALOGREF.flatMap((e) => e.tags || []))].sort())
const list = computed(() => {
  const s = q.value.trim().toLowerCase()
  return CATALOGREF.filter((e) => (!tag.value || (e.tags || []).includes(tag.value))
    && (!s || `${e.title} ${e.description} ${(e.tags || []).join(' ')}`.toLowerCase().includes(s)))
})
async function demo() { store.modals.examples = false; runDemo() }
</script>
<template>
  <Modal title="Exemplos" :width="860" @close="store.modals.examples = false">
    <div class="bar">
      <div class="search"><Icon name="search" :size="14" /><input class="input" v-model="q" type="search" placeholder="Buscar exemplos…" aria-label="Buscar exemplos" data-autofocus /></div>
      <div class="tags" role="group" aria-label="Filtrar por etiqueta">
        <button class="tagb" :class="{ on: !tag }" @click="tag = null">Todos</button>
        <button v-for="t in tags" :key="t" class="tagb" :class="{ on: tag === t }" :aria-pressed="tag === t" @click="tag = tag === t ? null : t">{{ t }}</button>
      </div>
    </div>
    <div class="grid">
      <article v-for="e in list" :key="e.id" class="card">
        <h3>{{ e.title }}</h3>
        <p>{{ e.description }}</p>
        <div class="meta"><span v-for="t in e.tags || []" :key="t" class="tag">{{ t }}</span><span v-if="e.robots" class="tag mono">{{ typeof e.robots === 'number' ? `${e.robots} ${e.robots === 1 ? 'robô' : 'robôs'}` : e.robots }}</span></div>
        <p v-if="e.notes" class="notes faint">{{ e.notes }}</p>
        <div class="act">
          <button class="btn primary sm" @click="loadExample(e)">Carregar no editor</button>
          <button v-if="e.id === 'demonstracao'" class="btn sm" @click="demo"><Icon name="demo" :size="13" />Executar demonstração</button>
        </div>
      </article>
      <p v-if="!list.length" class="faint">Nenhum exemplo encontrado.</p>
    </div>
  </Modal>
</template>
<style scoped>
.bar { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.search { position: relative; } .search svg { position: absolute; left: 8px; top: 7px; color: var(--text-faint); } .search .input { padding-left: 28px; }
.tags { display: flex; flex-wrap: wrap; gap: 4px; }
.tagb { border: 1px solid var(--border); background: var(--surface); border-radius: 99px; padding: 2px 10px; font-size: 12px; color: var(--text-muted); }
.tagb:hover { background: var(--surface-3); } .tagb.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.card { border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; display: flex; flex-direction: column; gap: 8px; background: var(--surface-2); }
.card h3 { font-size: 14px; } .card p { margin: 0; color: var(--text-muted); line-height: 1.45; font-size: 12.5px; }
.meta { display: flex; flex-wrap: wrap; gap: 4px; } .notes { font-size: 11.5px !important; }
.act { margin-top: auto; display: flex; gap: 6px; flex-wrap: wrap; }
</style>

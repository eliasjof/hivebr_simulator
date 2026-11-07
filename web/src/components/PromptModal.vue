<script setup>
import { reactive } from 'vue'
import Modal from './Modal.vue'
import { store, resolvePrompt } from '../state/store.js'
import { t } from '../i18n/index.js'

const cfg = store.prompt.cfg
const values = reactive(Object.fromEntries((cfg.fields || []).map((f) => [f.key, f.value])))
function ok() {
  const out = {}
  for (const f of cfg.fields || []) {
    let v = values[f.key]
    if (f.type === 'number') {
      v = Number(String(v).replace(',', '.'))
      if (!Number.isFinite(v)) return
      if (f.min != null) v = Math.max(f.min, v)
      if (f.max != null) v = Math.min(f.max, v)
    }
    out[f.key] = v
  }
  resolvePrompt(cfg.fields?.length ? out : true)
}
function cancel() { resolvePrompt(null) }
</script>
<template>
  <Modal :title="cfg.title" :width="cfg.width || 420" @close="cancel">
    <form @submit.prevent="ok">
      <p v-if="cfg.message" class="msg">{{ cfg.message }}</p>
      <div v-for="(f, i) in cfg.fields || []" :key="f.key" class="field">
        <label :for="'pf-' + f.key">{{ f.label }}<span v-if="f.suffix" class="faint"> ({{ f.suffix }})</span></label>
        <input :id="'pf-' + f.key" class="input mono" :type="f.type === 'number' ? 'number' : 'text'" v-model="values[f.key]"
          :min="f.min" :max="f.max" :step="f.step" :data-autofocus="i === 0 ? '' : null" @focus="$event.target.select?.()" />
        <small v-if="f.hint" class="faint">{{ f.hint }}</small>
      </div>
      <button type="submit" hidden />
    </form>
    <template #footer>
      <button class="btn" @click="cancel">{{ cfg.cancelText || t('common.cancel') }}</button>
      <button class="btn" :class="cfg.danger ? 'danger solid' : 'primary'" :data-autofocus="cfg.fields?.length ? null : ''" @click="ok">{{ cfg.confirmText || t('common.ok') }}</button>
    </template>
  </Modal>
</template>
<style scoped>
.msg { margin: 0 0 var(--sp-5); color: var(--text-muted); line-height: 1.5; }
.field { margin-bottom: var(--sp-4); }
</style>

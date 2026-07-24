import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ConnectionForm.vue', import.meta.url), 'utf8')

test('model field uses a searchable selector that accepts custom model ids', () => {
  assert.match(source, /<el-select[\s\S]*?filterable[\s\S]*?allow-create[\s\S]*?default-first-option/)
  assert.match(source, /v-model="profile\.model"/)
  assert.match(source, /@change="\$emit\('validate', 'model'\)"/)
  assert.doesNotMatch(source, /<datalist|list="llm-model-options"/)
})

test('model selector renders provider metadata and a constrained popup', () => {
  assert.match(source, /<el-option[\s\S]*?v-for="model in modelOptions"/)
  assert.match(source, /model\.owned_by/)
  assert.match(source, /popper-class="model-select-popper"/)
  assert.match(source, /model-select-popper[\s\S]*?max-height:\s*280px/)
  assert.match(source, /暂无可选模型，可直接输入模型名称/)
})

test('model input row stacks on narrow screens', () => {
  assert.match(source, /@media \(max-width:\s*600px\)[\s\S]*?\.model-input-row[\s\S]*?flex-direction:\s*column/)
  assert.match(source, /\.model-input-row \.btn[\s\S]*?min-height:\s*44px/)
  assert.match(source, /\.btn:focus-visible[\s\S]*?outline:/)
})

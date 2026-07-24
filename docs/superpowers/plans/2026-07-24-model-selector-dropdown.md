# Model Selector Dropdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the browser-native model `datalist` with a compact, searchable Element Plus selector that still accepts arbitrary model IDs.

**Architecture:** Keep `profile.model` and the existing refresh data flow unchanged. Limit the implementation to `ConnectionForm.vue`, using Element Plus' teleported select popup with a dedicated `popper-class`; protect the interaction contract with the repository's existing Node source-structure test pattern.

**Tech Stack:** Vue 3, TypeScript, Element Plus 2.13, scoped CSS, Node.js built-in test runner, Vite.

---

## File Structure

- Create `frontend/src/views/ai/model-config/components/connectionForm.test.mjs`: regression assertions for selector capabilities, option metadata, popup sizing hooks, validation events, and removal of the native datalist.
- Modify `frontend/src/views/ai/model-config/components/ConnectionForm.vue`: render the searchable/createable selector, model options, empty state, validation event, responsive layout, and popup styles.

### Task 1: Add the model selector regression test

**Files:**
- Create: `frontend/src/views/ai/model-config/components/connectionForm.test.mjs`
- Test: `frontend/src/views/ai/model-config/components/connectionForm.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ConnectionForm.vue', import.meta.url), 'utf8')

test('model field uses a searchable selector that accepts custom model ids', () => {
  assert.match(source, /<el-select[\\s\\S]*?filterable[\\s\\S]*?allow-create[\\s\\S]*?default-first-option/)
  assert.match(source, /v-model="profile\.model"/)
  assert.match(source, /@change="\$emit\('validate', 'model'\)"/)
  assert.doesNotMatch(source, /<datalist|list="llm-model-options"/)
})

test('model selector renders provider metadata and a constrained popup', () => {
  assert.match(source, /<el-option[\\s\\S]*?v-for="model in modelOptions"/)
  assert.match(source, /model\.owned_by/)
  assert.match(source, /popper-class="model-select-popper"/)
  assert.match(source, /model-select-popper[\\s\\S]*?max-height:\s*280px/)
  assert.match(source, /暂无可选模型，可直接输入模型名称/)
})

test('model input row stacks on narrow screens', () => {
  assert.match(source, /@media \(max-width:\s*600px\)[\\s\\S]*?\.model-input-row[\\s\\S]*?flex-direction:\s*column/)
})
```

- [ ] **Step 2: Run the test and verify it fails for the native datalist**

Run: `cd frontend && node --test src/views/ai/model-config/components/connectionForm.test.mjs`

Expected: FAIL because `ConnectionForm.vue` does not contain a filterable `el-select` and still contains `datalist`.

- [ ] **Step 3: Commit the failing regression test**

```bash
git add frontend/src/views/ai/model-config/components/connectionForm.test.mjs
git commit -m "test(ai): cover model selector dropdown"
```

### Task 2: Replace the native datalist with the controlled selector

**Files:**
- Modify: `frontend/src/views/ai/model-config/components/ConnectionForm.vue`
- Test: `frontend/src/views/ai/model-config/components/connectionForm.test.mjs`

- [ ] **Step 1: Render the searchable and createable selector**

Replace the native model input and `datalist` with:

```vue
<el-select
  v-model="profile.model"
  class="model-select"
  :class="{ 'is-error': formErrors.model }"
  filterable
  allow-create
  default-first-option
  fit-input-width
  clearable
  placeholder="输入或选择模型"
  popper-class="model-select-popper"
  aria-label="模型名称"
  @change="$emit('validate', 'model')"
  @blur="$emit('validate', 'model')"
>
  <template #empty>
    <div class="model-select-empty">暂无可选模型，可直接输入模型名称</div>
  </template>
  <el-option
    v-for="model in modelOptions"
    :key="model.id"
    :label="model.id"
    :value="model.id"
  >
    <div class="model-option" :title="model.owned_by ? `${model.id} · ${model.owned_by}` : model.id">
      <span class="model-option__id">{{ model.id }}</span>
      <span v-if="model.owned_by" class="model-option__owner">{{ model.owned_by }}</span>
    </div>
  </el-option>
</el-select>
```

Keep the refresh button and existing helper/error text unchanged.

- [ ] **Step 2: Add component and popup styles**

Add styles that make `.model-select` fill the remaining row width, map the error state to `--danger-color`, keep option text on one line, and constrain `.model-select-popper .el-select-dropdown__wrap` to `max-height: 280px`. Use `:global(...)` for the teleported popup class and `color-mix()` for focus/error rings.

Add a `600px` media query that sets `.model-input-row { flex-direction: column; align-items: stretch; }` and gives the refresh button a stable minimum height.

- [ ] **Step 3: Run the focused test and verify it passes**

Run: `cd frontend && node --test src/views/ai/model-config/components/connectionForm.test.mjs`

Expected: PASS, 3 tests and 0 failures.

- [ ] **Step 4: Run the complete frontend source tests**

Run: `cd frontend && node --test "src/**/*.test.mjs" "tests/*.test.mjs"`

Expected: PASS with 0 failures.

- [ ] **Step 5: Run technical UI audit and production build**

Run: `node .agents/skills/impeccable/scripts/detect.mjs --json frontend/src/views/ai/model-config/components/ConnectionForm.vue`

Expected: no newly introduced blocking accessibility, responsive, or styling findings.

Run: `cd frontend && npm run build`

Expected: `vue-tsc -b` and `vite build` exit with code 0.

- [ ] **Step 6: Verify in the browser**

Start the Vite development server, open the model configuration route, refresh a long model list, and check desktop and mobile viewports. Confirm popup alignment, 280px scrolling, filtering, custom value entry, keyboard navigation, loading state, empty state, long IDs, and absence of overlap.

- [ ] **Step 7: Commit the implementation**

```bash
git add frontend/src/views/ai/model-config/components/ConnectionForm.vue
git commit -m "fix(ai): improve refreshed model selector"
```

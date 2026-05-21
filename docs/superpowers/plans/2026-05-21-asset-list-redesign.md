# 主机管理页面重设计 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在主机管理页面顶部增加统计卡片，美化表格布局，重构新增资产表单为分组形式。

**Architecture:** 后端新增 `/assets/stats` 端点返回状态计数（复用已有 `count_assets_by_status` 服务函数），前端重写 `AssetListView.vue` 模板和样式。

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, Element Plus, TypeScript

---

## 文件变更清单

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `backend/app/api/assets.py:52-73` | 在 `/{asset_id}` 路由之前插入 `/stats` 端点 |
| Modify | `frontend/src/api/assets.ts` | 新增 `getAssetStats()` 函数 |
| Rewrite | `frontend/src/views/assets/AssetListView.vue` | 统计卡片 + 美化表格 + 分组表单 |

---

### Task 1: 后端 — 新增 `/assets/stats` 端点

**Files:**
- Modify: `backend/app/api/assets.py:52` (在 `api_list_assets` 之前插入)

- [x] **Step 1: 在 `api_list_assets` 之前插入 stats 端点**

在 `backend/app/api/assets.py` 的 `api_list_assets` 函数（第 52 行）之前插入：

```python
@router.get("/stats")
def api_asset_stats(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("assets.view")),
):
    from app.services.assets import count_assets_by_status
    counts = count_assets_by_status(db)
    total = sum(counts.values())
    return {
        "code": 0,
        "data": {
            "total": total,
            "active": counts.get("使用中", 0),
            "shutdown": counts.get("已关机", 0),
            "deleted": counts.get("已删除", 0),
        },
    }
```

注意：必须在 `@router.get("/{asset_id}")` 之前定义，否则 FastAPI 路由冲突。

- [x] **Step 2: 验证后端**

启动后端，访问 `http://localhost:8000/docs`，确认 `/api/v1/assets/stats` 端点可见并返回正确数据。

- [x] **Step 3: 提交**

```bash
git add backend/app/api/assets.py
git commit -m "feat(assets): add /stats endpoint for status counts"
```

---

### Task 2: 前端 API — 新增 `getAssetStats`

**Files:**
- Modify: `frontend/src/api/assets.ts`

- [x] **Step 1: 在 `assets.ts` 末尾添加函数**

```typescript
export function getAssetStats() {
  return request.get('/assets/stats')
}
```

- [x] **Step 2: 提交**

```bash
git add frontend/src/api/assets.ts
git commit -m "feat(api): add getAssetStats function"
```

---

### Task 3: 前端视图 — 重写 AssetListView

**Files:**
- Rewrite: `frontend/src/views/assets/AssetListView.vue`

这是主要变更，整体重写模板、脚本和样式。

- [x] **Step 1: 重写 AssetListView.vue**

完整替换文件内容：

```vue
<template>
  <div>
    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon stat-icon--blue">
          <el-icon size="20"><Monitor /></el-icon>
        </div>
        <div>
          <div class="stat-label">主机总数</div>
          <div class="stat-value">{{ stats.total }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--green">
          <el-icon size="20"><CircleCheckFilled /></el-icon>
        </div>
        <div>
          <div class="stat-label">使用中</div>
          <div class="stat-value">{{ stats.active }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--amber">
          <el-icon size="20"><VideoPause /></el-icon>
        </div>
        <div>
          <div class="stat-label">已关机</div>
          <div class="stat-value">{{ stats.shutdown }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--red">
          <el-icon size="20"><CircleCloseFilled /></el-icon>
        </div>
        <div>
          <div class="stat-label">已删除</div>
          <div class="stat-value">{{ stats.deleted }}</div>
        </div>
      </div>
    </div>

    <!-- 筛选栏 + 表格 -->
    <div class="data-card">
      <div class="toolbar">
        <h3 class="toolbar-title">资产列表</h3>
        <div class="toolbar-actions">
          <el-input v-model="filters.keyword" placeholder="搜索名称/IP…" clearable style="width:200px" @keyup.enter="fetchData" />
          <el-select v-model="filters.asset_type" placeholder="类型" clearable style="width:120px" @change="fetchData">
            <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
          </el-select>
          <el-select v-model="filters.status" placeholder="状态" clearable style="width:120px" @change="fetchData">
            <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
          <el-button @click="resetFilters" text>重置</el-button>
          <el-button type="primary" @click="showDialog()">+ 新增资产</el-button>
        </div>
      </div>

      <el-table :data="items" stripe v-loading="loading">
        <el-table-column label="主机信息" min-width="180">
          <template #default="{ row }">
            <div class="cell-stack">
              <span class="cell-primary">{{ row.name }}</span>
              <span class="cell-secondary">{{ row.ip_address }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="主机规格" min-width="150">
          <template #default="{ row }">
            <div class="cell-stack">
              <span class="cell-primary">{{ row.spec || '-' }}</span>
              <span class="cell-secondary">{{ row.os || '-' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="owner" label="负责人" width="100" />

        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small" round>{{ row.status }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button size="small" type="primary" link @click="$router.push(`/monitoring/hosts/${row.id}/ssh`)">
                <el-icon><Monitor /></el-icon> SSH
              </el-button>
              <el-button size="small" type="info" link @click="$router.push(`/assets/${row.id}`)">详情</el-button>
              <el-popconfirm title="确认删除该资产？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button size="small" type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <span class="pagination-total">共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="sizes, prev, pager, next"
          @current-change="handleCurrentChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- 新增资产弹窗 -->
    <el-dialog v-model="dialogVisible" title="新增资产" width="580px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" label-position="left">
        <!-- 第一组：基础信息 -->
        <div class="form-group">
          <div class="form-group-title">
            <span class="form-group-number">1</span>
            基础信息
          </div>
          <div class="form-row">
            <el-form-item label="名称" prop="name"><el-input v-model="form.name" placeholder="如 Web-Server-01" /></el-form-item>
            <el-form-item label="类型" prop="asset_type">
              <el-select v-model="form.asset_type" style="width:100%">
                <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-row">
            <el-form-item label="IP" prop="ip_address"><el-input v-model="form.ip_address" placeholder="如 192.168.1.100" /></el-form-item>
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" style="width:100%">
                <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
          </div>
        </div>

        <!-- 第二组：规格与系统 -->
        <div class="form-group">
          <div class="form-group-title">
            <span class="form-group-number">2</span>
            规格与系统
          </div>
          <div class="form-row">
            <el-form-item label="规格"><el-input v-model="form.spec" placeholder="如 4C8G" /></el-form-item>
            <el-form-item label="系统"><el-input v-model="form.os" placeholder="如 Ubuntu 22.04" /></el-form-item>
          </div>
          <el-form-item label="负责人"><el-input v-model="form.owner" placeholder="输入负责人姓名" /></el-form-item>
          <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" placeholder="用途说明" /></el-form-item>
        </div>

        <!-- 第三组：SSH 连接配置 -->
        <div class="form-group">
          <div class="form-group-title">
            <span class="form-group-number">3</span>
            SSH 连接配置
          </div>
          <div class="form-row form-row--three">
            <el-form-item label="端口"><el-input-number v-model="form.ssh_port" :min="1" :max="65535" style="width:100%" /></el-form-item>
            <el-form-item label="用户名"><el-input v-model="form.ssh_username" placeholder="root" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="form.ssh_password" type="password" show-password placeholder="SSH 密码" /></el-form-item>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAssets, getAssetStats, createAsset, deleteAsset } from '@/api/assets'
import { usePagination } from '@/hooks/usePagination'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Monitor, CircleCheckFilled, VideoPause, CircleCloseFilled } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const items = ref<any[]>([])
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const stats = reactive({ total: 0, active: 0, shutdown: 0, deleted: 0 })

const assetTypes = ['云主机', '数据库', '网络设备', '中间件', '其他']
const statusList = [
  { label: '使用中', value: '使用中' },
  { label: '已关机', value: '已关机' },
  { label: '已删除', value: '已删除' },
]

function statusTagType(status: string) {
  const map: Record<string, string> = { '使用中': 'success', '已关机': 'warning', '已删除': 'info' }
  return map[status] || 'info'
}

const { currentPage, pageSize, total, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

const filters = reactive({ keyword: '', asset_type: '', status: '' })
const form = reactive({
  name: '', asset_type: '云主机', ip_address: '', status: '使用中', owner: '', description: '',
  spec: '', os: '', ssh_port: 22, ssh_username: 'root', ssh_password: '',
})
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ip_address: [{ required: true, message: '请输入IP', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

async function fetchStats() {
  try {
    const res: any = await getAssetStats()
    Object.assign(stats, res.data)
  } catch { /* ignore */ }
}

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = { ...filters, page: extra?.page || currentPage.value, page_size: extra?.page_size || pageSize.value }
    const res: any = await getAssets(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

function resetFilters() {
  Object.assign(filters, { keyword: '', asset_type: '', status: '' })
  resetPagination()
  fetchData()
}

function showDialog() {
  Object.assign(form, {
    name: '', asset_type: '云主机', ip_address: '', status: '使用中', owner: '', description: '',
    spec: '', os: '', ssh_port: 22, ssh_username: 'root', ssh_password: '',
  })
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await createAsset(form)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchData()
    fetchStats()
  } finally { saving.value = false }
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确认删除该资产？删除后关联的告警和工单将解除关联。', '确认删除', { type: 'warning' })
  await deleteAsset(id)
  ElMessage.success('删除成功')
  fetchData()
  fetchStats()
}

onMounted(() => { fetchStats(); fetchData() })
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: box-shadow 0.2s;
}
.stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.stat-icon--blue { background: #3b82f6; }
.stat-icon--green { background: #22c55e; }
.stat-icon--amber { background: #f59e0b; }
.stat-icon--red { background: #ef4444; }
.stat-label { font-size: 12px; color: var(--text-muted); }
.stat-value { font-size: 24px; font-weight: 800; color: var(--text-primary); }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar-title { margin: 0; font-size: 16px; font-weight: 700; }
.toolbar-actions { display: flex; gap: 8px; align-items: center; }

.cell-stack { display: flex; flex-direction: column; gap: 2px; }
.cell-primary { font-weight: 600; font-size: 13px; color: var(--text-primary); }
.cell-secondary { font-size: 12px; color: var(--text-muted); }
.action-cell { display: flex; align-items: center; gap: 4px; }

.pagination-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}
.pagination-total { font-size: 13px; color: var(--text-muted); }

.form-group { margin-bottom: 20px; }
.form-group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.form-group-number {
  width: 18px;
  height: 18px;
  background: var(--primary-bg);
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.form-row--three { grid-template-columns: 1fr 1fr 1fr; }

@media (max-width: 900px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
```

- [x] **Step 2: 验证前端**

启动前端开发服务器，打开主机管理页面，确认：
- 顶部 4 个统计卡片正确显示
- 筛选栏布局正确（左侧标题，右侧搜索+筛选+新增按钮）
- 表格样式改善（表头背景、行高、斑马纹）
- 分页栏左右分布
- 点击"新增资产"弹窗分 3 组显示
- 创建/删除操作后统计卡片自动刷新

- [x] **Step 3: 提交**

```bash
git add frontend/src/views/assets/AssetListView.vue
git commit -m "feat(asset-list): redesign with stat cards, improved table and grouped form"
```

---

### Task 4: 最终验证与推送

- [x] **Step 1: 完整功能验证**

1. 打开 `http://localhost:3000/assets/list`
2. 确认统计卡片数字与实际数据一致
3. 测试搜索筛选功能
4. 新增一个资产，确认表单分组正确、创建成功后卡片数字更新
5. 删除一个资产，确认卡片数字更新
6. 点击详情跳转正常
7. 点击 SSH 跳转正常

- [x] **Step 2: 推送**

```bash
git push
```

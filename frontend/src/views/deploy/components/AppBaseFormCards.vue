<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="app-form-cards">
    <div class="form-grid">
      <!-- 主列 -->
      <div class="col-main">
        <section class="form-card" aria-labelledby="afcBasic">
          <header class="card-head">
            <span class="card-icon"><el-icon><Document /></el-icon></span>
            <div class="card-head-t">
              <h3 id="afcBasic" class="card-title">基本信息</h3>
              <p class="card-desc">应用的唯一标识与分类</p>
            </div>
          </header>
          <el-form-item label="应用名称" prop="name">
            <el-input v-model="form.name" placeholder="如：user-service" maxlength="100" show-word-limit />
          </el-form-item>
          <el-form-item label="应用类型" prop="app_type">
            <el-select v-model="form.app_type" style="width: 100%">
              <el-option v-for="t in APP_TYPES" :key="t.value" :label="t.label" :value="t.value">
                <div class="type-opt">
                  <span>{{ t.label }}</span>
                  <span class="type-opt-desc">{{ t.desc }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="应用用途说明（可选）" />
          </el-form-item>
        </section>

        <section class="form-card" aria-labelledby="afcBuild">
          <header class="card-head">
            <span class="card-icon"><el-icon><Connection /></el-icon></span>
            <div class="card-head-t">
              <h3 id="afcBuild" class="card-title">构建与代码源</h3>
              <p class="card-desc">绑定执行构建部署的 Jenkins Job 与代码仓库</p>
            </div>
          </header>
          <el-form-item label="Jenkins Job" prop="jenkins_job_name">
            <el-input v-model="form.jenkins_job_name" placeholder="Jenkins Job 名称（执行构建与部署）" />
          </el-form-item>
          <div class="field-row">
            <el-form-item label="Git 仓库地址">
              <el-input v-model="form.git_url" placeholder="https://github.com/org/repo.git" />
            </el-form-item>
            <el-form-item label="默认分支">
              <el-input v-model="form.git_branch" placeholder="main" />
            </el-form-item>
          </div>
        </section>

        <slot name="main-extra" />
      </div>

      <!-- 辅列 -->
      <div class="col-side">
        <slot name="side-top" />

        <section class="form-card" aria-labelledby="afcContract">
          <header class="card-head">
            <span class="card-icon"><el-icon><Tickets /></el-icon></span>
            <div class="card-head-t">
              <h3 id="afcContract" class="card-title">参数契约</h3>
              <p class="card-desc">Job 需声明以下参数，平台触发时自动注入</p>
            </div>
          </header>
          <div class="param-list">
            <code v-for="p in CONTRACT_PARAMS" :key="p" class="param-chip">{{ p }}</code>
          </div>
          <p class="card-note">构建结束后 Jenkins 回调平台更新部署状态。</p>
        </section>
      </div>
    </div>

    <!-- 底部操作条 -->
    <div class="form-footer">
      <span class="footer-hint"><slot name="footer-hint" /></span>
      <div class="footer-actions"><slot name="footer" /></div>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { Document, Connection, Tickets } from '@element-plus/icons-vue'
import { APP_TYPES } from '@/utils/appTypes'

defineProps<{ form: Record<string, any> }>()

const CONTRACT_PARAMS = ['APP_NAME', 'ENV', 'VERSION', 'OPERATOR', 'RECORD_ID', 'RELEASE_MODE', 'ROLLBACK_FROM', 'CALLBACK_TOKEN']

const rules: FormRules = {
  name: [
    { required: true, message: '请输入应用名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度 2-100 个字符', trigger: 'blur' },
  ],
  app_type: [{ required: true, message: '请选择应用类型', trigger: 'change' }],
}

const formRef = ref<FormInstance>()

defineExpose({
  validate: () => formRef.value?.validate(),
  clearValidate: () => formRef.value?.clearValidate(),
})
</script>

<!-- 非 scoped：所有选择器收敛在 .app-form-cards 下，让插槽内容（状态/环境卡片）复用同一套卡片样式 -->
<style lang="scss">
.app-form-cards {
  .form-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 16px;
    align-items: start;
  }

  .col-main,
  .col-side {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
  }

  .form-card {
    background: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    padding: 18px 20px;
  }

  .card-head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }

  .card-icon {
    width: 30px;
    height: 30px;
    flex: none;
    display: grid;
    place-items: center;
    border-radius: 8px;
    color: var(--primary-color);
    background: var(--primary-bg);
  }

  .card-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
  .card-desc { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

  .el-form-item {
    margin-bottom: 16px;

    &:last-child { margin-bottom: 0; }
  }

  .el-form-item__label { font-weight: 600; }

  .field-row {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
    gap: 12px;

    .el-form-item { margin-bottom: 0; }
  }

  .type-opt {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .type-opt-desc { font-size: 12px; color: var(--text-muted); }

  .param-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .param-chip {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--primary-color);
    background: var(--primary-bg);
    border-radius: 6px;
    padding: 3px 8px;
  }

  .card-note {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 12px;
    line-height: 1.6;
  }

  .form-footer {
    position: sticky;
    bottom: 12px;
    z-index: 5;
    margin-top: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    background: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    padding: 10px 16px;
    box-shadow: 0 6px 20px rgba(15, 23, 42, .08);
  }

  .footer-hint {
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .footer-actions {
    display: flex;
    gap: 8px;

    .el-button + .el-button { margin-left: 0; }
  }

  .dirty-note {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: #b45309;
    font-weight: 600;
  }

  .dirty-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--warning-color);
  }

  @media (max-width: 1100px) {
    .form-grid { grid-template-columns: 1fr; }
  }

  @media (max-width: 640px) {
    .field-row { grid-template-columns: 1fr; }

    .form-footer {
      flex-direction: column;
      align-items: stretch;
      text-align: center;

      .footer-actions { justify-content: center; }
    }
  }
}
</style>

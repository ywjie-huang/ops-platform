<template>
  <div v-loading="loading">
    <!-- 健康总览横幅 -->
    <div class="hero">
      <div class="hero-left">
        <div class="hero-eyebrow">Integration Center</div>
        <div class="hero-title">集成中心</div>
        <div class="hero-desc">统一管理外部服务接入，配置即时生效，无需重启平台。</div>
        <div class="hero-stats">
          <span class="stat-chip"><span class="dot" style="background:#4ade80"></span>正常 <b>{{ countBy('ok') }}</b></span>
          <span class="stat-chip"><span class="dot" style="background:#f87171"></span>异常 <b>{{ countBy('fail') }}</b></span>
          <span class="stat-chip"><span class="dot" style="background:#c9cedb"></span>未配置 <b>{{ countBy('none') }}</b></span>
        </div>
      </div>
      <div class="hero-right">
        <div class="health-ring">
          <svg width="108" height="108" viewBox="0 0 108 108">
            <circle class="ring-track" cx="54" cy="54" r="46" fill="none" stroke-width="9" />
            <circle class="ring-value" cx="54" cy="54" r="46" fill="none" stroke-width="9"
                    :stroke-dasharray="circumference" :stroke-dashoffset="ringOffset" />
          </svg>
          <div class="health-ring-text">
            <b>{{ healthPercent }}%</b>
            <span>服务健康度</span>
          </div>
        </div>
        <button class="btn-glass" :disabled="checkingAll" @click="checkAll">
          {{ checkingAll ? '检测中…' : '重新检测全部' }}
        </button>
      </div>
    </div>

    <!-- 分组卡片 -->
    <template v-for="group in groups" :key="group.title">
      <div class="section-head">
        <span class="section-title">{{ group.title }}</span>
        <span class="section-sub">{{ group.sub }}</span>
      </div>

      <div class="integration-grid">
        <div v-for="svc in servicesByGroup(group.key)" :key="svc.key"
             class="integration-card" :class="'card-' + svc.status">
          <div class="card-head">
            <div class="service-icon" :class="'icon-' + svc.key" v-html="svc.svg"></div>
            <div class="card-title-block">
              <div class="service-name">{{ svc.name }}</div>
              <div class="service-tagline">{{ svc.tagline }}</div>
            </div>
            <span class="status-badge" :class="'status-' + svc.status">
              <span class="dot"></span>{{ statusText(svc.status) }}
            </span>
          </div>

          <p class="service-desc">{{ svc.desc }}</p>

          <div class="service-summary">
            <span class="summary-icon" v-html="linkSvg"></span>
            <span class="url mono" v-if="svc.summary">{{ svc.summary }}</span>
            <span class="empty" v-else>尚未配置服务地址</span>
          </div>

          <div class="card-foot">
            <span class="last-check" v-if="svc.lastCheck">最后检测 {{ svc.lastCheck }}</span>
            <span class="last-check" v-else>&nbsp;</span>
            <div class="card-actions">
              <el-button size="small" :type="svc.expanded ? 'primary' : ''" plain @click="svc.expanded = !svc.expanded">
                {{ svc.expanded ? '收起' : (svc.status === 'none' ? '去配置' : '修改配置') }}
              </el-button>
              <el-button size="small" text :loading="svc.testing" :disabled="!svc.summary" @click="handleTest(svc)">
                测试连接
              </el-button>
            </div>
          </div>

          <el-collapse-transition>
            <div v-show="svc.expanded" class="config-panel">
              <el-form label-position="top">
                <el-form-item v-for="field in svc.fields" :key="field.key" :label="field.label">
                  <el-input v-model="field.value" :type="field.password ? 'password' : 'text'"
                            :show-password="field.password" :placeholder="field.placeholder" />
                  <div class="form-tip">{{ field.tip }}</div>
                </el-form-item>
                <el-button type="primary" size="small" :loading="svc.saving" @click="handleSave(svc)">保存配置</el-button>
              </el-form>
            </div>
          </el-collapse-transition>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSetting, testConnection } from '@/api/settings'

type ServiceStatus = 'ok' | 'fail' | 'none' | 'checking'

interface ConfigField {
  key: string
  label: string
  value: string
  tip: string
  placeholder: string
  password?: boolean
}

interface IntegrationService {
  key: string
  name: string
  tagline: string
  group: string
  desc: string
  status: ServiceStatus
  summary: string
  lastCheck: string
  expanded: boolean
  testing: boolean
  saving: boolean
  svg: string
  fields: ConfigField[]
}

const svgPrometheus = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M12 2c.8 3.2-.6 4.6-2.1 6C8.2 9.5 7 11 7 13.5A5 5 0 0 0 12 18.5a5 5 0 0 0 5-5c0-1.5-.6-2.7-1.4-3.7-.4 1-1 1.6-1.9 2C14.2 9 15.5 5.5 12 2z" fill="currentColor"/><path d="M12 22a8.5 8.5 0 0 0 8.5-8.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity=".55"/></svg>'
const svgAlertmanager = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M12 3a5.5 5.5 0 0 0-5.5 5.5c0 4-1.3 5.6-2.2 6.6-.4.5-.1 1.4.6 1.4h14.2c.7 0 1-.9.6-1.4-.9-1-2.2-2.6-2.2-6.6A5.5 5.5 0 0 0 12 3z" fill="currentColor"/><path d="M9.8 19a2.3 2.3 0 0 0 4.4 0" fill="currentColor" opacity=".7"/></svg>'
const svgJenkins = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="9" r="5.2" fill="currentColor"/><path d="M7 21c.6-3 2.6-4.5 5-4.5s4.4 1.5 5 4.5" fill="currentColor" opacity=".75"/><circle cx="10.2" cy="8.4" r=".9" fill="#2c4250"/><circle cx="13.8" cy="8.4" r=".9" fill="#2c4250"/></svg>'
const svgElasticsearch = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none"><ellipse cx="12" cy="6" rx="7" ry="3" fill="currentColor"/><path d="M5 6v6c0 1.66 3.13 3 7 3s7-1.34 7-3V6" stroke="currentColor" stroke-width="1.8" fill="none" opacity=".75"/><path d="M5 12v6c0 1.66 3.13 3 7 3s7-1.34 7-3v-6" stroke="currentColor" stroke-width="1.8" fill="none" opacity=".55"/></svg>'
const svgKibana = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M4 20V10" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><path d="M10 20V4" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".8"/><path d="M16 20v-8" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".6"/><path d="M22 20v-5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".45"/></svg>'
const linkSvg = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>'

const groups = [
  { key: 'monitor', title: '监控与告警', sub: '数据源与告警事件接入' },
  { key: 'logs', title: '日志服务', sub: '日志存储检索与可视化入口' },
  { key: 'build', title: '构建与发布', sub: '流水线构建引擎接入' },
]

const loading = ref(false)
const checkingAll = ref(false)

const services = reactive<IntegrationService[]>([
  {
    key: 'prometheus', name: 'Prometheus', tagline: 'Metrics & TSDB', group: 'monitor',
    desc: '时序指标数据源，为主机监控图表与告警规则计算提供数据。',
    status: 'none', summary: '', lastCheck: '',
    expanded: false, testing: false, saving: false, svg: svgPrometheus,
    fields: [
      { key: 'url', label: '服务地址', value: '', tip: 'Prometheus HTTP API 地址，如 http://prometheus:9090', placeholder: 'http://prometheus:9090' },
    ],
  },
  {
    key: 'alertmanager', name: 'Alertmanager', tagline: 'Alert Routing', group: 'monitor',
    desc: '告警事件源，用于告警中心的事件拉取与状态同步。',
    status: 'none', summary: '', lastCheck: '',
    expanded: false, testing: false, saving: false, svg: svgAlertmanager,
    fields: [
      { key: 'url', label: '服务地址', value: '', tip: 'Alertmanager HTTP API 地址，如 http://alertmanager:9093', placeholder: 'http://alertmanager:9093' },
    ],
  },
  {
    key: 'elasticsearch', name: 'Elasticsearch', tagline: 'Log Storage & Search', group: 'logs',
    desc: '日志存储与检索引擎，为日志检索、Pod 历史日志与 AI 诊断提供数据。',
    status: 'none', summary: '', lastCheck: '',
    expanded: false, testing: false, saving: false, svg: svgElasticsearch,
    fields: [
      { key: 'url', label: '服务地址', value: '', tip: 'Elasticsearch HTTP 地址，如 http://elasticsearch:9200', placeholder: 'http://elasticsearch:9200' },
      { key: 'username', label: '用户名', value: '', tip: '可选，开启安全认证时填写', placeholder: 'elastic' },
      { key: 'password', label: '密码', value: '', tip: '可选，开启安全认证时填写；留空表示不修改已保存的密码', placeholder: '未设置', password: true },
      { key: 'index', label: '索引模式', value: '', tip: '日志索引匹配模式，如 filebeat-* 或 logs-*', placeholder: 'filebeat-*' },
    ],
  },
  {
    key: 'kibana', name: 'Kibana', tagline: 'Log Visualization', group: 'logs',
    desc: '日志可视化分析入口，从平台一键跳转 Kibana 进行深度日志探索。',
    status: 'none', summary: '', lastCheck: '',
    expanded: false, testing: false, saving: false, svg: svgKibana,
    fields: [
      { key: 'url', label: '服务地址', value: '', tip: 'Kibana 地址（浏览器可访问），如 http://kibana:5601', placeholder: 'http://kibana:5601' },
    ],
  },
  {
    key: 'jenkins', name: 'Jenkins', tagline: 'Build & CI', group: 'build',
    desc: '构建引擎，用于发布部署模块触发流水线构建。',
    status: 'none', summary: '', lastCheck: '',
    expanded: false, testing: false, saving: false, svg: svgJenkins,
    fields: [
      { key: 'url', label: 'Jenkins URL', value: '', tip: 'Jenkins 服务器地址', placeholder: 'http://jenkins.example.com' },
      { key: 'username', label: '用户名', value: '', tip: 'Jenkins API 用户名', placeholder: 'admin' },
      { key: 'token', label: 'API Token', value: '', tip: '在 Jenkins → 用户设置 → API Token 中生成', placeholder: 'Jenkins API Token', password: true },
    ],
  },
])

const servicesByGroup = (g: string) => services.filter(s => s.group === g)
const statusText = (s: ServiceStatus) => ({ ok: '已连接', fail: '连接失败', none: '未配置', checking: '检测中' }[s])
const countBy = (st: ServiceStatus) => services.filter(s => s.status === st).length

const circumference = 2 * Math.PI * 46
const healthPercent = computed(() => Math.round(countBy('ok') / services.length * 100))
const ringOffset = computed(() => circumference * (1 - healthPercent.value / 100))

function now() {
  return new Date().toTimeString().slice(0, 8)
}

function fieldValue(svc: IntegrationService, key: string) {
  return svc.fields.find(f => f.key === key)?.value.trim() || ''
}

async function runTest(svc: IntegrationService, silent = false) {
  const url = fieldValue(svc, 'url')
  if (!url) {
    svc.status = 'none'
    if (!silent) ElMessage.warning('请先输入服务地址')
    return
  }
  svc.testing = true
  svc.status = 'checking'
  try {
    const res: any = await testConnection(svc.key, url, {
      username: fieldValue(svc, 'username'),
      token: fieldValue(svc, 'token') || fieldValue(svc, 'password'),
    })
    svc.status = res.data?.ok ? 'ok' : 'fail'
    if (!silent) {
      if (svc.status === 'ok') ElMessage.success(res.msg || '连接成功')
      else ElMessage.warning(res.msg || '连接失败')
    }
  } catch {
    svc.status = 'fail'
    if (!silent) ElMessage.error('连接失败')
  } finally {
    svc.testing = false
    svc.lastCheck = now()
  }
}

async function handleTest(svc: IntegrationService) {
  await runTest(svc)
}

async function handleSave(svc: IntegrationService) {
  svc.saving = true
  try {
    if (svc.key === 'jenkins') {
      await updateSetting('jenkins_config', JSON.stringify({
        url: fieldValue(svc, 'url'),
        username: fieldValue(svc, 'username'),
        token: fieldValue(svc, 'token'),
      }))
    } else if (svc.key === 'elasticsearch') {
      await updateSetting('elasticsearch.url', fieldValue(svc, 'url'))
      await updateSetting('elasticsearch.username', fieldValue(svc, 'username'))
      await updateSetting('elasticsearch.index', fieldValue(svc, 'index') || 'filebeat-*')
      // 密码留空表示不修改已保存的凭据
      const pwd = fieldValue(svc, 'password')
      if (pwd) await updateSetting('elasticsearch.password', pwd)
    } else {
      await updateSetting(`${svc.key}.url`, fieldValue(svc, 'url'))
    }
    svc.summary = fieldValue(svc, 'url')
    ElMessage.success('配置已保存')
    // 保存后自动探测一次
    await runTest(svc, true)
  } finally {
    svc.saving = false
  }
}

async function checkAll() {
  checkingAll.value = true
  try {
    await Promise.all(services.filter(s => s.summary).map(s => runTest(s, true)))
  } finally {
    checkingAll.value = false
  }
}

async function fetchConfigs() {
  loading.value = true
  try {
    const res: any = await getSettings()
    const configMap: Record<string, string> = {}
    for (const item of res.data.items) {
      configMap[item.key] = item.value
    }
    for (const svc of services) {
      if (svc.key === 'jenkins') {
        try {
          const jc = JSON.parse(configMap['jenkins_config'] || '{}')
          svc.fields.find(f => f.key === 'url')!.value = jc.url || ''
          svc.fields.find(f => f.key === 'username')!.value = jc.username || ''
          svc.fields.find(f => f.key === 'token')!.value = jc.token || ''
        } catch { /* ignore */ }
      } else if (svc.key === 'elasticsearch') {
        svc.fields.find(f => f.key === 'url')!.value = configMap['elasticsearch.url'] || ''
        svc.fields.find(f => f.key === 'username')!.value = configMap['elasticsearch.username'] || ''
        svc.fields.find(f => f.key === 'index')!.value = configMap['elasticsearch.index'] || ''
        // 密码只回传掩码：不回填输入框，用 placeholder 提示已设置
        const pwdField = svc.fields.find(f => f.key === 'password')!
        pwdField.value = ''
        pwdField.placeholder = configMap['elasticsearch.password']
          ? `已设置（${configMap['elasticsearch.password']}），留空不修改`
          : '未设置'
      } else {
        svc.fields[0].value = configMap[`${svc.key}.url`] || ''
      }
      svc.summary = fieldValue(svc, 'url')
      svc.status = svc.summary ? 'checking' : 'none'
    }
  } finally {
    loading.value = false
  }
  // 已配置的服务自动探测连通性
  checkAll()
}

onMounted(fetchConfigs)
</script>

<style scoped>
.mono { font-family: "SF Mono", "JetBrains Mono", Consolas, "Courier New", monospace; }

/* ═══ 顶部健康总览横幅 ═══ */
.hero {
  position: relative; overflow: hidden;
  border-radius: 16px; padding: 28px 32px;
  background: linear-gradient(120deg, #4c54c0 0%, #5e6ad2 45%, #7c5cd6 100%);
  color: #fff; box-shadow: 0 12px 32px -8px rgba(94, 106, 210, .45);
  display: flex; align-items: center; justify-content: space-between; gap: 24px;
}
.hero::before {
  content: ''; position: absolute; inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, .14) 1px, transparent 1px);
  background-size: 22px 22px;
  mask-image: linear-gradient(120deg, rgba(0, 0, 0, .7), transparent 65%);
}
.hero::after {
  content: ''; position: absolute; right: -80px; top: -120px;
  width: 320px; height: 320px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, .18), transparent 70%);
}
.hero-left { position: relative; z-index: 1; }
.hero-eyebrow { font-size: 12px; letter-spacing: .12em; text-transform: uppercase; opacity: .75; margin-bottom: 6px; }
.hero-title { font-size: 24px; font-weight: 700; letter-spacing: .01em; }
.hero-desc { font-size: 13px; opacity: .82; margin-top: 6px; }
.hero-stats { display: flex; gap: 10px; margin-top: 18px; flex-wrap: wrap; }
.stat-chip {
  display: inline-flex; align-items: center; gap: 7px;
  background: rgba(255, 255, 255, .14); backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, .22);
  padding: 5px 12px; border-radius: 20px; font-size: 12px;
}
.stat-chip b { font-size: 14px; font-weight: 700; }
.stat-chip .dot { width: 7px; height: 7px; border-radius: 50%; }

.hero-right { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; gap: 12px; flex-shrink: 0; }
.health-ring { position: relative; width: 108px; height: 108px; }
.health-ring svg { transform: rotate(-90deg); }
.ring-track { stroke: rgba(255, 255, 255, .2); }
.ring-value { stroke: #4ade80; stroke-linecap: round; transition: stroke-dashoffset .8s cubic-bezier(.4, 0, .2, 1); }
.health-ring-text { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.health-ring-text b { font-size: 22px; font-weight: 700; line-height: 1; }
.health-ring-text span { font-size: 11px; opacity: .8; margin-top: 3px; }
.btn-glass {
  background: rgba(255, 255, 255, .16); border: 1px solid rgba(255, 255, 255, .3); color: #fff;
  border-radius: 8px; padding: 7px 14px; font-size: 12px; cursor: pointer;
  backdrop-filter: blur(6px); transition: background .2s; font-family: inherit;
}
.btn-glass:hover:not(:disabled) { background: rgba(255, 255, 255, .26); }
.btn-glass:disabled { opacity: .6; cursor: not-allowed; }

/* ═══ 分组小标题 ═══ */
.section-head { display: flex; align-items: baseline; gap: 10px; margin: 30px 0 14px; }
.section-title { font-size: 15px; font-weight: 700; }
.section-sub { font-size: 12px; color: var(--text-muted); }

/* ═══ 集成卡片 ═══ */
.integration-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 18px; }

.integration-card {
  position: relative;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(23, 24, 28, .04), 0 1px 3px rgba(23, 24, 28, .06);
  padding: 22px;
  transition: transform .22s ease, box-shadow .22s ease;
  overflow: hidden;
}
.integration-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent-from), var(--accent-to));
  opacity: .9;
}
.integration-card:hover { transform: translateY(-4px); box-shadow: 0 8px 16px -4px rgba(23, 24, 28, .08), 0 24px 48px -8px rgba(23, 24, 28, .16); }
.card-ok       { --accent-from: #4ade80; --accent-to: #22c55e; }
.card-fail     { --accent-from: #f87171; --accent-to: #e5484d; }
.card-none     { --accent-from: #d3d7e0; --accent-to: #b9bfcc; }
.card-checking { --accent-from: #818cf8; --accent-to: #5e6ad2; }

.card-head { display: flex; align-items: center; gap: 14px; }
.service-icon {
  width: 48px; height: 48px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #fff; box-shadow: 0 4px 10px -2px var(--icon-shadow);
  background: linear-gradient(135deg, var(--icon-from), var(--icon-to));
}
.icon-prometheus   { --icon-from: #f47c48; --icon-to: #d9431b; --icon-shadow: rgba(230, 82, 44, .4); }
.icon-alertmanager { --icon-from: #ffc65c; --icon-to: #f09000; --icon-shadow: rgba(245, 166, 35, .4); }
.icon-jenkins      { --icon-from: #4b7385; --icon-to: #2c4250; --icon-shadow: rgba(51, 80, 97, .4); }
.icon-elasticsearch { --icon-from: #f5b83d; --icon-to: #d97706; --icon-shadow: rgba(217, 119, 6, .4); }
.icon-kibana       { --icon-from: #f472b6; --icon-to: #d63384; --icon-shadow: rgba(214, 51, 132, .4); }

.card-title-block { flex: 1; min-width: 0; }
.service-name { font-size: 15px; font-weight: 700; letter-spacing: .01em; }
.service-tagline { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* 状态徽章（带呼吸灯） */
.status-badge {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 600; padding: 3px 10px 3px 8px; border-radius: 20px;
  letter-spacing: .02em; flex-shrink: 0;
}
.status-badge .dot { width: 6px; height: 6px; border-radius: 50%; }
.status-ok    { background: rgba(34, 197, 94, .10); color: #15803d; }
.status-ok .dot { background: var(--success-color); animation: breathe 2.2s infinite; }
.status-fail  { background: rgba(229, 72, 77, .10); color: #c2282d; }
.status-fail .dot { background: var(--danger-color); animation: breathe 1.2s infinite; }
.status-none  { background: rgba(154, 160, 171, .12); color: var(--text-secondary); }
.status-none .dot { background: var(--text-muted); }
.status-checking { background: var(--primary-bg); color: var(--primary-color); }
.status-checking .dot { background: var(--primary-color); animation: breathe 1s infinite; }
@keyframes breathe {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; opacity: 1; }
  50% { box-shadow: 0 0 0 4px transparent; opacity: .55; }
}

.service-desc { font-size: 12px; color: var(--text-secondary); line-height: 1.7; margin: 14px 0; min-height: 40px; }

.service-summary {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-secondary);
  background: var(--bg-color); border: 1px solid var(--border-color);
  border-radius: 8px; padding: 8px 11px; margin-bottom: 16px;
  overflow: hidden;
}
.service-summary .url { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.service-summary .empty { color: var(--text-muted); font-style: italic; }
.summary-icon { color: var(--text-muted); flex-shrink: 0; display: flex; }

.card-foot { display: flex; align-items: center; justify-content: space-between; }
.last-check { font-size: 11px; color: var(--text-muted); }
.card-actions { display: flex; gap: 8px; }

/* 展开配置面板 */
.config-panel {
  margin-top: 16px; padding: 16px 16px 8px;
  background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 10px;
}
.form-tip { font-size: 11px; color: var(--text-muted); line-height: 1.4; margin-top: 4px; }

@media (max-width: 720px) {
  .hero { flex-direction: column; align-items: flex-start; }
  .hero-right { align-self: center; }
}
</style>

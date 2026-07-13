<template>
  <div>
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">模型配置</h2>
        <span v-if="configured" class="status-tag success">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          已配置
        </span>
        <span v-else class="status-tag info">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          未配置
        </span>
      </div>
      <div class="header-right">
        <button class="btn" :class="{ 'is-loading': testing }" :disabled="testing" @click="handleTest">
          <svg v-if="!testing" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          <div v-else class="spinner"></div>
          测试连接
        </button>
        <button class="btn btn-primary" :class="{ 'is-loading': saving }" :disabled="saving" @click="handleSave">
          <svg v-if="!saving" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          <div v-else class="spinner"></div>
          保存配置
        </button>
      </div>
    </div>

    <!-- 测试结果提示 -->
    <div v-if="testResult !== null" class="alert" :class="testResult ? 'alert-success' : 'alert-error'" style="margin-bottom: 16px;">
      <svg v-if="testResult" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      <div>
        <strong>{{ testResult ? '连接成功' : '连接失败' }}</strong>
        <div v-if="testResultMsg">{{ testResultMsg }}</div>
      </div>
      <button class="btn-text" @click="testResult = null" style="margin-left: auto;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>

    <!-- 主布局：左侧列表 + 右侧配置 -->
    <div class="main-layout">

      <!-- LEFT: 模型列表 -->
      <div class="card profile-list-card">
        <div class="profile-list-header">
          <span class="profile-list-title">模型配置</span>
          <button class="btn btn-sm btn-primary" @click="handleAddProfile">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            新增
          </button>
        </div>
        <div class="profile-items" v-loading="loadingProfiles">
          <div
            v-for="p in profiles"
            :key="p.id"
            class="profile-item"
            :class="{ active: activeProfileId === p.id }"
            role="option"
            :aria-selected="activeProfileId === p.id"
            tabindex="0"
            @click="selectProfile(p)"
            @keydown.enter.space.prevent="selectProfile(p)"
          >
            <div class="profile-icon">{{ p.icon }}</div>
            <div class="profile-info">
              <div class="profile-name">{{ p.name }}</div>
              <div class="profile-meta">{{ p.provider }} · {{ extractHost(p.base_url) }}</div>
            </div>
            <span class="profile-status" :class="p.is_active ? 'active' : 'inactive'" :title="p.is_active ? '当前使用中' : '未启用'"></span>
          </div>
          <div v-if="!profiles.length && !loadingProfiles" class="empty-state">
            <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            <span class="empty-state-text">暂无配置，点击"新增"开始</span>
          </div>
        </div>
      </div>

      <!-- RIGHT: 配置面板 -->
      <div class="config-panel" v-if="activeProfile">

        <!-- Section 1: 服务商预设 -->
        <div class="card">
          <div class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            快速选择服务商
          </div>
          <div class="card-content">
            <div class="provider-presets">
              <div
                v-for="p in providers"
                :key="p.id"
                class="provider-card"
                :class="{ selected: activeProfile.provider === p.id }"
                role="radio"
                :aria-checked="activeProfile.provider === p.id"
                :aria-label="`${p.name}: ${p.hint}`"
                tabindex="0"
                @click="applyProvider(p)"
                @keydown.enter.space.prevent="applyProvider(p)"
              >
                <div class="provider-logo">{{ p.icon }}</div>
                <div class="provider-name">{{ p.name }}</div>
                <div class="provider-desc">{{ p.hint }}</div>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">接口模式</label>
                <select class="form-input" v-model="activeProfile.api_mode" @change="handleApiModeChange">
                  <option value="chat_completions">Chat Completions</option>
                  <option value="responses">Responses</option>
                </select>
                <span class="form-tip">中转站支持 Responses 时可切换到新接口</span>
              </div>
              <div class="form-group" v-if="activeProfile.api_mode === 'responses'">
                <label class="form-label">推理强度</label>
                <select class="form-input" v-model="activeProfile.reasoning_effort">
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
                <span class="form-tip">仅 Responses 模式生效</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Section 2: 连接配置 -->
        <div class="card">
          <div class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
            连接配置
          </div>
          <div class="card-content">
            <div class="form-group">
              <label class="form-label"><span class="required">*</span> API 地址</label>
              <input
                class="form-input"
                :class="{ error: formErrors.base_url }"
                v-model="activeProfile.base_url"
                placeholder="https://api.openai.com/v1"
                @blur="validateField('base_url')"
              />
              <span v-if="formErrors.base_url" class="form-error">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                {{ formErrors.base_url }}
              </span>
              <span v-else class="form-tip">OpenAI 兼容接口地址，支持 OpenAI / DeepSeek / 通义千问 / Ollama 等</span>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">API Key</label>
                <div class="form-input-password">
                  <input
                    class="form-input"
                    :type="showPassword ? 'text' : 'password'"
                    v-model="activeProfile.api_key"
                    placeholder="sk-xxxxxxxxxxxxxxxx"
                  />
                  <span class="eye-icon" @click="showPassword = !showPassword">
                    <svg v-if="!showPassword" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  </span>
                </div>
                <span class="form-tip">部分本地模型（如 Ollama）可留空</span>
              </div>
              <div class="form-group">
                <label class="form-label"><span class="required">*</span> 模型名称</label>
                <input
                  class="form-input"
                  :class="{ error: formErrors.model }"
                  v-model="activeProfile.model"
                  placeholder="gpt-4o"
                  @blur="validateField('model')"
                />
                <span v-if="formErrors.model" class="form-error">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  {{ formErrors.model }}
                </span>
                <span v-else class="form-tip">模型标识符，如 gpt-4o、deepseek-chat、qwen-plus</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Section 3: 模型参数 -->
        <div class="card">
          <div class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            模型参数
          </div>
          <div class="card-content">
            <div class="params-grid">
              <div class="param-card">
                <div class="param-header">
                  <div class="param-label-row">
                    <span class="param-label">Temperature</span>
                    <span class="param-tooltip" tabindex="0">
                      <svg class="tooltip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                      <span class="tooltip-content">控制回复的随机性。低值 (0.1-0.3) 更精确稳定，适合事实查询；高值 (0.7-1.0) 更有创意，适合头脑风暴。运维场景建议 0.3-0.5。</span>
                    </span>
                  </div>
                  <span class="param-value">{{ activeProfile.temperature.toFixed(1) }}</span>
                </div>
                <input
                  type="range"
                  class="param-slider"
                  v-model.number="activeProfile.temperature"
                  min="0"
                  max="2"
                  step="0.1"
                  aria-label="Temperature 值"
                />
                <div class="param-range"><span>0 (精确)</span><span>2 (随机)</span></div>
              </div>
              <div class="param-card">
                <div class="param-header">
                  <div class="param-label-row">
                    <span class="param-label">Max Tokens</span>
                    <span class="param-tooltip" tabindex="0">
                      <svg class="tooltip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                      <span class="tooltip-content">单次回复的最大长度（token 数）。1 个中文字约 1.5 token。4096 约等于 2700 个中文字，足够大多数运维问答。复杂任务可适当增大。</span>
                    </span>
                  </div>
                  <span class="param-value">{{ activeProfile.max_tokens }}</span>
                </div>
                <input
                  type="range"
                  class="param-slider"
                  v-model.number="activeProfile.max_tokens"
                  min="256"
                  max="32768"
                  step="256"
                  aria-label="Max Tokens 值"
                />
                <div class="param-range"><span>256</span><span>32768</span></div>
              </div>
              <div class="param-card">
                <div class="param-header">
                  <div class="param-label-row">
                    <span class="param-label">Top P</span>
                    <span class="param-tooltip" tabindex="0">
                      <svg class="tooltip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                      <span class="tooltip-content">核采样参数，与 Temperature 配合使用。1.0 表示不启用，0.9 表示只考虑概率前 90% 的词。通常保持默认 1.0 即可，调低会使回复更保守。</span>
                    </span>
                  </div>
                  <span class="param-value">{{ activeProfile.top_p.toFixed(2) }}</span>
                </div>
                <input
                  type="range"
                  class="param-slider"
                  v-model.number="activeProfile.top_p"
                  min="0"
                  max="1"
                  step="0.05"
                  aria-label="Top P 值"
                />
                <div class="param-range"><span>0</span><span>1</span></div>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">系统提示词 <span class="tag tag-default">可选</span></label>
              <textarea
                class="form-input"
                v-model="activeProfile.system_prompt"
                rows="3"
                placeholder="你是一个专业的运维助手，擅长 Linux 系统管理、Docker 容器编排和 Kubernetes 运维..."
                style="resize: vertical; min-height: 72px;"
              ></textarea>
              <span class="form-tip">自定义 AI 助手的角色和行为。留空使用默认提示词。</span>
            </div>
          </div>
        </div>

        <!-- Section 4: 快速测试 -->
        <div class="card">
          <div class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            快速测试
          </div>
          <div class="card-content">
            <div class="test-area">
              <div class="test-messages" ref="testMessagesRef" aria-live="polite">
                <div
                  v-for="(msg, idx) in testMessages"
                  :key="idx"
                  class="test-msg"
                  :class="msg.role"
                >
                  <div class="test-msg-avatar">
                    <svg v-if="msg.role === 'user'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
                  </div>
                  <div class="test-msg-bubble">{{ msg.content }}</div>
                </div>
                <div v-if="testSending" class="test-msg assistant">
                  <div class="test-msg-avatar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
                  </div>
                  <div class="test-msg-bubble" style="color: var(--text-muted); font-style: italic;">思考中...</div>
                </div>
              </div>
              <div class="test-input-row">
                <input
                  class="form-input"
                  v-model="testInput"
                  placeholder="输入测试消息，按 Enter 发送..."
                  @keydown.enter.prevent="handleTestChat"
                  :disabled="testSending"
                />
                <button
                  class="btn btn-primary"
                  :disabled="!testInput.trim() || testSending"
                  :class="{ 'is-loading': testSending }"
                  @click="handleTestChat"
                >
                  <svg v-if="!testSending" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                  <div v-else class="spinner"></div>
                  发送
                </button>
              </div>
              <div v-if="testChatResult" class="test-result" :class="testChatResult.ok ? 'success' : 'error'">
                <svg v-if="testChatResult.ok" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                {{ testChatResult.ok ? '✓' : '✗' }} {{ testChatResult.msg }}
              </div>
            </div>
          </div>
        </div>

        <!-- 操作栏 -->
        <div class="action-bar">
          <button
            v-if="profiles.length > 1"
            class="btn btn-danger"
            @click="handleDeleteProfile"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            删除此配置
          </button>
          <div class="action-bar-right">
            <button
              v-if="!activeProfile.is_active"
              class="btn btn-success"
              @click="handleSetActive"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              设为当前使用
            </button>
            <span v-else class="tag tag-active">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              当前使用中
            </span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="card empty-panel">
        <svg class="empty-panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        <p>请从左侧选择或新增一个模型配置</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getLLMProfiles, updateLLMProfiles, testLLMConnection,
  type LLMProfile,
} from '@/api/settings'
import { sendAiMessageStream } from '@/api/ai'
import { resolveProviderDraft, snapshotProviderDraft } from './providerPreset'

// ── 服务商预设 ──
const providers: Array<{
  id: string
  name: string
  icon: string
  hint: string
  base_url: string
  model: string
  api_mode?: 'chat_completions' | 'responses'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
}> = [
  { id: 'openai', name: 'OpenAI', icon: 'AI', hint: 'GPT-4o / o3', base_url: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { id: 'deepseek', name: 'DeepSeek', icon: 'DS', hint: 'DeepSeek Chat', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  { id: 'qwen', name: '通义千问', icon: 'QW', hint: 'Qwen Plus', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  { id: 'ollama', name: 'Ollama', icon: 'OL', hint: '本地部署', base_url: 'http://localhost:11434/v1', model: 'qwen2.5:7b' },
]

// ── 状态 ──
const loading = ref(false)
const loadingProfiles = ref(false)
const saving = ref(false)
const testing = ref(false)
const configured = ref(false)
const testResult = ref<boolean | null>(null)
const testResultMsg = ref('')
const showPassword = ref(false)

const profiles = ref<LLMProfile[]>([])
const activeProfileId = ref<string | null>(null)
const providerDrafts = reactive<Record<string, ReturnType<typeof snapshotProviderDraft>>>({})

const activeProfile = computed(() => profiles.value.find(p => p.id === activeProfileId.value) || null)

// ── 表单验证 ──
const formErrors = reactive<Record<string, string>>({
  base_url: '',
  model: '',
})

function validateField(field: string) {
  if (field === 'base_url') {
    formErrors.base_url = activeProfile.value?.base_url.trim() ? '' : '请输入 API 地址'
  } else if (field === 'model') {
    formErrors.model = activeProfile.value?.model.trim() ? '' : '请输入模型名称'
  }
}

function validateForm(): boolean {
  validateField('base_url')
  validateField('model')
  return !formErrors.base_url && !formErrors.model
}

// ── 快速测试 ──
const testInput = ref('')
const testSending = ref(false)
const testMessages = ref<Array<{ role: string; content: string }>>([])
const testMessagesRef = ref<HTMLElement | null>(null)
const testChatResult = ref<{ ok: boolean; msg: string } | null>(null)

// ── 工具函数 ──
function extractHost(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url || '—'
  }
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}

// ── 数据加载 ──
async function fetchProfiles() {
  loadingProfiles.value = true
  try {
    const res: any = await getLLMProfiles()
    profiles.value = res.data?.items || []

    // 迁移：如果没有 profiles，从旧的单一配置创建一个
    if (!profiles.value.length) {
      await migrateFromLegacy()
    }

    // 默认选中激活的
    const active = profiles.value.find(p => p.is_active)
    activeProfileId.value = active?.id || profiles.value[0]?.id || null
    configured.value = !!active
  } finally {
    loadingProfiles.value = false
  }
}

async function migrateFromLegacy() {
  // 读取旧的单一配置
  const { getSettings } = await import('@/api/settings')
  const res: any = await getSettings()
  const items: Record<string, string> = {}
  for (const item of res.data.items) {
    items[item.key] = item.value
  }

  if (items['llm.base_url'] || items['llm.model']) {
    const profile: LLMProfile = {
      id: generateId(),
      name: items['llm.model'] || '默认模型',
      provider: guessProvider(items['llm.base_url'] || ''),
      icon: guessIcon(items['llm.base_url'] || ''),
      base_url: items['llm.base_url'] || '',
      api_key: items['llm.api_key'] || '',
      model: items['llm.model'] || '',
      temperature: parseFloat(items['llm.temperature'] || '0.7'),
      max_tokens: parseInt(items['llm.max_tokens'] || '4096'),
      top_p: parseFloat(items['llm.top_p'] || '1.0'),
      system_prompt: items['llm.system_prompt'] || '',
      is_active: true,
    }
    profiles.value = [profile]
    await saveProfiles()
  }
}

function guessProvider(url: string): string {
  if (url.includes('openai')) return 'openai'
  if (url.includes('deepseek')) return 'deepseek'
  if (url.includes('dashscope') || url.includes('aliyuncs')) return 'qwen'
  if (url.includes('localhost:11434') || url.includes('ollama')) return 'ollama'
  return 'custom'
}

function guessIcon(url: string): string {
  const provider = guessProvider(url)
  const found = providers.find(p => p.id === provider)
  return found?.icon || '⚡'
}

// ── 保存 profiles ──
async function saveProfiles() {
  saving.value = true
  try {
    await updateLLMProfiles(profiles.value)
    configured.value = profiles.value.some(p => p.is_active)
    ElMessage.success('配置已保存')
  } finally {
    saving.value = false
  }
}

// ── 选择配置 ──
function selectProfile(p: LLMProfile) {
  activeProfileId.value = p.id
  testResult.value = null
  testMessages.value = []
  testChatResult.value = null
  formErrors.base_url = ''
  formErrors.model = ''
}

// ── 新增配置 ──
function handleAddProfile() {
  const newProfile: LLMProfile = {
    id: generateId(),
    name: '新模型',
    provider: 'custom',
    icon: '⚡',
    base_url: '',
    api_key: '',
    model: '',
    temperature: 0.7,
    max_tokens: 4096,
    top_p: 1.0,
    system_prompt: '',
    is_active: false,
  }
  profiles.value.push(newProfile)
  activeProfileId.value = newProfile.id
}

// ── 删除配置 ──
async function handleDeleteProfile() {
  if (!activeProfile.value) return
  await ElMessageBox.confirm(`确定删除配置「${activeProfile.value.name}」？`, '确认删除', {
    type: 'warning',
  })
  const idx = profiles.value.findIndex(p => p.id === activeProfileId.value)
  profiles.value.splice(idx, 1)
  activeProfileId.value = profiles.value[Math.min(idx, profiles.value.length - 1)]?.id || null
  await saveProfiles()
}

// ── 设为当前使用 ──
async function handleSetActive() {
  if (!activeProfile.value) return
  profiles.value.forEach(p => { p.is_active = p.id === activeProfileId.value })
  await saveProfiles()
}

// ── 应用服务商预设 ──
function applyProvider(p: typeof providers[number]) {
  if (!activeProfile.value) return
  if (activeProfile.value.provider) {
    providerDrafts[activeProfile.value.provider] = snapshotProviderDraft(activeProfile.value)
  }
  const draft = resolveProviderDraft({
    nextPreset: p,
    rememberedDraft: providerDrafts[p.id],
  })
  activeProfile.value.provider = p.id
  activeProfile.value.icon = p.icon
  activeProfile.value.name = p.name
  activeProfile.value.base_url = draft.base_url
  activeProfile.value.model = draft.model
  activeProfile.value.api_mode = draft.api_mode
  activeProfile.value.reasoning_effort = draft.reasoning_effort
  testResult.value = null
  formErrors.base_url = ''
  formErrors.model = ''
}

function handleApiModeChange() {
  if (!activeProfile.value) return
  if (activeProfile.value.api_mode === 'responses') {
    activeProfile.value.reasoning_effort = activeProfile.value.reasoning_effort || 'medium'
  } else {
    activeProfile.value.reasoning_effort = ''
  }
}

// ── 保存按钮 ──
async function handleSave() {
  if (!activeProfile.value) return
  if (!validateForm()) return
  // 自动更新名称
  if (activeProfile.value.name === '新模型' && activeProfile.value.model) {
    activeProfile.value.name = activeProfile.value.model
  }
  await saveProfiles()
}

// ── 测试连接 ──
async function handleTest() {
  if (!activeProfile.value) return
  const p = activeProfile.value
  if (!p.base_url.trim() || !p.model.trim()) {
    ElMessage.warning('请至少填写 API 地址和模型名称')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const res: any = await testLLMConnection({
      base_url: p.base_url.trim(),
      api_key: p.api_key.trim(),
      model: p.model.trim(),
      api_mode: p.api_mode || 'chat_completions',
      reasoning_effort: p.reasoning_effort || '',
    })
    testResult.value = res.data?.ok ?? false
    testResultMsg.value = res.msg || ''
  } catch {
    testResult.value = false
    testResultMsg.value = '请求失败，请检查网络或配置'
  } finally {
    testing.value = false
  }
}

// ── 快速测试聊天 ──
async function handleTestChat() {
  if (!testInput.value.trim() || testSending.value) return
  const msg = testInput.value.trim()
  testInput.value = ''
  testMessages.value.push({ role: 'user', content: msg })
  testSending.value = true
  testChatResult.value = null
  await nextTick()
  scrollTestMessages()

  const startTime = Date.now()
  try {
    let fullText = ''
    for await (const event of sendAiMessageStream(msg)) {
      if (event.type === 'text') {
        fullText += event.content
      } else if (event.type === 'error') {
        testChatResult.value = { ok: false, msg: event.content || '请求失败' }
        break
      } else if (event.type === 'done') {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
        testChatResult.value = {
          ok: true,
          msg: `连接成功 · 响应时间 ${elapsed}s · 模型: ${activeProfile.value?.model}`,
        }
        break
      }
    }
    if (fullText) {
      testMessages.value.push({ role: 'assistant', content: fullText })
    }
  } catch (e: any) {
    testChatResult.value = { ok: false, msg: e.message || '请求失败' }
  } finally {
    testSending.value = false
    await nextTick()
    scrollTestMessages()
  }
}

function scrollTestMessages() {
  if (testMessagesRef.value) {
    testMessagesRef.value.scrollTo({
      top: testMessagesRef.value.scrollHeight,
      behavior: 'smooth'
    })
  }
}

onMounted(fetchProfiles)
</script>

<style scoped>
/* ── SVG Icon System ── */
.icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* ── Page Header ── */
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-right {
  display: flex;
  gap: 8px;
}

/* ── Status Tag ── */
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.status-tag.success { background: var(--success-bg, #f0fdf4); color: var(--success-color, #16a34a); border: 1px solid var(--success-border, #bbf7d0); }
.status-tag.info { background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; }
.status-tag.error { background: var(--error-bg, #fef2f2); color: var(--error-color, #dc2626); border: 1px solid var(--error-border, #fecaca); }

/* ── Buttons ── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-primary);
  transition: all 0.15s;
}
.btn:hover { border-color: #c0c4cc; }
.btn:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}
.btn-primary:hover { background: var(--primary-hover); }
.btn-danger {
  background: var(--error-bg, #fef2f2);
  color: var(--error-color, #dc2626);
  border-color: var(--error-border, #fecaca);
}
.btn-danger:hover { background: #fee2e2; }
.btn-success {
  background: var(--success-bg, #f0fdf4);
  color: var(--success-color, #16a34a);
  border-color: var(--success-border, #bbf7d0);
}
.btn-success:hover { background: #dcfce7; }
.btn-text { border: none; background: none; color: var(--primary-color); padding: 4px 8px; }
.btn-text:hover { background: var(--primary-bg); }
.btn-sm { padding: 4px 12px; font-size: 12px; }
.btn:disabled, .btn.is-loading {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Cards ── */
.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
}

/* ── Main Layout ── */
.main-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  align-items: start;
}

/* ── Profile List ── */
.profile-list-card {
  padding: 0;
  overflow: hidden;
}
.profile-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--border-color);
}
.profile-list-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.profile-items {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 120px;
}
.profile-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s;
  border: 1px solid transparent;
}
.profile-item:hover { background: var(--bg-color); }
.profile-item:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.profile-item.active {
  background: var(--primary-bg);
  border-color: rgba(94, 106, 210, 0.2);
}
.profile-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #f5f5f5;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-secondary);
}
.profile-item.active .profile-icon {
  background: rgba(94, 106, 210, 0.12);
  color: var(--primary-color);
}
.profile-info { flex: 1; min-width: 0; }
.profile-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.profile-meta {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.profile-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.profile-status.active { background: var(--success-color, #16a34a); }
.profile-status.inactive { background: #d9d9d9; }

/* ── Empty State ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
  gap: 8px;
}
.empty-state-icon {
  width: 40px;
  height: 40px;
  color: var(--text-muted);
  opacity: 0.5;
}
.empty-state-text {
  font-size: 13px;
  color: var(--text-muted);
}
.empty-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 12px;
}
.empty-panel-icon {
  width: 48px;
  height: 48px;
  color: #d9d9d9;
}
.empty-panel p { font-size: 14px; color: var(--text-muted); }

/* ── Config Panel ── */
.config-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Section Title ── */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title svg { color: var(--text-secondary); }

/* ── Card Content ── */
.card-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 12px;
}

/* ── Provider Presets ── */
.provider-presets {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.provider-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.15s;
  background: var(--surface-color);
}
.provider-card:hover {
  border-color: #c0c4cc;
  background: #fafafa;
}
.provider-card:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.provider-card.selected {
  border-color: var(--primary-color);
  background: var(--primary-bg);
  box-shadow: 0 0 0 1px var(--primary-color);
}
.provider-logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
}
.provider-card.selected .provider-logo {
  background: rgba(94, 106, 210, 0.12);
  color: var(--primary-color);
}
.provider-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.provider-desc {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
}

/* ── Form Styles ── */
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 4px;
}
.form-label .required { color: var(--error-color, #dc2626); }
.form-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
  background: var(--surface-color);
  color: var(--text-primary);
}
.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.1);
}
.form-input:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 1px;
}
.form-input::placeholder { color: var(--text-muted); }
.form-input.error {
  border-color: var(--error-color, #dc2626);
  box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.1);
}
.form-input-password {
  position: relative;
}
.form-input-password .form-input { padding-right: 36px; width: 100%; }
.form-input-password .eye-icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
}
.form-tip {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}
.form-error {
  font-size: 12px;
  color: var(--error-color, #dc2626);
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ── Advanced Params ── */
.params-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.param-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-color);
}
.param-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.param-label-row {
  display: flex;
  align-items: center;
  gap: 4px;
}
.param-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}
.param-tooltip {
  position: relative;
  display: inline-flex;
  cursor: help;
}
.param-tooltip .tooltip-icon {
  width: 14px;
  height: 14px;
  color: var(--text-muted);
  opacity: 0.7;
}
.param-tooltip .tooltip-content {
  display: none;
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: #1a1a1a;
  color: #fff;
  font-size: 12px;
  font-weight: 400;
  padding: 8px 10px;
  border-radius: 6px;
  line-height: 1.4;
  white-space: normal;
  width: 220px;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.param-tooltip .tooltip-content::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: #1a1a1a;
}
.param-tooltip:hover .tooltip-content,
.param-tooltip:focus-within .tooltip-content {
  display: block;
}
.param-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-color);
  font-family: 'SF Mono', 'Consolas', monospace;
}
.param-slider {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: #e8e8e8;
  border-radius: 2px;
  outline: none;
}
.param-slider:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 4px;
  border-radius: 2px;
}
.param-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--primary-color);
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(94, 106, 210, 0.3);
}
.param-range {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-muted);
}

/* ── Inline Tag ── */
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  height: 22px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}
.tag-default { background: #f5f5f5; color: var(--text-secondary); }
.tag-active { background: var(--primary-bg); color: var(--primary-color); }

/* ── Alert Banner ── */
.alert {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.4;
}
.alert svg { flex-shrink: 0; margin-top: 1px; }
.alert-success { background: var(--success-bg, #f0fdf4); color: var(--success-color, #16a34a); border: 1px solid var(--success-border, #bbf7d0); }
.alert-error { background: var(--error-bg, #fef2f2); color: var(--error-color, #dc2626); border: 1px solid var(--error-border, #fecaca); }

/* ── Test Area ── */
.test-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.test-messages {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 240px;
  overflow-y: auto;
  padding: 12px;
  background: var(--bg-color);
  border-radius: 6px;
  border: 1px solid var(--border-color);
}
.test-msg {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.test-msg.user { flex-direction: row-reverse; }
.test-msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #f0f0f0;
}
.test-msg.user .test-msg-avatar { background: var(--primary-bg); color: var(--primary-color); }
.test-msg.assistant .test-msg-avatar { background: #e8f5e9; color: #4caf50; }
.test-msg-bubble {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  max-width: 80%;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.test-msg.user .test-msg-bubble {
  background: var(--primary-color);
  color: white;
  border-bottom-right-radius: 2px;
}
.test-msg.assistant .test-msg-bubble {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 2px;
}
.test-input-row {
  display: flex;
  gap: 8px;
}
.test-input-row .form-input { flex: 1; }
.test-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
}
.test-result svg { flex-shrink: 0; }
.test-result.success { background: var(--success-bg, #f0fdf4); color: var(--success-color, #16a34a); border: 1px solid var(--success-border, #bbf7d0); }
.test-result.error { background: var(--error-bg, #fef2f2); color: var(--error-color, #dc2626); border: 1px solid var(--error-border, #fecaca); }

/* ── Loading Spinner ── */
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Action Bar ── */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.action-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .main-layout { grid-template-columns: 1fr; }
  .provider-presets { grid-template-columns: repeat(2, 1fr); }
  .params-grid { grid-template-columns: 1fr; }
  .form-row { grid-template-columns: 1fr; }
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d9d9d9; border-radius: 3px; }

/* ── Reduced Motion ── */
@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
    transition: none !important;
  }
}
</style>

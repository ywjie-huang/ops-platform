export type ApiMode = 'chat_completions' | 'responses' | 'anthropic'

export interface ProviderDraft {
  base_url: string
  model: string
  api_mode: ApiMode
  reasoning_effort: '' | 'low' | 'medium' | 'high'
}

export interface ProviderPreset {
  id: string
  name: string
  icon: string
  hint: string
  base_url: string
  model: string
  api_mode?: ApiMode
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
}

export const PROVIDER_PRESETS: ProviderPreset[] = [
  // ─── 国际 ───
  { id: 'openai', name: 'OpenAI', icon: 'AI', hint: 'GPT-4o / o3', base_url: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { id: 'claude', name: 'Claude (Anthropic)', icon: 'CL', hint: 'Sonnet / Opus · Anthropic 协议', base_url: 'https://api.anthropic.com', model: 'claude-sonnet-4-5', api_mode: 'anthropic' },
  // ─── 国内 ───
  { id: 'zhipu', name: '智谱 GLM', icon: 'ZP', hint: 'GLM-4.7 / GLM-5 · OpenAI 协议', base_url: 'https://open.bigmodel.cn/api/paas/v4/', model: 'glm-4.7-flash' },
  { id: 'zhipu_coding', name: '智谱 Coding', icon: 'ZP', hint: 'GLM Coding Plan · Anthropic 协议', base_url: 'https://open.bigmodel.cn/api/anthropic', model: 'glm-4.6', api_mode: 'anthropic' },
  { id: 'moonshot', name: 'Kimi (月之暗面)', icon: 'KS', hint: 'Kimi K3', base_url: 'https://api.moonshot.cn/v1', model: 'kimi-k3' },
  { id: 'deepseek', name: 'DeepSeek', icon: 'DS', hint: 'DeepSeek V4', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-v4-flash' },
  { id: 'qwen', name: '通义千问', icon: 'QW', hint: 'Qwen3.7 (阿里云百炼)', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen3.7-plus' },
  { id: 'doubao', name: '豆包 (火山方舟)', icon: 'DB', hint: 'Doubao Seed (字节跳动)', base_url: 'https://ark.cn-beijing.volces.com/api/v3', model: 'doubao-seed-1.6-250615' },
  { id: 'wenxin', name: '文心一言 (百度千帆)', icon: 'WX', hint: 'ERNIE 4.0', base_url: 'https://qianfan.baidubce.com/v2', model: 'ernie-4.0-turbo' },
  // ─── 本地 / 通用 ───
  { id: 'ollama', name: 'Ollama', icon: 'OL', hint: '本地部署', base_url: 'http://localhost:11434/v1', model: 'qwen2.5:7b' },
  { id: 'openai_compatible', name: 'OpenAI 兼容', icon: 'API', hint: '中转站 / 网关', base_url: 'https://your-gateway.example/v1', model: 'gpt-4o' },
  { id: 'custom', name: '自定义', icon: '⚡', hint: '手动填写全部字段', base_url: '', model: '' },
]

export const SYSTEM_PROMPT_TEMPLATES: Array<{ id: string; name: string; content: string }> = [
  {
    id: 'ops_general',
    name: '通用运维助手',
    content:
      '你是一个专业的运维助手，擅长 Linux 系统管理、Docker 容器编排、Kubernetes 运维与故障排查。回答简洁、可执行，优先给出命令和排查步骤。',
  },
  {
    id: 'incident',
    name: '故障排查',
    content:
      '你是线上故障排查专家。请按“现象确认 → 影响面 → 可能原因 → 验证步骤 → 处置建议”结构化回答，避免空泛建议，优先可落地命令。',
  },
  {
    id: 'patrol',
    name: '巡检报告解读',
    content:
      '你是巡检报告解读助手。请提炼异常项、风险等级、可能根因和优先处理建议，输出适合值班交接的简洁结论。',
  },
  {
    id: 'ticket',
    name: '工单撰写',
    content:
      '你是运维工单撰写助手。请输出清晰的标题、背景、影响、处理步骤与验收标准，语言专业简洁，便于协作跟进。',
  },
]

export const TEMPERATURE_PRESETS = [
  { id: 'precise', label: '精确', value: 0.2 },
  { id: 'balanced', label: '均衡', value: 0.5 },
  { id: 'creative', label: '发散', value: 0.8 },
] as const

export function snapshotProviderDraft(profile: Partial<ProviderDraft>): ProviderDraft {
  return {
    base_url: profile.base_url || '',
    model: profile.model || '',
    api_mode: profile.api_mode || 'chat_completions',
    reasoning_effort: profile.reasoning_effort || '',
  }
}

export function resolveProviderDraft({
  nextPreset,
  rememberedDraft,
}: {
  nextPreset: ProviderPreset
  rememberedDraft?: Partial<ProviderDraft>
}): ProviderDraft {
  const draft = rememberedDraft || {}
  return {
    base_url: draft.base_url || nextPreset.base_url,
    model: draft.model || nextPreset.model,
    api_mode: draft.api_mode || nextPreset.api_mode || 'chat_completions',
    reasoning_effort:
      draft.reasoning_effort !== undefined
        ? draft.reasoning_effort
        : nextPreset.reasoning_effort || '',
  }
}

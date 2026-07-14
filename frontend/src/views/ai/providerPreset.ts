export interface ProviderDraft {
  base_url: string
  model: string
  api_mode: 'chat_completions' | 'responses'
  reasoning_effort: '' | 'low' | 'medium' | 'high'
}

export interface ProviderPreset {
  id: string
  name: string
  icon: string
  hint: string
  base_url: string
  model: string
  api_mode?: 'chat_completions' | 'responses'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
}

export const PROVIDER_PRESETS: ProviderPreset[] = [
  { id: 'openai', name: 'OpenAI', icon: 'AI', hint: 'GPT-4o / o3', base_url: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { id: 'deepseek', name: 'DeepSeek', icon: 'DS', hint: 'DeepSeek Chat', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  { id: 'qwen', name: '通义千问', icon: 'QW', hint: 'Qwen Plus', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
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

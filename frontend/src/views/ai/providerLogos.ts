/**
 * 服务商品牌 Logo 映射 —— 独立模块，避免 providerPreset.ts 引入静态资源。
 * providerPreset.ts 会被 node --test（类型擦除）直接 import，不能依赖 vite alias / svg loader。
 */
import openaiLogo from '@/assets/provider-logos/openai.svg'
import claudeLogo from '@/assets/provider-logos/claude.svg'
import zhipuLogo from '@/assets/provider-logos/zhipu.svg'
import kimiLogo from '@/assets/provider-logos/kimi.svg'
import deepseekLogo from '@/assets/provider-logos/deepseek.svg'
import qwenLogo from '@/assets/provider-logos/qwen.svg'
import doubaoLogo from '@/assets/provider-logos/doubao.svg'
import ollamaLogo from '@/assets/provider-logos/ollama.svg'
import openaiCompatibleLogo from '@/assets/provider-logos/openai-compatible.svg'
import customLogo from '@/assets/provider-logos/custom.svg'

const PROVIDER_LOGOS: Record<string, string> = {
  openai: openaiLogo,
  claude: claudeLogo,
  zhipu: zhipuLogo,
  zhipu_coding: zhipuLogo,
  moonshot: kimiLogo,
  deepseek: deepseekLogo,
  qwen: qwenLogo,
  doubao: doubaoLogo,
  ollama: ollamaLogo,
  openai_compatible: openaiCompatibleLogo,
  custom: customLogo,
}

/** 按 provider id 取品牌 Logo；无匹配时返回 undefined，调用方回退显示字母 icon */
export function providerLogoOf(providerId?: string): string | undefined {
  return providerId ? PROVIDER_LOGOS[providerId] : undefined
}

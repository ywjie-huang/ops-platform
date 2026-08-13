// 集成中心各服务的品牌 logo（真实 SVG 资源），按 service.key 取用
import prometheusLogo from '@/assets/integration-logos/prometheus.svg'
import alertmanagerLogo from '@/assets/integration-logos/alertmanager.svg'
import elasticsearchLogo from '@/assets/integration-logos/elasticsearch.svg'
import kibanaLogo from '@/assets/integration-logos/kibana.svg'
import jenkinsLogo from '@/assets/integration-logos/jenkins.svg'

const INTEGRATION_LOGOS: Record<string, string> = {
  prometheus: prometheusLogo,
  alertmanager: alertmanagerLogo,
  elasticsearch: elasticsearchLogo,
  kibana: kibanaLogo,
  jenkins: jenkinsLogo,
}

export function integrationLogoOf(key?: string): string | undefined {
  return key ? INTEGRATION_LOGOS[key] : undefined
}

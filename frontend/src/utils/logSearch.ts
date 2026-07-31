export interface LogHighlightSegment {
  text: string
  highlighted: boolean
}

export type HighlightedLogLine = LogHighlightSegment[]

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function normalizeLogKeyword(keyword: string): string {
  return keyword.trim().toLowerCase()
}

export function filterLogLines(logs: string, keyword: string): string {
  if (!logs || !keyword) return logs
  const matcher = new RegExp(escapeRegExp(keyword), 'i')
  return logs.split('\n').filter((line) => matcher.test(line)).join('\n')
}

export function highlightLogLines(logs: string, keyword: string): HighlightedLogLine[] {
  if (!logs || !keyword) return []

  const matcher = new RegExp(escapeRegExp(keyword), 'gi')
  return logs.split('\n').map((line) => {
    const segments: LogHighlightSegment[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null

    matcher.lastIndex = 0
    while ((match = matcher.exec(line))) {
      if (match.index > lastIndex) {
        segments.push({ text: line.slice(lastIndex, match.index), highlighted: false })
      }
      segments.push({ text: match[0], highlighted: true })
      lastIndex = match.index + match[0].length
    }

    if (lastIndex < line.length) {
      segments.push({ text: line.slice(lastIndex), highlighted: false })
    }
    return segments.length ? segments : [{ text: line, highlighted: false }]
  })
}

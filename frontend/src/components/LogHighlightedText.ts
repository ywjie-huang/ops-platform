import { defineComponent, h, type PropType, type VNodeChild } from 'vue'
import type { HighlightedLogLine } from '@/utils/logSearch'

export default defineComponent({
  name: 'LogHighlightedText',
  props: {
    lines: {
      type: Array as PropType<HighlightedLogLine[]>,
      required: true,
    },
  },
  setup(props) {
    return () => {
      const nodes: VNodeChild[] = []

      props.lines.forEach((line, lineIndex) => {
        line.forEach((segment, segmentIndex) => {
          if (segment.highlighted) {
            nodes.push(h('mark', {
              key: `${lineIndex}-${segmentIndex}`,
              class: 'log-keyword-match',
            }, segment.text))
          } else {
            nodes.push(segment.text)
          }
        })
        if (lineIndex < props.lines.length - 1) nodes.push('\n')
      })

      return nodes
    }
  },
})

<template>
  <span class="math-text" v-html="html"></span>
</template>

<script>
/**
 * 数学文本渲染组件（方案C：KaTeX）。
 *
 * 输入 OCR/手输的自由文本，把「17/2、x^2、\frac{}{}、\sqrt{}」等数学片段
 * 交给 KaTeX 渲染成真分式/上下标，其余内容原样保留（含换行，父容器需 pre-wrap）。
 *
 * 安全与降级：
 * - KaTeX 惰性加载（独立 chunk，主包不膨胀）；加载失败时保持纯文本显示
 * - 渲染异常的片段回退为原文本（.math-fallback），绝不整题白屏
 * - 先同步输出兜底 HTML，KaTeX 就绪后异步升级，不阻塞列表渲染
 * - 纯文本段做 HTML 转义，v-html 无注入风险
 *
 * 组卷 A4 打印（PaperPrintView）与本组件共用，打印效果同屏显。
 */
import { renderMathHtml } from '../utils/mathText'

export default {
  name: 'MathText',
  props: {
    text: { type: String, default: '' },
  },
  data() {
    return { html: '' }
  },
  watch: {
    text: { immediate: true, handler: 'render' },
  },
  beforeUnmount() {
    this._epoch = (this._epoch || 0) + 1 // 组件销毁后放弃未完成的异步升级
  },
  methods: {
    async render() {
      const epoch = (this._epoch = (this._epoch || 0) + 1)
      const { html, hasMath, upgrade } = renderMathHtml(this.text)
      this.html = html
      if (!hasMath || !upgrade) return
      try {
        const rich = await upgrade()
        if (epoch === this._epoch) this.html = rich
      } catch {
        /* KaTeX chunk 加载失败：保持兜底纯文本 */
      }
    },
  },
}
</script>

<style scoped>
.math-text {
  white-space: pre-wrap;
  word-break: break-word;
}

/* KaTeX 渲染失败的片段：等宽退回原文本，避免红色报错惊到孩子 */
.math-text :deep(.math-fallback) {
  font-family: var(--font-mono, monospace);
}

/* 分数与整行中轴对齐：分数线压在数字中线上，不下沉 */
.math-text :deep(.katex) {
  vertical-align: middle;
  /* KaTeX 默认 1.21em 是为衬线字体设计的，中文题干里会显得偏大，收到接近正文 */
  font-size: 1.08em;
}

.math-text :deep(.katex-display) {
  margin: 0;
  text-align: inherit;
}
</style>

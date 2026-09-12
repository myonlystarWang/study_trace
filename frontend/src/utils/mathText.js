/**
 * 数学文本分段与 LaTeX 化（供 MathText.vue 使用）。
 *
 * 设计目标：OCR/手输的自由文本里，把「分数 17/2、上标 x^2、\frac{}{}、\sqrt{}」
 * 这类数学片段识别出来交给 KaTeX 渲染，其余内容原样保留。
 * 原则：宁可漏渲染（退化为原文本），不可误渲染（日期/比分/题号被拆成分数）。
 */

// 单个数学 token：
//  1) 已是 LaTeX 的命令：\frac{a}{b}、\sqrt{2}、\pi、\times …（命令后可跟一组花括号参数）
//  2) 斜杠分数：17/2（分子/分母各 1~3 位数字）
//  3) 上标：x^2、10^-3、x^(2n-1)
const TOKEN_RE = new RegExp(
  [
    '\\\\[a-zA-Z]+\\s*(?:\\{[^{}]*\\})*', // LaTeX 命令（可带花括号参数）
    '([0-9]{1,3})/([0-9]{1,3})', // 斜杠分数（前面紧贴数字的情况在代码里排除，避免用 lookbehind 兼容旧 iOS Safari）
    '([0-9]+|[A-Za-z])\\^\\s*(\\([^)]*\\)|[-+]?[A-Za-z0-9]+)', // 上标（数字底数允许多位，如 10^-2）
  ].join('|'),
  'g',
)

// 分数黑名单：紧跟/前缀这些字样时视为日期、题号、比分等，不转分数
const FRAC_CTX_DENY = /[年月日时分秒页题号名楼第班次：%:]/i

function isSafeFraction(num, den, raw, index, len) {
  if (Number(den) === 0) return false // 分母 0 必假
  // 前后各看 2 个字符：「第 23/24 题」「用时 9/12 分钟」这类语境不转
  const before = raw.slice(Math.max(0, index - 2), index)
  const after = raw.slice(index + len, index + len + 2)
  if (/[0-9]/.test(before.slice(-1))) return false // 1234/5 只会匹配到 234/5 残串，直接放弃
  if (FRAC_CTX_DENY.test(before) || FRAC_CTX_DENY.test(after)) return false
  // 连续多段斜杠（2024/9/12 这类日期串）不转
  if (before.endsWith('/') || after.startsWith('/')) return false
  return true
}

function toSuperscriptTex(base, expRaw) {
  // x^(2n-1) → x^{2n-1}；x^2 → x^{2}；10^-3 → 10^{-3}
  let exp = expRaw.trim()
  if (exp.startsWith('(') && exp.endsWith(')')) exp = exp.slice(1, -1)
  if (!/^[-+]?[A-Za-z0-9]+$/.test(exp)) return null // 含其它符号则不转
  return `${base}^{${exp}}`
}

/**
 * 把自由文本切成 [{type:'text'|'math', value}] 段。
 * math 段的 value 是可直接喂给 KaTeX 的 LaTeX 源串。
 */
export function buildSegments(raw) {
  const out = []
  if (!raw) return out
  let last = 0
  TOKEN_RE.lastIndex = 0
  let m
  while ((m = TOKEN_RE.exec(raw)) !== null) {
    let tex = null
    if (m[0].startsWith('\\')) {
      tex = m[0].replace(/\s+/, '') // \frac {17}{2} → \frac{17}{2}
    } else if (m[1] !== undefined) {
      // 斜杠分数：过黑名单才转
      if (!isSafeFraction(m[1], m[2], raw, m.index, m[0].length)) continue
      tex = `\\frac{${m[1]}}{${m[2]}}`
    } else if (m[3] !== undefined) {
      tex = toSuperscriptTex(m[3], m[4])
      if (!tex) continue
    }
    if (!tex) continue
    if (m.index > last) out.push({ type: 'text', value: raw.slice(last, m.index) })
    out.push({ type: 'math', value: tex })
    last = m.index + m[0].length
  }
  if (last < raw.length) out.push({ type: 'text', value: raw.slice(last) })
  return out
}

export function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// KaTeX 惰性加载：主包不膨胀，首次遇到数学片段才拉取独立 chunk
let katexPromise = null
function loadKatex() {
  if (!katexPromise) katexPromise = import('katex').then((m) => m.default || m)
  return katexPromise
}

/**
 * 渲染为 HTML 字符串（同步返回兜底版；KaTeX 就绪后通过 onReady 回调升级）。
 * 返回 { html, hasMath, upgrade } —— upgrade() 为 null 表示无需升级。
 */
export function renderMathHtml(raw) {
  const segs = buildSegments(raw || '')
  if (segs.length === 0) return { html: '', hasMath: false, upgrade: null }
  const hasMath = segs.some((s) => s.type === 'math')
  const plain = segs.map((s) => escapeHtml(s.value)).join('')
  if (!hasMath) return { html: plain, hasMath: false, upgrade: null }

  const upgrade = async () => {
    const katex = await loadKatex()
    return segs
      .map((s) => {
        if (s.type !== 'math') return escapeHtml(s.value)
        try {
          return katex.renderToString(s.value, { throwOnError: true, strict: false })
        } catch {
          return `<span class="math-fallback">${escapeHtml(s.value)}</span>`
        }
      })
      .join('')
  }
  return { html: plain, hasMath: true, upgrade }
}

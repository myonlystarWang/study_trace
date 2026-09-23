/**
 * 数学文本分段与 LaTeX 化（供 MathText.vue 使用）。
 *
 * 设计目标：OCR/手输的自由文本里，把「分数 17/2、上标 x^2、\frac{}{}、\sqrt{}」
 * 这类数学片段识别出来交给 KaTeX 渲染，其余内容原样保留。
 * 原则：宁可漏渲染（退化为可读文本），不可误渲染（日期/比分/题号被拆成分数）。
 *
 * 三层防线（对应 OCR 输出风格不稳定的现实）：
 * 1. normalizeMathSource —— 剥掉 $…$、\( \) 这类定界符与纯排版命令，
 *    历史脏数据（如库里已存的 `\(|-\frac{5}{2}|\)`）也能就地洗干净；
 * 2. buildSegments —— 挑出可渲染的数学片段（含 ^{...} 带花括号上标）；
 * 3. texToReadable —— KaTeX 渲染失败时降级成「看得懂的文字」，
 *    绝不再把 \frac{1}{2} 这种源码直接摊给孩子看。
 */

const SIMPLE_EXPR_RE = '[A-Za-z0-9]+(?:[+\\-*/][A-Za-z0-9]+)*'
const PAREN_BASE_RE = `[（(](?:[^{}()（）\\r\\n]|\\{[^{}]*\\})+[）)]`

// 单个数学 token：
//  1) 上标：优先匹配带底数的幂（支持字母连写与中英文括号底数，含括号内含分数/负数如 (-\frac{3}{2})^2、(cd)^2027）
//  2) 已是 LaTeX 的命令：\frac{a}{b}、\sqrt{2}、\pi、\times …（命令后可跟一组花括号参数）
//  3) 斜杠分数：17/2（分子/分母各 1~3 位数字）
const TOKEN_RE = new RegExp(
  [
    `([0-9]+|[A-Za-z]+|${PAREN_BASE_RE})\\^\\s*(\\{[^{}]*\\}|\\([^)]*\\)|[-+]?[A-Za-z0-9]+)`, // 上标（优先匹配，避免被 \frac 拆碎）
    '\\\\[a-zA-Z]+\\s*(?:\\{[^{}]*\\})*', // LaTeX 命令（可带花括号参数）
    '([0-9]{1,3})/([0-9]{1,3})', // 斜杠分数（前面紧贴数字的情况在代码里排除，避免用 lookbehind 兼容旧 iOS Safari）
  ].join('|'),
  'g',
)

// 手机键盘、OCR 与聊天复制常把指数写为 Unicode 上标；先归一为 ^，再走同一渲染链路。
const UNICODE_SUPERSCRIPT_RE = new RegExp(`(${PAREN_BASE_RE}|[0-9A-Za-z]+)([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)`, 'g')
const UNICODE_SUPERSCRIPT_MAP = {
  '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
  '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
  '⁺': '+', '⁻': '-',
}

// 分数黑名单：紧跟/前缀这些字样时视为日期、题号、比分等，不转分数
const FRAC_CTX_DENY = /[年月日时分秒页题号名楼第班次：%:]/i

// 尺寸/排版命令：只影响 KaTeX 排版，去掉不影响语义
const LAYOUT_CMDS = [
  'left', 'right',
  'bigl', 'bigr', 'Bigl', 'Bigr', 'bigg', 'Bigg', 'big', 'Big',
  'displaystyle', 'textstyle', 'limits', 'nolimits',
]

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
  // x^2 → x^{2}；（cd）^2027 → (cd)^{2027}；x^(2n-1) → x^{2n-1}
  let exp = expRaw.trim()
  if (exp.startsWith('{') && exp.endsWith('}')) exp = exp.slice(1, -1)
  if (exp.startsWith('(') && exp.endsWith(')')) exp = exp.slice(1, -1)
  if (!new RegExp(`^${SIMPLE_EXPR_RE}$`).test(exp)) return null // 含其它符号则不转
  return `${base.replace(/[（]/g, '(').replace(/[）]/g, ')')}^{${exp}}`
}

function normalizeUnicodeSuperscripts(s) {
  return s.replace(UNICODE_SUPERSCRIPT_RE, (_, base, superscript) => {
    const exponent = [...superscript].map((ch) => UNICODE_SUPERSCRIPT_MAP[ch] || ch).join('')
    return `${base.replace(/[（]/g, '(').replace(/[）]/g, ')')}^${exponent}`
  })
}

/**
 * 清洗 OCR/手输文本里的 LaTeX 定界符与纯排版命令。
 *
 * 云端视觉模型会自由选择输出风格：纯文本 / 裸 LaTeX / 带定界符的 LaTeX。
 * 定界符（$、$$、\(、\)、\[、\]）不是本渲染器的数学边界，不剥掉就会作为
 * 可见字符留在题干里（孩子会看到「$」「\」）。后端入库前已清洗一遍，
 * 这里再兜一次，保证历史记录与手工粘贴的内容同样干净。
 */
export function normalizeMathSource(raw) {
  if (!raw) return ''
  let s = String(raw)

  // 换行命令 \\ 还原成真实换行（必须在清理反斜杠之前）
  s = s.replace(/\\\\/g, '\n')
  // 转义字面符号
  s = s.replace(/\\\{/g, '{').replace(/\\\}/g, '}')
    .replace(/\\_/g, '_').replace(/\\%/g, '%')
    .replace(/\\&/g, '&').replace(/\\#/g, '#')
    .replace(/\\\$/g, '')
    .replace(/\\(?:,|;|:|!| )/g, ' ')
  // 定界符：只删符号本身，内容原样保留
  s = s.replace(/\$\$/g, '').replace(/\$/g, '')
  s = s.replace(/\\\[/g, '').replace(/\\\]/g, '')
  s = s.replace(/\\\(/g, '').replace(/\\\)/g, '')
  // \text{...} / \mathrm{...} 这类「内容即正文」的包装只留内容
  s = s.replace(/\\(?:text|mathrm|mathbf|mathit|mathbb|mathcal|operatorname)\s*\{([^{}]*)\}/g, '$1')
  // 尺寸/排版命令与空白命令
  LAYOUT_CMDS.forEach((cmd) => { s = s.replace(new RegExp('\\\\' + cmd + '(?![a-zA-Z])', 'g'), '') })
  s = s.replace(/\\(?:quad|qquad|enspace|thinspace|medspace|thickspace)(?![a-zA-Z])/g, ' ')
  s = normalizeUnicodeSuperscripts(s)

  return s
}

/**
 * 把自由文本切成 [{type:'text'|'math', value}] 段。
 * math 段的 value 是可直接喂给 KaTeX 的 LaTeX 源串。
 */
export function buildSegments(raw) {
  const out = []
  const source = normalizeMathSource(raw)
  if (!source) return out
  let last = 0
  TOKEN_RE.lastIndex = 0
  let m
  while ((m = TOKEN_RE.exec(source)) !== null) {
    let tex = null
    if (m[1] !== undefined) {
      tex = toSuperscriptTex(m[1], m[2])
      if (!tex) continue
    } else if (m[0].startsWith('\\')) {
      tex = m[0].replace(/\s+/, '') // \frac {17}{2} → \frac{17}{2}
    } else if (m[3] !== undefined) {
      // 斜杠分数：过黑名单才转
      if (!isSafeFraction(m[3], m[4], source, m.index, m[0].length)) continue
      tex = `\\frac{${m[3]}}{${m[4]}}`
    }
    if (!tex) continue
    if (m.index > last) out.push({ type: 'text', value: source.slice(last, m.index) })
    out.push({ type: 'math', value: tex })
    last = m.index + m[0].length
  }
  if (last < source.length) out.push({ type: 'text', value: source.slice(last) })
  return out
}

export function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function replaceCmd(s, name, ch) {
  return s.replace(new RegExp('\\\\' + name + '(?![a-zA-Z])', 'g'), ch)
}

/**
 * KaTeX 渲染失败时的降级：把 LaTeX 转成「看得懂的中文数学写法」。
 *
 * 为什么不直接显示源码：`\begin{cases}` / `\left` 缺配对等情况会让 KaTeX 抛错，
 * 此时把 `\frac{1}{2}` 摊给孩子看毫无意义，不如退成 `(1)/(2)`。
 */
export function texToReadable(tex) {
  let s = String(tex || '')
  s = s.replace(/\\begin\{[^}]*\}/g, '').replace(/\\end\{[^}]*\}/g, '')
  s = s.replace(/\\(?:d|t|c)?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, '($1)/($2)')
  s = s.replace(/\\sqrt\s*\{([^{}]*)\}/g, '√($1)')
  s = s.replace(/\^\{([^{}]*)\}/g, '^$1')
  const sym = {
    times: '×', div: '÷', cdot: '·', pm: '±', mp: '∓',
    leq: '≤', le: '≤', geq: '≥', ge: '≥', neq: '≠', ne: '≠',
    angle: '∠', triangle: '△', parallel: '∥', perp: '⊥',
    pi: 'π', alpha: 'α', beta: 'β', gamma: 'γ', theta: 'θ',
    lambda: 'λ', mu: 'μ', sigma: 'σ', omega: 'ω', Delta: 'Δ',
    infty: '∞', degree: '°',
  }
  Object.keys(sym).forEach((k) => { s = replaceCmd(s, k, sym[k]) })
  s = s.replace(/[{}]/g, '')
  s = s.replace(/\\/g, '')
  return s.trim()
}

// KaTeX 惰性加载：主包不膨胀，首次遇到数学片段才拉取独立 chunk
let katexPromise = null
function loadKatex() {
  if (!katexPromise) katexPromise = import('katex').then((m) => m.default || m)
  return katexPromise
}

/**
 * 渲染为 HTML 字符串（同步返回兜底版；KaTeX 就绪后通过 upgrade 回调升级）。
 * 返回 { html, hasMath, upgrade } —— upgrade() 为 null 表示无需升级。
 */
export function renderMathHtml(raw) {
  const segs = buildSegments(raw || '')
  if (segs.length === 0) return { html: '', hasMath: false, upgrade: null }
  const hasMath = segs.some((s) => s.type === 'math')
  // KaTeX 就绪前的兜底版同样不暴露 LaTeX 源码，避免首帧闪出「\frac」
  const plain = segs
    .map((s) => escapeHtml(s.type === 'math' ? texToReadable(s.value) : s.value))
    .join('')
  if (!hasMath) return { html: plain, hasMath: false, upgrade: null }

  const upgrade = async () => {
    const katex = await loadKatex()
    return segs
      .map((s) => {
        if (s.type !== 'math') return escapeHtml(s.value)
        try {
          return katex.renderToString(s.value, { throwOnError: true, strict: false })
        } catch {
          // 渲染失败：退成可读数学写法，不留 LaTeX 源码
          return `<span class="math-fallback">${escapeHtml(texToReadable(s.value))}</span>`
        }
      })
      .join('')
  }
  return { html: plain, hasMath: true, upgrade }
}

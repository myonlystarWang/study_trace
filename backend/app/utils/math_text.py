"""数学文本规范化：把 OCR 产出的 LaTeX 变回「前端渲染器吃得下」的干净文本。

为什么需要它
------------
云端视觉模型（glm-4v-flash 等）输出风格不稳定，同一张数学题照片可能给出三种形态：

1. 纯文本          ``x = (-b + sqrt(b^2-4ac)) / 2a``
2. 裸 LaTeX 片段   ``\\sqrt{18} - 3\\sqrt{2} + \\frac{1}{2}``
3. 带定界符的 LaTeX ``\\(|-\\frac{5}{2}|\\)``、``$\\frac{2}{x}=1$``

前端 ``MathText`` 只认「裸 LaTeX 片段」，定界符（``$``、``$$``、``\\(``、``\\)``、``\\[``、``\\]``）
不会被识别成数学边界，于是作为可见字符残留在题干里 —— 孩子会看到「$」「\\」。
这里在**入库之前**统一剥掉定界符、清理纯排版命令、并让真正无法渲染的命令
至少不裸露反斜杠，保证错题卡片、编辑框、复习卷打印三处都是干净的。
"""

from __future__ import annotations

import re

# 尺寸/排版类命令：只是给 KaTeX 看的，去掉不影响语义（\left| → |、\displaystyle → 空）
_LAYOUT_CMDS = (
    "left",
    "right",
    "big",
    "Big",
    "bigg",
    "Bigg",
    "bigl",
    "bigr",
    "Bigl",
    "Bigr",
    "displaystyle",
    "textstyle",
    "scriptstyle",
    "scriptscriptstyle",
    "limits",
    "nolimits",
)

# 带花括号参数、但内容本身就是正文的命令：\text{厘米} → 厘米
_TEXT_WRAPPER_CMDS = ("text", "mathrm", "mathbf", "mathit", "mathbb", "mathcal", "operatorname")

# 空白类命令：替换成普通空格
_SPACE_CMDS = (
    "quad",
    "qquad",
    "hspace",
    "enspace",
    "thinspace",
    "medspace",
    "thickspace",
    "negthinspace",
)

# KaTeX 能渲染、且初中数学题干里会出现的命令（保留，绝不剥掉反斜杠）
_KATEX_KEEP = {
    # 分式与根式
    "frac", "dfrac", "tfrac", "cfrac", "sqrt", "binom", "choose",
    # 运算与关系
    "times", "div", "cdot", "pm", "mp", "ast", "star", "circ", "bullet",
    "le", "leq", "ge", "geq", "ne", "neq", "lt", "gt", "equiv", "approx", "sim", "simeq", "cong",
    "propto", "because", "therefore", "implies", "iff", "land", "lor", "neg", "forall", "exists",
    # 几何与集合
    "angle", "measuredangle", "degree", "triangle", "square", "parallel", "nparallel", "perp",
    "in", "notin", "subset", "subseteq", "supset", "cup", "cap", "emptyset", "varnothing", "mid",
    "lfloor", "rfloor", "lceil", "rceil", "langle", "rangle", "vert", "Vert",
    # 微积分/数列（初中偶见）
    "sum", "prod", "int", "infty", "lim", "partial", "nabla",
    # 函数与对数
    "log", "ln", "lg", "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan",
    # 希腊字母
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta", "theta", "vartheta",
    "iota", "kappa", "lambda", "mu", "nu", "xi", "rho", "sigma", "tau", "upsilon", "phi", "varphi",
    "chi", "psi", "omega", "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi", "Omega",
    # 箭头
    "to", "mapsto", "leftarrow", "rightarrow", "leftrightarrow", "uparrow", "downarrow", "updownarrow",
    "Leftarrow", "Rightarrow", "Leftrightarrow", "longleftarrow", "longrightarrow", "longleftrightarrow",
    # 修饰
    "overline", "underline", "vec", "bar", "hat", "tilde", "widehat", "widetilde", "dot", "ddot",
    "overset", "underset", "stackrel", "boxed", "prime", "backprime", "pmod", "bmod", "mod",
    # 省略号
    "dots", "ldots", "cdots", "vdots", "ddots", "dotsb", "dotsc",
    # 环境（\begin{cases} 等靠前端 KaTeX 兜底）
    "begin", "end",
}

# 转义的字面符号：剥掉反斜杠、留下符号本身
_ESCAPED_LITERALS = {
    "\\{": "{",
    "\\}": "}",
    "\\_": "_",
    "\\%": "%",
    "\\&": "&",
    "\\#": "#",
    "\\$": "",
    "\\ ": " ",
    "\\,": " ",
    "\\;": " ",
    "\\:": " ",
    "\\!": "",
}

# 剩余的反斜杠命令：保留白名单，其余只留命令名（不让「\」露给孩子看）
_CMD_RE = re.compile(r"\\([a-zA-Z]+)")

# 手机键盘、OCR 与聊天复制常使用 Unicode 上标（m²、x⁻²）；统一成前端
# MathText 与 KaTeX 都能稳定处理的 ^ 写法。只转换 ASCII 数学底数，避免误伤中文正文。
_UNICODE_SUPERSCRIPT_RE = re.compile(
    r"([A-Za-z0-9]+|[（(][A-Za-z0-9]+(?:[+\-*/][A-Za-z0-9]+)*[）)])([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)"
)
_UNICODE_SUPERSCRIPT_MAP = str.maketrans({
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "-",
})


def _normalize_unicode_superscripts(text: str) -> str:
    """将 OCR 常见的 Unicode 上标统一为 ^，供前端 KaTeX 稳定渲染。"""
    def _replace(match: re.Match) -> str:
        base = match.group(1).replace("（", "(").replace("）", ")")
        return f"{base}^{match.group(2).translate(_UNICODE_SUPERSCRIPT_MAP)}"

    return _UNICODE_SUPERSCRIPT_RE.sub(_replace, text)


def _strip_wrappers(text: str) -> str:
    """把 \\text{...} 这类「内容即正文」的包装剥掉，保留花括号内的内容。"""
    for cmd in _TEXT_WRAPPER_CMDS:
        pattern = re.compile(r"\\" + cmd + r"\s*\{([^{}]*)\}")
        prev = None
        while prev != text:  # 允许嵌套，反复收敛
            prev = text
            text = pattern.sub(r"\1", text)
    return text


def normalize_math_text(text: str | None) -> str:
    """清洗 OCR 输出的数学文本，返回可直接入库/渲染的纯文本。

    幂等：重复调用结果不变。
    """
    if not text:
        return ""

    out = text

    # 1) 换行命令 \\ 还原成真实换行（必须在清理反斜杠之前做）
    out = out.replace("\\\\", "\n")

    # 2) 转义字面符号（\$ 直接丢弃，题干里没有合法的美元符号语义）
    for src, dst in _ESCAPED_LITERALS.items():
        out = out.replace(src, dst)

    # 3) 定界符：$$…$$ / $…$ / \( \) / \[ \] 全部剥掉，只留内部内容
    out = out.replace("$$", "")
    out = out.replace("\\[", "").replace("\\]", "")
    out = out.replace("\\(", "").replace("\\)", "")
    out = out.replace("$", "")

    # 4) 正文包装命令
    out = _strip_wrappers(out)

    # 5) 尺寸/排版命令与空白命令
    for cmd in _LAYOUT_CMDS:
        out = re.sub(r"\\" + cmd + r"(?![a-zA-Z])", "", out)
    for cmd in _SPACE_CMDS:
        out = re.sub(r"\\" + cmd + r"(?![a-zA-Z])", " ", out)

    # 5.1) OCR / 手机输入的 Unicode 上标统一成 ^ 形式
    out = _normalize_unicode_superscripts(out)

    # 6) 白名单之外的反斜杠命令：只丢反斜杠，命令名留作普通文字，避免裸「\」进入题干
    def _keep_or_strip(m: re.Match) -> str:
        name = m.group(1)
        return m.group(0) if name in _KATEX_KEEP else name

    out = _CMD_RE.sub(_keep_or_strip, out)

    # 7) 收敛空白：行内多余空格压成一个，行首行尾去空；保留换行结构
    lines = [re.sub(r"[ \t\u3000]{2,}", " ", ln).strip() for ln in out.split("\n")]
    return "\n".join(lines).strip()

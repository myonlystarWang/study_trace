/**
 * 作业文本智能解析引擎 (StudyTrace Homework Parser)
 * 支持识别常见微信群通知、Markdown列表符号 (*, -, •)、跨学科批量布置、行内多序号拆分等。
 */

export const DEFAULT_FALLBACK_SUBJECTS = [
  { id: 2, name: '语文', is_default: true },
  { id: 1, name: '数学', is_default: true },
  { id: 3, name: '英语', is_default: true },
  { id: 4, name: '道法', is_default: true },
  { id: 5, name: '历史', is_default: true },
  { id: 6, name: '地理', is_default: true },
  { id: 7, name: '生物', is_default: true },
  { id: 8, name: '物理', is_default: true },
  { id: 9, name: '化学', is_default: true }
];

export const aliasGroups = [
  ['语文', '国文'],
  ['数学'],
  ['英语', '英文', '外语'],
  ['道德与法治', '道法', '政治', '思想品德', '思品'],
  ['历史'],
  ['地理'],
  ['生物', '生物学'],
  ['物理'],
  ['化学'],
  ['科学']
];

/**
 * 为学科获取全部同义词与别名列表
 */
export const getAliasesForSubject = (subjectName) => {
  const clean = (subjectName || '').trim();
  for (const group of aliasGroups) {
    if (group.includes(clean) || group.some((alias) => clean.includes(alias) || alias.includes(clean))) {
      return Array.from(new Set([...group, clean]));
    }
  }
  return [clean];
};

/**
 * 清理单条作业文字（去除前缀序号、列表符，支持多重前缀如 "* 1."）
 */
export const cleanTaskContent = (content) => {
  if (!content) return '';
  let cleaned = content.trim();
  const prefixRegex = /^(?:(?:[①-⑩\d]+[\.、\)\s\-]+|\([①-⑩\d]+\)|（[①-⑩\d]+）|[一二三四五六七八九十]+[、\.]|[-*•·\+\■◆▲●✦★✓✔○◇□△☆✧➢➤])\s*)+/;
  cleaned = cleaned.replace(prefixRegex, '').trim();
  return cleaned;
};

/**
 * 智能拆解同一行内包含的多个递增序号子项
 * 例如："1. 发的作文题 2. 在发的四线三格上写自己字帖的内容。"
 * -> ["发的作文题", "在发的四线三格上写自己字帖的内容。"]
 *
 * 对于非列表连续内容（如 "P20 1, 3, 4, 5 P21 10" 或 "订练习册 P33~P43"），保持原样不拆分。
 */
export const splitInlineItems = (text) => {
  const t = (text || '').trim();
  if (!t) return [];

  const markerPattern = /(?:^|[\s;；。，,\n])(?:(\d+)[\.、\)]|\(([①-⑩\d]+)\)|（([①-⑩\d]+)）|([①-⑩]))\s*/g;
  const matches = [];
  let m;
  while ((m = markerPattern.exec(t)) !== null) {
    matches.push({
      index: m.index,
      lastIndex: markerPattern.lastIndex,
      groups: [m[1], m[2], m[3], m[4]]
    });
  }

  if (matches.length < 2) {
    const cleaned = cleanTaskContent(t);
    return cleaned ? [cleaned] : [];
  }

  const circ = '①②③④⑤⑥⑦⑧⑨⑩';
  const parseNum = (match) => {
    for (const g of match.groups) {
      if (g !== undefined) {
        if (/^\d+$/.test(g)) return parseInt(g, 10);
        const idx = circ.indexOf(g);
        if (idx !== -1) return idx + 1;
      }
    }
    return null;
  };

  const nums = matches.map(parseNum);
  if (nums.some((n) => n === null)) {
    const cleaned = cleanTaskContent(t);
    return cleaned ? [cleaned] : [];
  }

  const isSequential = nums.every((n, i) => i === 0 || n === nums[i - 1] + 1);
  if (!isSequential || (nums[0] !== 1 && nums[0] !== 2)) {
    const cleaned = cleanTaskContent(t);
    return cleaned ? [cleaned] : [];
  }

  const results = [];
  for (let i = 0; i < matches.length; i++) {
    const start = matches[i].lastIndex;
    const end = (i + 1 < matches.length) ? matches[i + 1].index : t.length;
    let sub = t.slice(start, end).trim();
    sub = sub.replace(/[;；,\s]+$/, '');
    sub = cleanTaskContent(sub);
    if (sub) {
      results.push(sub);
    }
  }

  return results.length > 0 ? results : ([cleanTaskContent(t)].filter(Boolean));
};

/**
 * 判断是否为纯杂质通知行（日期、标题、问候等）
 */
export const isNoiseLine = (line) => {
  const trimmed = line.trim();
  if (!trimmed) return true;
  if (/^\d{1,2}月\d{1,2}日.*$/.test(trimmed)) return true;
  if (/^\d{4}[年\-\/]\d{1,2}[月\-\/]\d{1,2}.*$/.test(trimmed)) return true;
  if (/^[【\[（(「『《]?(今日作业|作业布置|家庭作业|各科作业|作业清单|作业是|作业如下|今日任务|作业)[】\]）)」』》]?[:：\s]*$/.test(trimmed)) return true;
  if (/^(大家好|各位家长|请各位家长|请家长|各位同学|收到请回复|家长您好|温馨提示).*$/.test(trimmed)) return true;
  return false;
};

const escapeRegex = (s) => s.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');

/**
 * 识别行首学科标记，支持列表前缀 (*, -, •, 1., ①, 一、 等) 和各种括号
 */
export const matchSubjectHeader = (line, subjectsList) => {
  const trimmed = line.trim();
  if (!trimmed) return null;

  const prefixPat = '(?:[\\s*•·\\-\\+■◆▲●✦★✓✔○◇□△☆✧➢➤]|\\d+[\\.、\\)]|[①-⑩]|\\([①-⑩\\d]+\\)|（[①-⑩\\d]+）|[一二三四五六七八九十]+[、\\.]|【\\d+】|\\[\\d+\\])*[【\\[（(「『《]?';
  const suffixPat = '[】\\]）)「』》]?';

  for (const sub of subjectsList) {
    const aliases = getAliasesForSubject(sub.name);
    for (const alias of aliases) {
      const esc = escapeRegex(alias);

      // 1. 冒号分隔：* 语文：作业 或 * 语文:
      const colonRegex = new RegExp(`^${prefixPat}(${esc})${suffixPat}\\s*[:：]\\s*(.*)$`);
      const m1 = trimmed.match(colonRegex);
      if (m1) {
        return {
          subject: sub,
          remainder: m1[2] ? m1[2].trim() : ''
        };
      }

      // 2. 独占一行的学科名：* 语文 / 【语文】 / 1. 语文 / 语文
      const exactRegex = new RegExp(`^${prefixPat}(${esc})${suffixPat}\\s*[:：]?$`);
      if (exactRegex.test(trimmed)) {
        return {
          subject: sub,
          remainder: ''
        };
      }

      // 3. 空格分隔学科名与作业：* 语文 第5课词语
      const spaceRegex = new RegExp(`^${prefixPat}(${esc})${suffixPat}\\s+(.*)$`);
      const m3 = trimmed.match(spaceRegex);
      if (m3 && m3[2].trim()) {
        return {
          subject: sub,
          remainder: m3[2].trim()
        };
      }
    }
  }

  return null;
};

/**
 * 核心智能多学科作业拆解
 */
export const parseHomeworkText = (text, subjectsList) => {
  const cleanInput = (text || '')
    .replace(/[\u00a0\u3000]/g, ' ')
    .replace(/\r\n/g, '\n');
  const rawLines = cleanInput.split('\n').map((l) => l.trim()).filter(Boolean);
  if (rawLines.length === 0) {
    return { groups: [], unassigned: [] };
  }

  const list = (subjectsList && subjectsList.length > 0) ? subjectsList : DEFAULT_FALLBACK_SUBJECTS;
  const groupsMap = new Map();
  const unassigned = [];
  let currentSubject = null;
  let detectedSubjectCount = 0;

  for (const line of rawLines) {
    if (isNoiseLine(line)) continue;

    const matched = matchSubjectHeader(line, list);
    if (matched) {
      currentSubject = matched.subject;
      if (!groupsMap.has(currentSubject.id)) {
        groupsMap.set(currentSubject.id, {
          subject: currentSubject,
          items: []
        });
        detectedSubjectCount++;
      }
      if (matched.remainder) {
        const splitItems = splitInlineItems(matched.remainder);
        for (const item of splitItems) {
          groupsMap.get(currentSubject.id).items.push(item);
        }
      }
    } else {
      if (currentSubject) {
        const splitItems = splitInlineItems(line);
        for (const item of splitItems) {
          groupsMap.get(currentSubject.id).items.push(item);
        }
      } else {
        const cleaned = cleanTaskContent(line);
        if (cleaned) {
          unassigned.push(cleaned);
        }
      }
    }
  }

  const groups = Array.from(groupsMap.values()).filter((g) => g.items.length > 0);
  if (detectedSubjectCount >= 1 && groups.length > 0) {
    return { groups, unassigned };
  }
  return { groups: [], unassigned: [] };
};

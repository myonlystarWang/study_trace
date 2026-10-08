/**
 * 智能成绩文本解析工具
 * 从微信群、短信或学校通知等大段文本中，自动结构化提取：
 * 1. 考试标题 (title) & 考试类型 (exam_type)
 * 2. 考试日期 (exam_date, 格式: YYYY-MM-DD)
 * 3. 班级排名 (class_rank) & 年级/校排名 (grade_rank)
 * 4. 各科目成绩明细 (学科名、实得分数、满分、是否缺考)
 */

// 常见学科同义词/别名映射表（按匹配优先级由长到短排列）
const SUBJECT_ALIASES = [
  { standard: '道德与法治', aliases: ['道德与法治', '道法', '政治', '思想品德', '思品'] },
  { standard: '信息技术', aliases: ['信息技术', '信息', '计算机', '微机'] },
  { standard: '生物', aliases: ['生物学', '生物'] },
  { standard: '语文', aliases: ['语文', '国文'] },
  { standard: '数学', aliases: ['数学'] },
  { standard: '英语', aliases: ['英语', '外语', '英文'] },
  { standard: '历史', aliases: ['历史'] },
  { standard: '地理', aliases: ['地理'] },
  { standard: '物理', aliases: ['物理'] },
  { standard: '化学', aliases: ['化学'] },
  { standard: '科学', aliases: ['科学'] },
  { standard: '体育', aliases: ['体育与健康', '体育'] },
  { standard: '音乐', aliases: ['音乐'] },
  { standard: '美术', aliases: ['美术'] }
];

export function parseScoreText(rawText, existingSubjects = []) {
  if (!rawText || typeof rawText !== 'string' || !rawText.trim()) {
    return null;
  }

  const text = rawText.trim();
  const result = {
    title: '',
    exam_type: '期中',
    exam_date: null,
    class_rank: null,
    grade_rank: null,
    remarks: '',
    parsedScores: [], // [{ subject_id, subject_name, score, full_score, is_absent }]
    matchedCount: 0
  };

  // 1. 考试类型与标题推断
  if (/期末/i.test(text)) {
    result.exam_type = '期末';
  } else if (/期中/i.test(text)) {
    result.exam_type = '期中';
  } else if (/月考/i.test(text)) {
    result.exam_type = '月考';
  } else if (/周测|周考/i.test(text)) {
    result.exam_type = '周测';
  } else if (/单元/i.test(text)) {
    result.exam_type = '单元测试';
  }

  // 提取更具体的考试标题短语
  const titlePatterns = [
    /([^\n，,。；;]{2,20}?(?:第[一二三四五12345]次月考|期中考试|期末考试|月度测试|模拟考|阶段检测|阶段测试|周考|周测|单元测试|月考|考试))/i,
    /(?:【|\[)([^\]】]+考试[^\]】]*)(?:】|\])/i
  ];
  for (const pat of titlePatterns) {
    const match = text.match(pat);
    if (match && match[1]) {
      let cleanTitle = match[1]
        .replace(/^(本次|关于|通知|各位家长[，,]?)/, '')
        .replace(/[：:，,。；;]$/, '')
        .trim();
      if (cleanTitle.length >= 2 && cleanTitle.length <= 30) {
        result.title = cleanTitle;
        break;
      }
    }
  }
  if (!result.title) {
    const now = new Date();
    result.title = `${now.getFullYear()}年${result.exam_type}考试`;
  }

  // 2. 日期提取 (YYYY-MM-DD 或 YYYY年M月D日 或 M月D日)
  const datePatterns = [
    /(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/,
    /(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?/,
    /(\d{1,2})\s*月\s*(\d{1,2})\s*日?/
  ];
  for (const pat of datePatterns) {
    const dMatch = text.match(pat);
    if (dMatch) {
      const currentYear = new Date().getFullYear();
      let y = dMatch.length === 4 ? parseInt(dMatch[1], 10) : currentYear;
      let m = dMatch.length === 4 ? parseInt(dMatch[2], 10) : parseInt(dMatch[1], 10);
      let d = dMatch.length === 4 ? parseInt(dMatch[3], 10) : parseInt(dMatch[2], 10);
      if (m >= 1 && m <= 12 && d >= 1 && d <= 31) {
        const mm = String(m).padStart(2, '0');
        const dd = String(d).padStart(2, '0');
        result.exam_date = `${y}-${mm}-${dd}`;
        break;
      }
    }
  }

  // 3. 班级排名提取 (支持 班排第3名、班级排名: 5、班级第2名 等)
  const classRankMatch = text.match(/(?:班级排名|班排|班级第|班级名次|班次)[：:\s]*第?(\d+)/i) ||
                         text.match(/班级[^\d\n]{0,6}?第?(\d+)\s*(?:名|位)?/);
  if (classRankMatch && classRankMatch[1]) {
    const r = parseInt(classRankMatch[1], 10);
    if (r > 0 && r < 1000) result.class_rank = r;
  }

  // 4. 年级/校排名提取 (支持 校排第18名、年级第15、年级排名: 28 等)
  const gradeRankMatch = text.match(/(?:年级排名|校排|校排名|年级第|年排|年级名次|校次)[：:\s]*第?(\d+)/i) ||
                         text.match(/年级[^\d\n]{0,6}?第?(\d+)\s*(?:名|位)?/);
  if (gradeRankMatch && gradeRankMatch[1]) {
    const r = parseInt(gradeRankMatch[1], 10);
    if (r > 0 && r < 10000) result.grade_rank = r;
  }

  // 5. 科目与分数/满分/缺考/排名 提取
  const parsedSubjects = new Map();
  const subjectWindows = []; // { standard, start, end } 用于内联排名归属
  let maxInlineRankEnd = 0; // 最后一个单科内联排名的结束位置，之后的排名才算考试级（总分）排名

  // 找到 text 中 fromIndex 之后下一个学科别名出现的位置（排除当前科目自身别名）
  const findNextSubjectIndex = (fromIndex, excludeAliases) => {
    let boundary = text.length;
    for (const { aliases } of SUBJECT_ALIASES) {
      for (const a of aliases) {
        if (excludeAliases.includes(a)) continue;
        const idx = text.indexOf(a, fromIndex);
        if (idx !== -1 && idx < boundary) boundary = idx;
      }
    }
    return boundary;
  };

  SUBJECT_ALIASES.forEach(({ standard, aliases }) => {
    // 匹配现有系统中的学科配置（优先标准名或别名）
    const matchedSubject = existingSubjects.find(s =>
      aliases.includes(s.name) || s.name === standard || aliases.some(a => s.name.includes(a))
    );

    for (const alias of aliases) {
      // 缺考匹配: 学科[：:\s]*(缺考|未考|弃考)
      const absentReg = new RegExp(`(?:^|[^a-zA-Z0-9\u4e00-\u9fa5])${alias}[：:\\s]*(缺考|未考|弃考)`, 'i');
      if (absentReg.test(text)) {
        const m = text.match(absentReg);
        parsedSubjects.set(standard, {
          subject_name: matchedSubject ? matchedSubject.name : standard,
          subject_id: matchedSubject ? matchedSubject.id : null,
          score: null,
          full_score: matchedSubject?.full_score || (['语文', '数学', '英语'].includes(standard) ? 120 : 100),
          is_absent: true
        });
        subjectWindows.push({ standard, start: m.index, end: findNextSubjectIndex(m.index, aliases) });
        break;
      }

      // 带满分格式: 语文: 108/120 或 语文108/120分 或 语文 108 / 120
      const scoreWithFullReg = new RegExp(
        `(?:^|[^a-zA-Z0-9\u4e00-\u9fa5])${alias}[：:\\s]*([0-9]+(?:\\.[0-9]+)?)\\s*[/／]\\s*([0-9]+(?:\\.[0-9]+)?)`,
        'i'
      );
      const mWithFull = text.match(scoreWithFullReg);
      if (mWithFull) {
        const sc = parseFloat(mWithFull[1]);
        const full = parseFloat(mWithFull[2]);
        parsedSubjects.set(standard, {
          subject_name: matchedSubject ? matchedSubject.name : standard,
          subject_id: matchedSubject ? matchedSubject.id : null,
          score: sc,
          full_score: full,
          is_absent: false
        });
        subjectWindows.push({ standard, start: mWithFull.index, end: findNextSubjectIndex(mWithFull.index, aliases) });
        break;
      }

      // 普通分数格式: 语文: 108 或 语文108分 (排除后面的斜杠)
      const normalScoreReg = new RegExp(
        `(?:^|[^a-zA-Z0-9\u4e00-\u9fa5])${alias}[：:\\s]*([0-9]+(?:\\.[0-9]+)?)\\s*(?:分)?(?![/／\\d])`,
        'i'
      );
      const mNormal = text.match(normalScoreReg);
      if (mNormal) {
        const sc = parseFloat(mNormal[1]);
        if (sc >= 0 && sc <= 200) {
          const defaultFull = matchedSubject?.full_score || (['语文', '数学', '英语'].includes(standard) ? 120 : 100);
          parsedSubjects.set(standard, {
            subject_name: matchedSubject ? matchedSubject.name : standard,
            subject_id: matchedSubject ? matchedSubject.id : null,
            score: sc,
            full_score: defaultFull,
            is_absent: false
          });
          subjectWindows.push({ standard, start: mNormal.index, end: findNextSubjectIndex(mNormal.index, aliases) });
          break;
        }
      }
    }
  });

  // 5.1 内联单科排名提取：在每科分数与其后一个学科别名之间的窗口内寻找 班级排名/年级排名
  const buildRankReg = (kind, flags = '') => {
    if (kind === 'class') {
      return new RegExp('(?:班级排名|班排|班级第|班级名次)[：:\\s]*第?(\\d+)|班级[^\\d\\n]{0,6}?第?(\\d+)\\s*(?:名|位)?', flags);
    }
    return new RegExp('(?:年级排名|校排|校排名|年级第|年排|年级名次|校次)[：:\\s]*第?(\\d+)|年级[^\\d\\n]{0,6}?第?(\\d+)\\s*(?:名|位)?', flags);
  };

  subjectWindows.forEach(({ standard, start, end }) => {
    const entry = parsedSubjects.get(standard);
    if (!entry || entry.is_absent) return;
    const windowText = text.slice(start, end);
    const cr = windowText.match(buildRankReg('class'));
    const gr = windowText.match(buildRankReg('grade'));
    if (cr) {
      const r = parseInt(cr[1] || cr[2], 10);
      if (r > 0 && r < 1000) {
        entry.class_rank = r;
        maxInlineRankEnd = Math.max(maxInlineRankEnd, start + cr.index + cr[0].length);
      }
    }
    if (gr) {
      const r = parseInt(gr[1] || gr[2], 10);
      if (r > 0 && r < 10000) {
        entry.grade_rank = r;
        maxInlineRankEnd = Math.max(maxInlineRankEnd, start + gr.index + gr[0].length);
      }
    }
  });

  // 5.2 考试级（总分）排名：只取位于所有单科内联排名之后的第一个匹配，避免把单科排名误当总排名
  const findRankAfterInline = (kind, max) => {
    const matches = [...text.matchAll(buildRankReg(kind, 'g'))];
    for (const m of matches) {
      if (m.index > maxInlineRankEnd) {
        const r = parseInt(m[1] || m[2], 10);
        if (r > 0 && r < max) return r;
      }
    }
    return null;
  };
  const examClass = findRankAfterInline('class', 1000);
  const examGrade = findRankAfterInline('grade', 10000);
  if (examClass != null) result.class_rank = examClass;
  if (examGrade != null) result.grade_rank = examGrade;

  result.parsedScores = Array.from(parsedSubjects.values());
  result.matchedCount = result.parsedScores.length;

  return result;
}

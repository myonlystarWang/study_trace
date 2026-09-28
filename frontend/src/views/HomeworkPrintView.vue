<template>
  <div class="homework-print-view">
    <!-- 顶部吸顶操作区：仅屏幕态展示，打印时由 print.css 的 .no-print 彻底隐藏 -->
    <div class="paper-top-bar no-print">
      <van-nav-bar
        :title="isMultiDay ? '多日作业合并打印' : '当日作业打印清单'"
        left-arrow
        @click-left="goBack"
        class="paper-nav-bar"
      />
      <div class="paper-action-bar">
        <div class="action-bar-inner">
          <!-- 排版维度切换 (多日模式下支持按学科 / 按日期切换) -->
          <div class="action-group-segment" v-if="isMultiDay">
            <button
              type="button"
              class="segment-btn"
              :class="{ active: groupBy === 'subject' }"
              @click="groupBy = 'subject'"
            >
              按学科归类
            </button>
            <button
              type="button"
              class="segment-btn"
              :class="{ active: groupBy === 'date' }"
              @click="groupBy = 'date'"
            >
              按日期排布
            </button>
          </div>

          <!-- 状态筛选切换 (全部 vs 仅待办) -->
          <div class="action-filter-segment">
            <button
              type="button"
              class="segment-btn"
              :class="{ active: !onlyUncompleted }"
              @click="onlyUncompleted = false"
            >
              全部作业
            </button>
            <button
              type="button"
              class="segment-btn"
              :class="{ active: onlyUncompleted }"
              @click="onlyUncompleted = true"
            >
              仅待办
            </button>
          </div>

          <div class="action-buttons-wrap">
            <van-button size="small" icon="info-o" class="paper-bar-btn" @click="showPrintTip = true">
              指南
            </van-button>
            <van-button
              size="small"
              type="primary"
              icon="printer"
              class="paper-bar-btn print-primary-btn"
              :disabled="!hasAny"
              @click="handlePrint"
            >
              打印 / 存PDF
            </van-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 打印核心区：复用 print.css 的通用 A4 纸预览框架 -->
    <div class="paper-preview-scroll">
      <div class="paper-page-frame">
        <div class="paper-page-sheet">
          <div v-if="loading" class="hwprint-loading">正在加载作业清单…</div>

          <template v-else>
            <!-- 清单抬头 -->
            <header class="hwprint-head">
              <h1 class="hwprint-title">{{ sheetTitle }}</h1>
              <div class="hwprint-meta">
                <span class="hwprint-meta-item">时间：{{ dateTitle }}</span>
                <span class="hwprint-meta-item">
                  姓名：<span class="hwprint-name-line"></span>
                </span>
                <span class="hwprint-meta-item">
                  共 <b>{{ displayedTotalCount }}</b> 项
                  <template v-if="!onlyUncompleted">
                    · 已完成 <b>{{ completedCount }}</b> 项 · 待办 <b>{{ displayedTotalCount - completedCount }}</b> 项
                  </template>
                </span>
              </div>
            </header>

            <!-- 空态 -->
            <div v-if="!hasAny" class="hwprint-empty">
              选定范围内暂无相关作业记录。
            </div>

            <!-- 模式 A：按学科归类聚合（默认） -->
            <template v-if="groupBy === 'subject'">
              <section v-for="g in subjectGroups" :key="g.name" class="hwprint-group">
                <div class="hwprint-group-header">
                  <span class="hwprint-subject">{{ g.name }}</span>
                  <span class="hwprint-group-count">（{{ g.list.length }} 项）</span>
                </div>
                <ul class="hwprint-list">
                  <li
                    v-for="item in g.list"
                    :key="item.id"
                    class="hwprint-item"
                    :class="{
                      'is-done': item.is_completed,
                      'hwprint-item--tall': isLongContent(item.content)
                    }"
                  >
                    <!-- 手写打勾方框 -->
                    <span class="hwprint-box" aria-hidden="true">
                      <span v-if="item.is_completed" class="hwprint-check">✓</span>
                    </span>
                    <span class="hwprint-content">
                      <span class="hwprint-text"><MathText :text="item.content" /></span>
                      <!-- 日期/顺延标识 -->
                      <span v-if="item.is_weekend_rollover" class="hwprint-rollover-tag">
                        {{ item.rollover_label || '顺延大作业' }}
                      </span>
                      <span v-else-if="isMultiDay && item.date" class="hwprint-date-tag">
                        {{ formatShortDate(item.date) }}
                      </span>
                    </span>
                  </li>
                </ul>
              </section>
            </template>

            <!-- 模式 B：按日期排布 -->
            <template v-else>
              <section v-for="g in dateGroups" :key="g.title" class="hwprint-group">
                <div class="hwprint-group-header">
                  <span class="hwprint-subject">{{ g.title }}</span>
                  <span class="hwprint-group-count">（{{ g.list.length }} 项）</span>
                </div>
                <ul class="hwprint-list">
                  <li
                    v-for="item in g.list"
                    :key="item.id"
                    class="hwprint-item"
                    :class="{
                      'is-done': item.is_completed,
                      'hwprint-item--tall': isLongContent(item.content)
                    }"
                  >
                    <span class="hwprint-box" aria-hidden="true">
                      <span v-if="item.is_completed" class="hwprint-check">✓</span>
                    </span>
                    <span class="hwprint-content">
                      <span class="hwprint-subject-pill">{{ item.subject_name || '综合' }}</span>
                      <span class="hwprint-text"><MathText :text="item.content" /></span>
                      <span v-if="item.is_weekend_rollover" class="hwprint-rollover-tag">
                        {{ item.rollover_label || '顺延大作业' }}
                      </span>
                    </span>
                  </li>
                </ul>
              </section>
            </template>

            <footer v-if="hasAny" class="hwprint-foot">
              完成后请在左侧方框内打勾，全部完成后回「智学迹」打卡。
            </footer>
          </template>
        </div>
      </div>
    </div>

    <!-- 打印指南 -->
    <van-dialog v-model:show="showPrintTip" title="A4 打印指南" confirm-button-text="知道了">
      <div class="print-tip-content">
        <p>为保证清单排版与勾选框清晰，请在浏览器打印预览面板中确认：</p>
        <ol>
          <li>纸张选 <strong>A4</strong>、页边距选 <strong>默认</strong>（已按 18mm 专业边距排版）；</li>
          <li>多日/假期作业较多时将自动跨页分页，建议勾选<strong>「页眉和页脚」</strong>以显示底部页码；</li>
          <li><strong>无需勾选「背景图形」</strong>：清单里的勾选框与分组线全部由线条绘制，不依赖底色；</li>
          <li>需要留档或发给别人，请在打印目标里选择<strong>「另存为 PDF」</strong>。</li>
        </ol>
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { showToast } from 'vant';
import { homeworkApi } from '../api';
import MathText from '../components/MathText.vue';

const route = useRoute();
const router = useRouter();

const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

const pad = (n) => String(n).padStart(2, '0');
const toDateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const parseDateStr = (s) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date();
};

const formatShortDate = (dStr) => {
  if (!dStr) return '';
  const parts = dStr.split('-');
  return parts.length >= 3 ? `${parts[1]}-${parts[2]}` : dStr;
};

// 模式参数提取
const queryStartDate = route.query.start_date;
const queryEndDate = route.query.end_date;
const queryDate = route.query.date;

const isMultiDay = computed(() => Boolean(queryStartDate && queryEndDate && queryStartDate !== queryEndDate));
const startDateStr = ref(typeof queryStartDate === 'string' && queryStartDate ? queryStartDate : (typeof queryDate === 'string' && queryDate ? queryDate : toDateStr(new Date())));
const endDateStr = ref(typeof queryEndDate === 'string' && queryEndDate ? queryEndDate : startDateStr.value);

// 状态与选项
const groupBy = ref('subject'); // 'subject' | 'date'
const onlyUncompleted = ref(route.query.only_uncompleted === '1' || route.query.only_uncompleted === 'true');
const loading = ref(true);
const showPrintTip = ref(false);

const rawItems = ref([]);
const rolloverItems = ref([]);
const breakInfo = ref(null);

// 所有条目合并池
const allItems = computed(() => [...rolloverItems.value, ...rawItems.value]);

// 经过「仅待办」过滤后的活跃条目池
const activeItems = computed(() => {
  if (!onlyUncompleted.value) {
    return allItems.value;
  }
  return allItems.value.filter((it) => !it.is_completed);
});

const displayedTotalCount = computed(() => activeItems.value.length);
const completedCount = computed(() => activeItems.value.filter((it) => it.is_completed).length);
const hasAny = computed(() => displayedTotalCount.value > 0);

// 学科排序权重字典
const SUBJECT_ORDER = ['语文', '数学', '英语', '道德与法治', '道法', '政治', '历史', '地理', '生物', '物理', '化学'];
const getSubjectOrder = (name) => {
  const idx = SUBJECT_ORDER.indexOf(name);
  return idx !== -1 ? idx : 999;
};

// 1. 按学科归类分组
const subjectGroups = computed(() => {
  const map = new Map();
  const push = (it) => {
    const key = it.subject_name || '综合';
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(it);
  };
  activeItems.value.forEach(push);

  const groups = Array.from(map, ([name, list]) => ({
    name,
    order: getSubjectOrder(name),
    list: [...list].sort((a, b) => {
      // 顺延大作业优先排在最前
      if (a.is_weekend_rollover !== b.is_weekend_rollover) {
        return a.is_weekend_rollover ? -1 : 1;
      }
      if (a.date !== b.date) {
        return (a.date || '').localeCompare(b.date || '');
      }
      return a.id - b.id;
    })
  }));

  return groups.sort((a, b) => a.order - b.order);
});

// 2. 按日期归类分组
const dateGroups = computed(() => {
  const map = new Map();

  // 若有放假前顺延作业，先建顺延作业分组
  const rolloverList = activeItems.value.filter((it) => it.is_weekend_rollover);
  if (rolloverList.length > 0) {
    const label = rolloverList[0].rollover_label || '假期/周末顺延大作业';
    map.set('rollover', {
      title: `${label}（截止假期结束）`,
      list: rolloverList
    });
  }

  // 正常每日作业按日期归类
  const normalList = activeItems.value.filter((it) => !it.is_weekend_rollover);
  normalList.forEach((it) => {
    const dStr = it.date || startDateStr.value;
    if (!map.has(dStr)) {
      const d = parseDateStr(dStr);
      const title = `${d.getMonth() + 1}月${d.getDate()}日 ${WEEK[d.getDay()]}`;
      map.set(dStr, { title, list: [] });
    }
    map.get(dStr).list.push(it);
  });

  return Array.from(map.values()).map((g) => ({
    ...g,
    list: [...g.list].sort((a, b) => {
      const ordA = getSubjectOrder(a.subject_name);
      const ordB = getSubjectOrder(b.subject_name);
      if (ordA !== ordB) return ordA - ordB;
      return a.id - b.id;
    })
  }));
});

// 标题渲染
const sheetTitle = computed(() => {
  if (breakInfo.value && breakInfo.value.display_name) {
    return `${breakInfo.value.display_name}作业清单`;
  }
  if (isMultiDay.value) {
    return '多日作业合并清单';
  }
  return '每日作业清单';
});

// 日期副标题
const dateTitle = computed(() => {
  if (isMultiDay.value) {
    const start = parseDateStr(startDateStr.value);
    const end = parseDateStr(endDateStr.value);
    const days = Math.round((end - start) / (1000 * 60 * 60 * 24)) + 1;
    const holidayTag = breakInfo.value?.holiday_name ? ` · ${breakInfo.value.holiday_name}` : '';
    return `${start.getFullYear()}年${start.getMonth() + 1}月${start.getDate()}日 ~ ${end.getMonth() + 1}月${end.getDate()}日（共 ${days} 天${holidayTag}）`;
  }
  const d = parseDateStr(startDateStr.value);
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${WEEK[d.getDay()]}`;
});

const isLongContent = (content) => (content || '').length > 80;

const load = async () => {
  loading.value = true;
  try {
    if (isMultiDay.value) {
      const res = await homeworkApi.getList({
        start_date: startDateStr.value,
        end_date: endDateStr.value
      });
      rawItems.value = res.data.items || [];
      rolloverItems.value = res.data.rollover_items || [];
      breakInfo.value = res.data.break_info || null;
    } else {
      const res = await homeworkApi.getList(startDateStr.value);
      rawItems.value = res.data.items || [];
      rolloverItems.value = res.data.weekend_rollover?.items || [];
      breakInfo.value = res.data.break_info || res.data.weekend_rollover?.break_info || null;
    }
  } catch (err) {
    console.error('获取打印清单数据失败:', err);
    rawItems.value = [];
    rolloverItems.value = [];
    breakInfo.value = null;
    showToast('加载作业失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

const handlePrint = async () => {
  if (!hasAny.value) return;

  try {
    const imgs = Array.from(document.images);
    await Promise.all(
      imgs.map((img) => {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        return img.decode().catch(() => {});
      })
    );
  } catch (e) {
    // 容错
  }

  await nextTick();
  await new Promise((resolve) => setTimeout(resolve, 150));

  window.print();
};

const goBack = () => {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push('/homework');
  }
};

onMounted(load);
</script>

<style scoped>
/* 顶部操作区（仅屏幕态）：与 PaperPrintView 同构，打印时靠全局 .no-print 隐藏 */
.paper-top-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--st-bg-card, #ffffff);
}

.paper-nav-bar {
  background: var(--st-bg-card, #ffffff);
  border-bottom: 1px solid var(--st-border, #e2e8f0);
}

.paper-action-bar {
  background: var(--st-bg-card, #ffffff);
  padding: 8px 16px;
  border-bottom: 1px solid var(--st-border, #e2e8f0);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.action-bar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  max-width: 800px;
  margin: 0 auto;
  flex-wrap: wrap;
}

/* 分段切换按钮组 */
.action-group-segment,
.action-filter-segment {
  display: flex;
  background: var(--st-bg-subtle, #f1f5f9);
  border-radius: var(--st-radius-md, 8px);
  padding: 2px;
  gap: 2px;
}

.segment-btn {
  border: none;
  background: transparent;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: var(--st-font-xs, 12px);
  font-weight: 500;
  color: var(--st-text-secondary, #64748b);
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.segment-btn.active {
  background: #ffffff;
  color: var(--st-primary, #2563eb);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.action-buttons-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.paper-bar-btn {
  white-space: nowrap !important;
  font-weight: 500;
  border-radius: var(--st-radius-full, 9999px);
  font-size: var(--st-font-xs, 12px);
}

.print-primary-btn {
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
}

.print-tip-content {
  padding: 16px;
  font-size: 13px;
  color: #334155;
  line-height: 1.6;
}

.print-tip-content ol {
  padding-left: 18px;
  margin-top: 6px;
}

.print-tip-content li {
  margin-bottom: 6px;
}

/* ==========================================================================
   印刷排版区（独立体系）：字号/尺寸一律用 pt 与 mm 硬编码，
   不引用屏幕端 --st-font-* / --st-space-* 令牌（见 design-tokens.css 顶部约定）。
   ========================================================================== */

.hwprint-loading,
.hwprint-empty {
  padding: 40mm 0;
  text-align: center;
  font-size: 11pt;
  color: #475569;
}

/* 抬头 */
.hwprint-head {
  border-bottom: 0.5mm solid #0f172a;
  padding-bottom: 2.5mm;
  margin-bottom: 3.5mm;
}

.hwprint-title {
  font-size: 15pt;
  font-weight: 800;
  text-align: center;
  letter-spacing: 1px;
  color: #0f172a;
  margin: 0 0 2mm;
}

.hwprint-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5mm 8mm;
  font-size: 9.5pt;
  color: #1e293b;
}

.hwprint-name-line {
  display: inline-block;
  min-width: 26mm;
  border-bottom: 0.3mm solid #0f172a;
  transform: translateY(-0.6mm);
}

/* 分组标题：左侧粗竖线；break-after: avoid 防止标题落成页尾孤儿 */
.hwprint-group-header {
  display: flex;
  align-items: baseline;
  gap: 1.5mm;
  margin: 3.5mm 0 1.5mm;
  padding-left: 2mm;
  border-left: 1mm solid #0f172a;
  break-after: avoid;
  page-break-after: avoid;
}

.hwprint-subject {
  font-size: 11.5pt;
  font-weight: 700;
  color: #0f172a;
}

.hwprint-group-count {
  font-size: 8.5pt;
  color: #475569;
}

.hwprint-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

/* 单条作业：左侧方框 + 内容，行高约 9.5mm */
.hwprint-item {
  display: flex;
  align-items: flex-start;
  gap: 2.5mm;
  min-height: 9.5mm;
  padding: 1.4mm 0;
  border-bottom: 0.2mm dotted #cbd5e1;
  break-inside: avoid;
  page-break-inside: avoid;
}

.hwprint-item--tall {
  min-height: 14mm;
  break-inside: auto;
  page-break-inside: auto;
}

/* 4.2mm 见方手写方框 */
.hwprint-box {
  width: 4.2mm;
  height: 4.2mm;
  border: 0.35mm solid #0f172a;
  border-radius: 0.5mm;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.8mm;
  background: transparent;
}

.hwprint-check {
  font-size: 8pt;
  font-weight: 800;
  line-height: 1;
  color: #0f172a;
}

.hwprint-content {
  flex: 1;
  min-width: 0;
  font-size: 10.5pt;
  line-height: 1.5;
  color: #0f172a;
  word-break: break-word;
}

.hwprint-text {
  font-size: 10.5pt;
}

.hwprint-item.is-done .hwprint-text {
  color: #64748b;
}

.hwprint-subject-pill {
  display: inline-block;
  font-size: 8.5pt;
  font-weight: 700;
  color: #0f172a;
  margin-right: 1.5mm;
}

.hwprint-date-tag,
.hwprint-rollover-tag {
  display: inline-block;
  font-size: 7.5pt;
  font-weight: 600;
  padding: 0.2mm 1.2mm;
  border-radius: 0.6mm;
  margin-left: 2mm;
  vertical-align: baseline;
}

.hwprint-date-tag {
  color: #475569;
  border: 0.25mm solid #94a3b8;
}

.hwprint-rollover-tag {
  color: #0369a1;
  border: 0.25mm solid #0284c7;
}

/* 页脚注记 */
.hwprint-foot {
  margin-top: 5mm;
  padding-top: 2mm;
  border-top: 0.2mm solid #cbd5e1;
  font-size: 8.5pt;
  color: #64748b;
  text-align: center;
  break-before: avoid;
  page-break-before: avoid;
}
</style>

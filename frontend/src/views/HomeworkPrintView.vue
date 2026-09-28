<template>
  <div class="homework-print-view">
    <!-- 顶部吸顶操作区：仅屏幕态展示，打印时由 print.css 的 .no-print 彻底隐藏 -->
    <div class="paper-top-bar no-print">
      <van-nav-bar
        title="当日作业打印清单"
        left-arrow
        @click-left="goBack"
        class="paper-nav-bar"
      />
      <div class="paper-action-bar">
        <div class="action-bar-inner">
          <van-button size="small" icon="info-o" class="paper-bar-btn" @click="showPrintTip = true">
            打印指南
          </van-button>
          <van-button
            size="small"
            type="primary"
            icon="printer"
            class="paper-bar-btn"
            :disabled="!hasAny"
            @click="handlePrint"
          >
            打印 / 存PDF
          </van-button>
        </div>
      </div>
    </div>

    <!-- 打印核心区：复用 print.css 的通用 A4 纸预览框架 -->
    <div class="paper-preview-scroll">
      <div class="paper-page-frame">
        <div class="paper-page-sheet">
          <div v-if="loading" class="hwprint-loading">正在加载作业…</div>

          <template v-else>
            <!-- 清单抬头 -->
            <header class="hwprint-head">
              <h1 class="hwprint-title">每日作业清单</h1>
              <div class="hwprint-meta">
                <span class="hwprint-meta-item">日期：{{ dateTitle }}</span>
                <span class="hwprint-meta-item">
                  姓名：<span class="hwprint-name-line"></span>
                </span>
                <span class="hwprint-meta-item">
                  共 <b>{{ totalCount }}</b> 项 · 已完成 <b>{{ completedCount }}</b> 项
                </span>
              </div>
            </header>

            <!-- 空态 -->
            <div v-if="!hasAny" class="hwprint-empty">
              当日（含周五顺延）暂无作业记录。
            </div>

            <!-- 按科目分组的清单 -->
            <section v-for="g in groups" :key="g.name" class="hwprint-group">
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
                  <!-- 手写打勾方框：border 绘制，不依赖浏览器「背景图形」打印选项 -->
                  <span class="hwprint-box" aria-hidden="true">
                    <span v-if="item.is_completed" class="hwprint-check">✓</span>
                  </span>
                  <span class="hwprint-content">
                    <span class="hwprint-text"><MathText :text="item.content" /></span>
                    <span v-if="item.is_weekend_rollover" class="hwprint-rollover-tag">周五顺延</span>
                  </span>
                </li>
              </ul>
            </section>

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
          <li>勾选<strong>「页眉和页脚」</strong>可显示底部页码（条目不超一页时用不到）；</li>
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
// 与 HomeworkView 一致用本地日期口径：toISOString() 在 UTC+8 凌晨会回退到昨天
const toDateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const parseDateStr = (s) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date();
};

// 入口传入的日期原样采用（所传即所印），缺省为本机今天
const dateStr = ref(typeof route.query.date === 'string' && route.query.date ? route.query.date : toDateStr(new Date()));
const todayItems = ref([]);
const rollover = ref(null);
const loading = ref(true);
const showPrintTip = ref(false);

const rolloverItems = computed(() => rollover.value?.items || []);

// 插入式分组：后端已按 Subject.sort_order / id 排序，首现即定序，顺延项并入各科目桶
const groups = computed(() => {
  const map = new Map();
  const push = (it) => {
    const key = it.subject_name || '综合';
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(it);
  };
  todayItems.value.forEach(push);
  rolloverItems.value.forEach(push);
  return Array.from(map, ([name, list]) => ({ name, list }));
});

const totalCount = computed(() => todayItems.value.length + rolloverItems.value.length);
const completedCount = computed(
  () => [...todayItems.value, ...rolloverItems.value].filter((it) => it.is_completed).length
);
const hasAny = computed(() => totalCount.value > 0);

const dateTitle = computed(() => {
  const d = parseDateStr(dateStr.value);
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${WEEK[d.getDay()]}`;
});

// 超长条目放开「不跨页」约束，允许自然跨页；短条目整条不腰斩
const isLongContent = (content) => (content || '').length > 80;

const load = async () => {
  loading.value = true;
  try {
    const res = await homeworkApi.getList(dateStr.value);
    todayItems.value = res.data.items || [];
    rollover.value = res.data.weekend_rollover || null;
  } catch (err) {
    console.error('获取打印清单数据失败:', err);
    todayItems.value = [];
    rollover.value = null;
    showToast('加载作业失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

const handlePrint = async () => {
  if (!hasAny.value) return;

  // 等图片解码完成，消除打印分页高度抖动（本页通常无图，保留以与试卷链路同口径）
  try {
    const imgs = Array.from(document.images);
    await Promise.all(
      imgs.map((img) => {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        return img.decode().catch(() => {});
      })
    );
  } catch (e) {
    // 容错不阻断打印
  }

  // MathText 先同步输出兜底文本、再异步升级为 KaTeX 真公式，留稳定期避免打到半成品
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
  background: var(--st-bg-card);
}

.paper-nav-bar {
  background: var(--st-bg-card);
  border-bottom: 1px solid var(--st-border);
}

.paper-action-bar {
  background: var(--st-bg-card);
  padding: var(--st-space-2) var(--st-space-4);
  border-bottom: 1px solid var(--st-border);
  box-shadow: var(--st-shadow-card);
}

.action-bar-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--st-space-2);
  max-width: 600px;
  margin: 0 auto;
}

.paper-bar-btn {
  flex: 1;
  white-space: nowrap !important;
  font-weight: 500;
  border-radius: var(--st-radius-full);
  font-size: var(--st-font-xs);
}

.print-tip-content {
  padding: var(--st-space-4);
  font-size: var(--st-font-sm);
  color: var(--st-text-regular);
  line-height: var(--st-leading-loose);
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

.hwprint-loading {
  padding: 40mm 0;
  text-align: center;
  font-size: 11pt;
  color: #475569;
}

/* 抬头 */
.hwprint-head {
  border-bottom: 0.5mm solid #0f172a;
  padding-bottom: 2.5mm;
  margin-bottom: 3mm;
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

/* 科目分组标题：左侧粗竖线；break-after: avoid 防止标题落成页尾孤儿 */
.hwprint-group-header {
  display: flex;
  align-items: baseline;
  gap: 1mm;
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
  padding: 1.2mm 0;
  border-bottom: 0.2mm dotted #cbd5e1;
  break-inside: avoid;
  page-break-inside: avoid;
}

.hwprint-item--tall {
  break-inside: auto;
  page-break-inside: auto;
}

/* 5mm 手写打勾方框：border 而非 background —— 不勾「背景图形」也能打印 */
.hwprint-box {
  flex: 0 0 auto;
  width: 5mm;
  height: 5mm;
  box-sizing: border-box;
  border: 0.35mm solid #0f172a;
  border-radius: 0.6mm;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 3.6mm;
  line-height: 1;
  color: #0f172a;
  margin-top: 0.8mm;
}

.hwprint-check {
  font-weight: 700;
}

.hwprint-content {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #0f172a;
}

/* 已完成项：内容灰化 + 删除线。
   删除线只加在 .hwprint-text 上，不加在 .hwprint-content —— text-decoration
   会沿 inline 后代继承且无法在子元素上撤销，加在父级会让「周五顺延」标签一起被划掉。 */
.hwprint-item.is-done .hwprint-text {
  color: #64748b;
  text-decoration: line-through;
}

.hwprint-item.is-done .hwprint-box {
  border-color: #64748b;
}

.hwprint-rollover-tag {
  display: inline-block;
  margin-left: 2mm;
  padding: 0 1.2mm;
  font-size: 7.5pt;
  color: #7c3aed;
  border: 0.2mm solid #c4b5fd;
  border-radius: 0.6mm;
  white-space: nowrap;
}

.hwprint-empty {
  padding: 20mm 0;
  text-align: center;
  font-size: 11pt;
  color: #475569;
}

.hwprint-foot {
  margin-top: 4mm;
  padding-top: 2mm;
  border-top: 0.2mm dashed #cbd5e1;
  font-size: 8pt;
  color: #64748b;
  text-align: center;
}
</style>

<template>
  <div class="paper-print-view">
    <!-- 顶部操作工具栏（仅屏幕展示，打印时彻底隐藏） -->
    <div class="paper-toolbar no-print">
      <div class="toolbar-left">
        <van-button size="small" icon="arrow-left" @click="goBack">返回</van-button>
        <span class="paper-title-tag">{{ paper.title || '试卷预览' }}</span>
        <van-tag v-if="paper.status === 'reviewed'" type="success" size="medium">已完成打卡</van-tag>
        <van-tag v-else-if="paper.status === 'printed'" type="warning" size="medium">已打印·待打卡</van-tag>
        <van-tag v-else type="primary" plain size="medium">未打印·待重练</van-tag>
      </div>
      <div class="toolbar-right">
        <van-button size="small" icon="info-o" @click="showPrintTip = true">打印提示</van-button>
        <van-button size="small" type="primary" icon="passed" @click="openReviewModal">📝 重练打卡</van-button>
        <van-button size="small" type="success" icon="printer" @click="handlePrint">🖨️ 打印 / 存PDF</van-button>
      </div>
    </div>

    <!-- 超长题黄色提示 Banner (仅屏幕显示) -->
    <van-notice-bar
      v-if="paper.warnings && paper.warnings.length > 0"
      left-icon="warning-o"
      color="#d97706"
      background="#fffbeb"
      class="paper-warning-bar no-print"
      wrapable
    >
      <span>排版提示：{{ paper.warnings.join('；') }}。建议留意打印预览，或使用下方「✂️ 在此题前换页」微调。</span>
    </van-notice-bar>


    <!-- 打印核心区域 -->
    <div class="paper-preview-scroll">
      <div class="paper-page-frame">
        <div class="paper-page-sheet">
          <!-- 试卷大抬头 -->
          <div class="paper-header">
            <h1 class="paper-main-title">{{ paper.title || '初一错题周末重练卷' }}</h1>
            <div v-if="paper.subtitle" class="paper-subtitle">{{ paper.subtitle }}</div>

            <!-- 考生个人信息栏 -->
            <div class="paper-student-info">
              <span class="info-item">考生姓名：<u>&nbsp;{{ paper.student_name || '初一同学' }}&nbsp;</u></span>
              <span class="info-item">班级：<u>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</u></span>
              <span class="info-item">学号：<u>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</u></span>
              <span class="info-item">日期：____年__月__日</span>
              <span class="info-item score-box">得分：__________</span>
            </div>

            <!-- 得分统计表格 -->
            <table class="paper-score-table">
              <tbody>
                <tr>
                  <td class="table-th">大题编号</td>
                  <td v-for="seg in scoreSegments" :key="seg.label" class="table-th">{{ seg.label }}</td>
                  <td class="table-th highlight-th">总分</td>
                </tr>
                <tr>
                  <td class="table-label">评卷得分</td>
                  <td v-for="seg in scoreSegments" :key="seg.label"></td>
                  <td></td>
                </tr>
              </tbody>
            </table>

            <!-- 考生须知 -->
            <div class="paper-notice-box">
              <div class="notice-title">【考生重练须知】</div>
              <div class="notice-item">1. 本卷为基于个人错题库定制生成的错题针对性重练卷，请独立闭卷规范作答；</div>
              <div class="notice-item">2. 建议使用 0.5mm 黑色水笔，在每道题目指定的网格留白答题区域内清晰书写；</div>
              <div class="notice-item">3. 线下完成练习后，请回到学迹系统点击「重练打卡」，系统将一键推进艾宾浩斯复习周期。</div>
            </div>
          </div>

          <!-- 试卷题目列表 -->
          <div class="paper-body">
            <div v-for="(group, gIdx) in groupedQuestions" :key="group.subjectName" class="paper-subject-group">
              <!-- 按科目大题标题（仅在按科目排序时展示） -->
              <div v-if="paper.sort_by === 'subject'" class="paper-subject-header">
                {{ getChineseNumber(gIdx + 1) }}、{{ group.subjectName }}（共 {{ group.questions.length }} 题）
              </div>

              <div class="paper-question-list">
                <div
                  v-for="q in group.questions"
                  :key="q.id"
                  class="paper-question-item"
                  :class="{
                    'is-oversized': q.is_oversized,
                    'manual-page-break': manualBreaks.includes(q.id)
                  }"
                >
                  <!-- 屏幕态手动分页控制按钮 -->
                  <div class="question-header-row">
                    <div class="question-meta-badge">
                      <span class="q-number">{{ q.order_num }}.</span>
                      <span class="q-subject-badge">{{ q.subject_name }}</span>
                      <span v-if="paper.show_error_type && q.error_type" class="q-error-tag">【错因：{{ q.error_type }}】</span>
                    </div>
                    <div class="page-break-btn no-print" @click="toggleManualBreak(q.id)">
                      <span v-if="manualBreaks.includes(q.id)" class="break-active">✂️ 已在此处换页（点击取消）</span>
                      <span v-else class="break-idle">✂️ 在此题前换页</span>
                    </div>
                  </div>

                  <!-- 题干文本 -->
                  <div class="question-text">
                    {{ q.extracted_text }}
                  </div>

                  <!-- 题目插图 (max-height: 55mm 自适应) -->
                  <div v-if="q.original_image_path" class="paper-question-img-wrap">
                    <img :src="q.original_image_path" class="paper-question-img" alt="题目配图" />
                  </div>

                  <!-- 答题留白区域 (防截断 + 格式化底纹) -->
                  <div
                    class="paper-answer-area"
                    :class="'paper-answer-area--' + (paper.style_mode || 'grid')"
                    :style="{ height: q.space_mm + 'mm' }"
                  >
                    <div class="answer-placeholder no-print">答题留白区 ({{ q.space_mm }}mm)</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 打印提示弹窗 -->
    <van-dialog v-model:show="showPrintTip" title="🖨️ A4 打印与另存 PDF 指南" confirm-button-text="知道了">
      <div class="print-tip-content">
        <p>为保证最佳试卷排版与格线效果，请在浏览器的打印预览面板中确认：</p>
        <ol>
          <li><strong>勾选「背景图形」</strong>：确保答题区的方格/横线底纹清晰印出；</li>
          <li><strong>勾选「页眉和页脚」</strong>：激活 A4 底部中央的「第 X 页 / 共 Y 页」页码；</li>
          <li><strong>页边距选择「默认」</strong>：已有标准 18mm 专业页边距规范；</li>
          <li><strong>纸张尺寸选择「A4」</strong>：iOS Safari 打印导出时请确认选定 A4 纸型。</li>
        </ol>
      </div>
    </van-dialog>

    <!-- 批量重练打卡弹窗 -->
    <van-dialog
      v-model:show="showReviewModal"
      title="📝 周末试卷批量重练打卡"
      show-cancel-button
      confirm-button-text="确认打卡"
      :confirm-button-disabled="!isAllReviewed"
      :confirm-button-loading="submittingReview"
      @confirm="submitBatchReview"
    >
      <div class="review-modal-body">
        <div class="review-header-tools">
          <span class="review-progress">
            进度：<strong>{{ reviewedCount }}</strong> / {{ paper.questions?.length || 0 }} 题
          </span>
          <div class="quick-batch-btns">
            <span class="batch-link" @click="batchSetAll('remembered')">一键全掌握</span>
            <span class="divider">|</span>
            <span class="batch-link" @click="batchSetAll('forgotten')">一键全遗忘</span>
          </div>
        </div>
        <div class="review-tip">
          请对照孩子线下卷面批改结果逐题标注（必须全部标注后方可提交，防止误触推进艾宾浩斯）：
        </div>
        <div class="review-question-list">
          <div v-for="q in paper.questions" :key="q.id" class="review-item-row">
            <div class="review-q-title">
              <span class="bold">{{ q.order_num }}.</span>
              <span class="sub-name">[{{ q.subject_name }}]</span>
              <span class="q-snippet">{{ getSnippet(q.extracted_text) }}</span>
            </div>
            <div class="review-toggles">
              <button
                class="review-tag-btn"
                :class="{ active: reviewMap[q.id] === 'remembered' }"
                @click="reviewMap[q.id] = 'remembered'"
              >
                ✅ 掌握
              </button>
              <button
                class="review-tag-btn forgot-btn"
                :class="{ active: reviewMap[q.id] === 'forgotten' }"
                @click="reviewMap[q.id] = 'forgotten'"
              >
                ❌ 遗忘
              </button>
            </div>
          </div>
        </div>
      </div>
    </van-dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { showToast } from 'vant';
import { paperApi } from '../api';

const route = useRoute();
const router = useRouter();

const paper = ref({
  paper_id: 0,
  title: '初一错题周末重练卷',
  subtitle: '满分: 100分 · 建议用时: 45分钟',
  student_name: '初一同学',
  sort_by: 'subject',
  space_level: 'standard',
  style_mode: 'grid',
  show_error_type: false,
  questions: [],
  total_questions: 0,
  estimated_pages: 1,
  warnings: [],
  status: 'draft',
});

const manualBreaks = ref([]);
const showPrintTip = ref(false);
const showReviewModal = ref(false);
const submittingReview = ref(false);
const reviewMap = ref({});

const goBack = () => {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push('/paper');
  }
};

const getChineseNumber = (n) => {
  const digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'];
  return digits[n] || String(n);
};

const getSnippet = (text) => {
  if (!text) return '（图题）';
  return text.length > 18 ? text.slice(0, 18) + '...' : text;
};

// 得分统计段计算
const scoreSegments = computed(() => {
  const total = paper.value.questions?.length || 0;
  if (total <= 0) return [{ label: '1~5' }];
  const segs = [];
  for (let i = 1; i <= total; i += 5) {
    const end = Math.min(i + 4, total);
    segs.push({ label: `${i}~${end}` });
  }
  return segs;
});

// 题目按科目分组（若非按科目排序，则作为单一总组展示）
const groupedQuestions = computed(() => {
  const qs = paper.value.questions || [];
  if (paper.value.sort_by !== 'subject') {
    return [{ subjectName: '全卷题目', questions: qs }];
  }
  const map = new Map();
  for (const q of qs) {
    const sub = q.subject_name || '综合';
    if (!map.has(sub)) {
      map.set(sub, []);
    }
    map.get(sub).push(q);
  }
  return Array.from(map.entries()).map(([subName, list]) => ({
    subjectName: subName,
    questions: list,
  }));
});

const toggleManualBreak = (qId) => {
  const idx = manualBreaks.value.indexOf(qId);
  if (idx > -1) {
    manualBreaks.value.splice(idx, 1);
  } else {
    manualBreaks.value.push(qId);
  }
};

const handlePrint = async () => {
  // 打印前等待全部图片解码完成，消除分页高度抖动
  try {
    const imgs = Array.from(document.images);
    await Promise.all(
      imgs.map((img) => {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        return img.decode().catch(() => {});
      })
    );
  } catch (e) {
    // 忽略解码容错
  }

  // 触发打印时回写试卷状态为 printed
  try {
    if (paper.value.paper_id && paper.value.status === 'draft') {
      await paperApi.markPrinted(paper.value.paper_id);
      paper.value.status = 'printed';
    }
  } catch (e) {
    // 容错不阻断打印
  }

  window.print();
};

const reviewedCount = computed(() => {
  const qs = paper.value.questions || [];
  return qs.filter((q) => reviewMap.value[q.id] === 'remembered' || reviewMap.value[q.id] === 'forgotten').length;
});

const isAllReviewed = computed(() => {
  const qs = paper.value.questions || [];
  if (qs.length === 0) return true;
  return qs.every((q) => reviewMap.value[q.id] === 'remembered' || reviewMap.value[q.id] === 'forgotten');
});

const batchSetAll = (result) => {
  for (const q of paper.value.questions || []) {
    reviewMap.value[q.id] = result;
  }
};

const openReviewModal = () => {
  // 默认初始为 null，要求用户主动显式标注，防止误触污染艾宾浩斯
  const initial = {};
  for (const q of paper.value.questions || []) {
    initial[q.id] = reviewMap.value[q.id] || null;
  }
  reviewMap.value = initial;
  showReviewModal.value = true;
};


const submitBatchReview = async () => {
  submittingReview.value = true;
  try {
    const reviews = Object.entries(reviewMap.value).map(([mid, res]) => ({
      mistake_id: Number(mid),
      result: res,
    }));
    const res = await paperApi.batchReview(paper.value.paper_id, reviews);
    paper.value.status = 'reviewed';
    showReviewModal.value = false;
    showToast({ message: res.data.message || '打卡成功', icon: 'success' });
  } catch (err) {
    showToast(err.response?.data?.detail || '批量打卡失败');
  } finally {
    submittingReview.value = false;
  }
};

const loadPaperData = async () => {
  const paperId = route.query.id || sessionStorage.getItem('current_paper_id');
  if (!paperId) {
    showToast('未指定试卷 ID');
    router.push('/paper');
    return;
  }
  try {
    const res = await paperApi.getPaper(Number(paperId));
    paper.value = res.data;
    if (res.data.warnings && res.data.warnings.length > 0) {
      console.info('试卷排版提示:', res.data.warnings);
    }
  } catch (err) {
    showToast('恢复试卷失败，可能试卷已失效');
    router.push('/paper');
  }
};

onMounted(async () => {
  await loadPaperData();
  if (route.query.action === 'review') {
    openReviewModal();
  }
});
</script>

<style scoped>
/* 工具栏样式 */
.paper-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.paper-title-tag {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 试卷大抬头排版规范 */
.paper-header {
  margin-bottom: 24px;
  border-bottom: 2px solid #0f172a;
  padding-bottom: 16px;
}

.paper-main-title {
  font-size: 22pt;
  font-weight: 800;
  text-align: center;
  color: #0f172a;
  letter-spacing: 2px;
  margin-bottom: 6px;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}

.paper-subtitle {
  font-size: 10.5pt;
  text-align: center;
  color: #475569;
  margin-bottom: 14px;
}

.paper-student-info {
  display: flex;
  justify-content: space-between;
  font-size: 10.5pt;
  color: #1e293b;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.score-box {
  font-weight: 700;
}

/* 得分统计表格 */
.paper-score-table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 14px 0;
  font-size: 9.5pt;
  text-align: center;
}

.paper-score-table td {
  border: 1px solid #94a3b8;
  padding: 5px 4px;
  height: 24px;
}

.table-th {
  background-color: #f8fafc;
  font-weight: 600;
  color: #334155;
}

.highlight-th {
  background-color: #f1f5f9;
  font-weight: 700;
}

.table-label {
  font-weight: 600;
}

/* 考生须知 */
.paper-notice-box {
  background-color: #fafafa;
  border: 1px dashed #cbd5e1;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 8.5pt;
  color: #475569;
  line-height: 1.5;
}

.notice-title {
  font-weight: 700;
  color: #334155;
  margin-bottom: 2px;
}

/* 题目排版 */
.paper-subject-header {
  font-size: 13pt;
  font-weight: 700;
  color: #0f172a;
  margin: 20px 0 12px 0;
  border-left: 4px solid #2563eb;
  padding-left: 8px;
}

.question-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.question-meta-badge {
  display: flex;
  align-items: center;
  gap: 6px;
}

.q-number {
  font-size: 11pt;
  font-weight: 800;
  color: #0f172a;
}

.q-subject-badge {
  font-size: 8pt;
  background: #f1f5f9;
  color: #475569;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

.q-error-tag {
  font-size: 8pt;
  color: #d97706;
}

.page-break-btn {
  font-size: 11px;
  cursor: pointer;
  user-select: none;
}

.break-idle {
  color: #94a3b8;
  padding: 2px 6px;
  border: 1px dashed #cbd5e1;
  border-radius: 4px;
}

.break-idle:hover {
  color: #2563eb;
  border-color: #2563eb;
}

.break-active {
  color: #ef4444;
  font-weight: 600;
  background: #fef2f2;
  padding: 2px 6px;
  border: 1px solid #fca5a5;
  border-radius: 4px;
}

.question-text {
  font-size: 10.5pt;
  line-height: 1.6;
  color: #0f172a;
  white-space: pre-wrap;
  text-align: justify;
}

.answer-placeholder {
  font-size: 9pt;
  color: #cbd5e1;
  padding: 6px 10px;
  user-select: none;
}

/* 打印提示弹窗内容 */
.print-tip-content {
  padding: 12px;
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

.paper-warning-bar {
  margin-bottom: 8px;
  border-radius: 6px;
  font-size: 13px;
}

/* 打卡弹窗 */
.review-modal-body {
  max-height: 60vh;
  overflow-y: auto;
  padding: 10px 14px;
}

.review-header-tools {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f1f5f9;
  padding: 8px 10px;
  border-radius: 6px;
  margin-bottom: 8px;
  font-size: 12px;
}

.review-progress strong {
  color: #2563eb;
}

.quick-batch-btns {
  display: flex;
  align-items: center;
}

.batch-link {
  color: #2563eb;
  cursor: pointer;
  font-weight: 500;
}

.batch-link:hover {
  text-decoration: underline;
}

.divider {
  margin: 0 6px;
  color: #cbd5e1;
}

.review-tip {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
}


.review-question-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.review-item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.review-q-title {
  flex: 1;
  font-size: 13px;
  color: #1e293b;
  min-width: 0;
  margin-right: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bold {
  font-weight: 700;
}

.sub-name {
  color: #2563eb;
  margin: 0 4px;
}

.q-snippet {
  color: #64748b;
}

.review-toggles {
  display: flex;
  gap: 6px;
}

.review-tag-btn {
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.review-tag-btn.active {
  background: #10b981;
  color: #ffffff;
  border-color: #10b981;
  font-weight: 600;
}

.review-tag-btn.forgot-btn.active {
  background: #ef4444;
  color: #ffffff;
  border-color: #ef4444;
  font-weight: 600;
}
</style>

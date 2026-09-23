<template>
  <div class="score-view">
    <!-- 顶部导航栏 -->
    <van-nav-bar
      title="成长"
    />

    <div class="score-content">
      <!-- 汇总概览卡片 (扁平纯白质感，统一全站设计语言) -->
      <div class="st-card summary-card">
        <div class="summary-header">
          <div class="student-info">
            <span class="st-icon-badge st-icon-badge--primary" style="width: 36px; height: 36px; font-size: 18px;">
              <van-icon name="award-o" />
            </span>
            <div>
              <div class="student-name">这一段时间的成长</div>
              <div class="student-sub">已记录 {{ examList.length }} 场考试 · 先看趋势，再看细节</div>
            </div>
          </div>
          <div v-if="latestExam" class="latest-badge">
            <span class="badge-label">最近总分</span>
            <span class="badge-val">{{ latestExam.total_score || '--' }}<small>/{{ latestExam.total_full_score || '--' }}</small></span>
          </div>
        </div>

        <div class="summary-stats-grid">
          <div class="stat-cell">
            <span class="stat-num">{{ examList.length }}</span>
            <span class="stat-tit">累计考试</span>
          </div>
          <div class="stat-cell">
            <span class="stat-num" :class="{ 'text-warn': weakSubjectsCount > 0, 'text-succ': weakSubjectsCount === 0 }">
              {{ weakSubjectsCount }}
            </span>
            <span class="stat-tit">薄弱科目</span>
          </div>
          <div class="stat-cell">
            <span class="stat-num">{{ latestRate !== null ? `${latestRate}%` : '--' }}</span>
            <span class="stat-tit">最新满分率</span>
          </div>
        </div>
      </div>

      <button class="growth-next-step" type="button" :aria-expanded="showInsights" @click="toggleInsights">
        <span>
          <b>{{ showInsights ? '成长解读与考试记录' : (weakSubjectsCount > 0 ? '下一步：复习需要关注的科目' : '下一步：保持今天的学习节奏') }}</b>
          <small>{{ showInsights ? '收起详细分析' : '查看完整分析、成绩与组卷管理' }}</small>
        </span>
        <van-icon :name="showInsights ? 'arrow-up' : 'arrow'" />
      </button>

      <template v-if="showInsights">
      <!-- 薄弱学科诊断预警条 -->
      <div v-if="weakSubjects.length > 0" class="weak-diagnostic-box">
        <div class="diagnostic-header">
          <div class="diag-title-row">
            <span class="st-icon-badge st-icon-badge--danger" style="width: 22px; height: 22px; font-size: var(--st-font-xs);">
              <van-icon name="warning" />
            </span>
            <span class="diag-title">薄弱学科诊断建议 ({{ weakSubjects.length }} 门)</span>
          </div>
          <span class="diag-tip">基于满分率 &lt; 60% 或 顽固错题 &ge; 3</span>
        </div>
        <div class="weak-tags-list">
          <div
            v-for="item in weakSubjects"
            :key="item.subject_id"
            class="weak-tag-card"
            @click="$router.push('/mistakes')"
          >
            <div class="weak-card-badge-col">
              <SubjectBadge :name="item.subject_name" size="sm" />
            </div>
            <div class="weak-card-body">
              <div class="weak-card-header-row">
                <div class="weak-card-title-group">
                  <span class="weak-sub-name">{{ item.subject_name }}</span>
                  <span class="weak-focus-pill">重点关注</span>
                </div>
                <div class="weak-card-action">
                  <span>前往错题本复习</span>
                  <van-icon name="arrow" class="action-arrow" />
                </div>
              </div>
              <div class="weak-card-desc">{{ item.reason }}</div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="weak-good-box">
        <span class="st-icon-badge st-icon-badge--success" style="width: 22px; height: 22px; font-size: var(--st-font-xs); margin-right: 6px;">
          <van-icon name="passed" />
        </span>
        <span class="good-text">各科基础扎实，目前未触发薄弱预警，继续保持！</span>
      </div>

      <!-- 走势折线图卡片 -->
      <div class="st-card chart-card">
        <div class="chart-card-header">
          <div class="card-title-group">
            <span class="st-icon-badge st-icon-badge--primary">
              <van-icon name="chart-trending-o" />
            </span>
            <span class="section-title">成绩走势分析</span>
          </div>
          <span class="card-sub">{{ selectedSubjectName }} 满分率变动</span>
        </div>

        <!-- 科目筛选切换 Chips -->
        <div class="subject-pills-scroll st-scroll-x">
          <span
            class="st-chip"
            :class="{ active: selectedSubjectId === null }"
            @click="changeTrendSubject(null, '全科总分')"
          >
            全科总分
          </span>
          <span
            v-for="sub in coreSubjects"
            :key="sub.id"
            class="st-chip"
            :class="{ active: selectedSubjectId === sub.id }"
            @click="changeTrendSubject(sub.id, sub.name)"
          >
            {{ sub.name }}
          </span>
        </div>

        <!-- 折线图 DOM -->
        <div ref="trendChartRef" class="echarts-container"></div>
        <div v-if="trendItems.length === 1" class="chart-footnote">
          <van-notice-bar left-icon="info-o" :scrollable="false" text="当前仅有 1 次考试数据，已作为独立参考点呈现，后续录入将自动生成连贯走势。" />
        </div>
        <div v-else-if="trendItems.length === 0" class="chart-empty-tip">
          暂无该科目的考试记录
        </div>
      </div>

      <!-- 7科均衡学力雷达图卡片 -->
      <div class="st-card chart-card">
        <div class="chart-card-header">
          <div class="card-title-group">
            <span class="st-icon-badge st-icon-badge--info">
              <van-icon name="aim" />
            </span>
            <span class="section-title">均衡学力雷达</span>
          </div>
          <div class="radar-exam-selector">
            <select v-model="selectedRadarExamId" @change="fetchRadarData" class="custom-select">
              <option v-for="ex in examList" :key="ex.id" :value="ex.id">
                {{ ex.title }} ({{ ex.exam_date }})
              </option>
            </select>
          </div>
        </div>

        <!-- 雷达图 DOM -->
        <div v-show="!radarMessage" ref="radarChartRef" class="echarts-container radar-height"></div>

        <!-- 缺考特别标注 -->
        <div v-if="radarAbsentSubjects.length > 0" class="absent-warning-banner">
          <van-icon name="warning" color="#ef4444" style="margin-right: 4px;" />
          <span><b>{{ radarAbsentSubjects.join('、') }}</b> 缺考，已按规则排除在雷达轴外，避免图形失真</span>
        </div>

        <!-- 不足 3 科 Fallback 友好提示 -->
        <div v-if="radarMessage" class="radar-fallback-box">
          <van-icon name="info-o" color="#94a3b8" size="24" style="margin-bottom: 4px;" />
          <p class="fallback-title">{{ radarMessage }}</p>
          <p class="fallback-sub">至少需要 3 门科目实考成绩才可构建闭合多边形</p>
        </div>
      </div>

      <!-- 历史考试台账 -->
      <div class="ledger-section">
        <div class="ledger-section-header">
          <div class="title-left">
            <span class="st-icon-badge st-icon-badge--info">
              <van-icon name="records" />
            </span>
            <span class="section-title">考试历史台账</span>
            <span class="ledger-count">({{ examList.length }} 场)</span>
          </div>
        </div>

        <div v-if="examLoading" class="ledger-state-box" aria-label="正在加载考试记录">
          <van-skeleton title :row="3" />
        </div>

        <div v-else-if="examLoadError" class="ledger-state-box ledger-error-state" role="status">
          <van-icon name="warning-o" class="ledger-state-icon" />
          <p class="custom-empty-title">考试记录暂时未能加载</p>
          <p class="custom-empty-subtitle">请检查网络后重新加载。</p>
          <button class="ledger-retry-btn" type="button" @click="reloadScoreData">重新加载</button>
        </div>

        <div v-else-if="examList.length > 0" class="ledger-list">
          <van-swipe-cell
            v-for="exam in examList"
            :key="exam.id"
            class="exam-swipe-cell"
          >
            <div class="st-card exam-card">
              <div class="exam-card-top">
                <div class="exam-meta">
                  <span class="exam-type-badge">{{ exam.exam_type }}</span>
                  <span class="exam-title">{{ exam.title }}</span>
                </div>
              </div>

              <div class="exam-date-row">
                <span><van-icon name="calendar-o" /> {{ exam.exam_date }}</span>
                <span v-if="exam.class_rank" class="rank-tag">班排 {{ exam.class_rank }}</span>
                <span v-if="exam.grade_rank" class="rank-tag">校排 {{ exam.grade_rank }}</span>
              </div>

              <!-- 分数总览条 -->
              <div class="exam-score-banner">
                <div class="banner-left">
                  <span class="total-label">实考总分：</span>
                  <span class="total-num">{{ exam.total_score !== null ? exam.total_score : '无实考' }}</span>
                  <span class="total-full">/ {{ exam.total_full_score || '--' }}</span>
                </div>
                <div class="banner-right">
                  <van-tag
                    :type="exam.rate >= 85 ? 'success' : exam.rate >= 60 ? 'primary' : 'danger'"
                    size="medium"
                    round
                  >
                    满分率 {{ exam.rate !== null ? `${exam.rate}%` : '--' }}
                  </van-tag>
                  <van-tag
                    v-if="exam.absent_count > 0"
                    color="#f59e0b"
                    plain
                    round
                    size="medium"
                    style="margin-left: 6px;"
                  >
                    {{ exam.absent_count }} 科缺考
                  </van-tag>
                </div>
              </div>

              <!-- 科目明细展开/收起 -->
              <div class="subject-chips-grid">
                <div
                  v-for="s in exam.scores"
                  :key="s.id"
                  class="sub-score-chip"
                  :class="{ 'chip-absent': s.is_absent }"
                >
                  <SubjectBadge :name="s.subject_name" size="sm" />
                  <span class="chip-name">{{ s.subject_name }}</span>
                  <span v-if="s.is_absent" class="chip-score absent-text">缺考</span>
                  <span v-else class="chip-score">
                    <b>{{ s.score }}</b>
                    <small>/{{ s.full_score }}</small>
                  </span>
                </div>
              </div>
            </div>

            <!-- 左滑呼出编辑与删除操作抽屉 -->
            <template #right>
              <div class="swipe-actions-box">
                <button class="swipe-action-btn btn-edit" @click.stop="handleRequestEdit(exam)">
                  <van-icon name="edit" size="16" />
                  <span>编辑</span>
                </button>
                <button class="swipe-action-btn btn-delete" @click.stop="handleDeleteExam(exam)">
                  <van-icon name="delete-o" size="16" />
                  <span>删除</span>
                </button>
              </div>
            </template>
          </van-swipe-cell>
        </div>

        <div v-else class="empty-ledger-box">
          <div class="custom-empty-state">
          <van-icon name="chart-trending-o" class="custom-empty-icon" />
            <p class="custom-empty-title">暂无考试记录</p>
            <p class="custom-empty-subtitle">点击下方按钮，录入第一场考试</p>
          </div>
        </div>
      </div>
      </template>
    </div>

    <!-- 删除成绩前的 PIN 验证抽屉 -->
    <van-popup
      v-model:show="showPinModal"
      position="bottom"
      round
      class="bottom-sheet-modal score-pin-sheet"
    >
      <div class="sheet-grabber"></div>
      <div class="score-pin-header">
        <div class="score-pin-title-row">
          <span class="st-icon-badge st-icon-badge--warning">
            <van-icon name="lock" />
          </span>
          <span class="score-pin-title">家长身份验证</span>
        </div>
        <van-icon name="cross" size="18" class="score-pin-close" @click="showPinModal = false" />
      </div>
      <p class="score-pin-copy">
        删除考试会同时移除全部科目成绩，请输入管理口令后继续：
      </p>
      <van-field
        v-model="parentPinInput"
        type="password"
        maxlength="6"
        placeholder="请输入口令 (默认 888888)"
        center
        class="score-pin-input"
      />
      <div class="score-pin-actions">
        <van-button round block plain @click="showPinModal = false">取消</van-button>
        <van-button type="primary" round block @click="handleConfirmPin">验证并继续</van-button>
      </div>
    </van-popup>

    <!-- 成绩录入 / 编辑弹窗 -->
    <van-popup
      v-model:show="showEditModal"
      position="bottom"
      round
      safe-area-inset-bottom
      class="edit-popup bottom-sheet-modal"
      :style="{ height: '90%' }"
    >
      <div class="popup-wrapper">
        <div class="popup-header">
          <span class="popup-title">{{ isEditing ? '编辑考试记录' : '录入新考试成绩' }}</span>
          <van-icon name="cross" size="20" @click="showEditModal = false" />
        </div>

        <div class="popup-scroll-body">
          <!-- 智能大段文字识别填表卡片（仅新建时显示） -->
          <div class="smart-parse-card" v-if="!isEditing">
            <div class="smart-parse-header">
              <div class="smart-parse-title">
                <span class="smart-parse-icon-badge">
                  <van-icon name="records" />
                </span>
                <span class="title-text">智能大段文字识别填表</span>
              </div>
              <span class="smart-parse-tag">微信/短信通知秒填</span>
            </div>

            <div class="smart-parse-input-box">
              <van-field
                v-model="rawScoreText"
                rows="3"
                autosize
                type="textarea"
                placeholder="直接粘贴微信群或短信成绩通知，例如：&#10;“期中考试成绩：语文108/120 数学116/120 英语112/120 道法89 历史92 地理85 生物缺考，班排第5名，校排第28名”"
                class="smart-parse-textarea"
              />
            </div>

            <div class="smart-parse-actions">
              <button type="button" class="sample-btn" @click="fillSampleText">
                <van-icon name="guide-o" /> 填入示例
              </button>
              <div class="actions-right">
                <button
                  type="button"
                  class="clear-text-btn"
                  v-if="rawScoreText"
                  @click="rawScoreText = ''"
                >
                  清空
                </button>
                <van-button
                  type="primary"
                  size="small"
                  round
                  icon="passed"
                  :disabled="!rawScoreText.trim()"
                  @click="handleParseAndFill"
                  class="parse-submit-btn"
                >
                  智能识别并填入
                </van-button>
              </div>
            </div>
          </div>

          <!-- 基本信息表单 -->
          <van-cell-group inset title="考试基本信息">
            <van-field
              v-model="formData.title"
              label="考试名称"
              placeholder="如：初一上学期期中考试"
              required
            />
            <van-field
              v-model="formData.exam_type"
              label="考试类型"
              placeholder="期中 / 期末 / 月考 / 周测 / 单元测试"
              required
            />
            <van-field
              v-model="formData.exam_date"
              label="考试日期"
              type="date"
              required
            />
            <van-field
              v-model="formData.class_rank"
              label="班级排名"
              type="digit"
              placeholder="选填"
            />
            <van-field
              v-model="formData.grade_rank"
              label="年级排名"
              type="digit"
              placeholder="选填"
            />
            <van-field
              v-model="formData.remarks"
              label="备注说明"
              placeholder="选填，如：因感冒缺考地理"
            />
          </van-cell-group>

          <!-- 实时总分计算计算条 -->
          <div class="live-calc-bar">
            <div class="calc-label">实时核算（自动剔除缺考）</div>
            <div class="calc-values">
              <span class="calc-main">总分: <b>{{ liveTotalScore }}</b> / {{ liveTotalFull }}</span>
              <span class="calc-sub">得分率: {{ liveRate !== null ? `${liveRate}%` : '--' }} · {{ liveAbsentCount }} 科缺考</span>
            </div>
          </div>

          <!-- 各科目成绩明细填写 -->
          <van-cell-group inset title="各科目成绩明细 (初一 7 科默认排齐)">
            <div
              v-for="(s, idx) in formData.scores"
              :key="s.subject_id"
              class="subject-edit-item"
            >
              <div class="sub-item-header">
                <span class="sub-name-tag">{{ s.subject_name }}</span>
                <div class="sub-absent-toggle">
                  <span class="toggle-label">缺考：</span>
                  <van-switch
                    v-model="s.is_absent"
                    size="18px"
                    @change="(val) => onAbsentChange(val, s)"
                  />
                </div>
              </div>

              <div class="sub-inputs-row">
                <van-field
                  v-model.number="s.score"
                  type="number"
                  label="实得分"
                  placeholder="分值"
                  :disabled="s.is_absent"
                  class="score-input-field"
                />
                <van-field
                  v-model.number="s.full_score"
                  type="number"
                  label="满分"
                  placeholder="满分"
                  class="full-input-field"
                />
              </div>
            </div>
          </van-cell-group>

          <!-- 底部提交按钮 -->
          <div class="popup-bottom-actions">
            <van-button
              type="primary"
              round
              block
              :loading="submitting"
              @click="submitExamForm"
            >
              {{ isEditing ? '保存修改' : '确认录入成绩' }}
            </van-button>
          </div>
        </div>
      </div>
    </van-popup>

    <!-- 底部常驻磨砂悬浮录入栏 -->
    <div class="floating-bottom-bar st-frosted-bar">
      <van-button
        type="primary"
        round
        block
        icon="plus"
        class="add-score-btn"
        @click="handleRequestCreate"
      >
        录入新考试成绩
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { showToast, showConfirmDialog } from 'vant';
import { examApi, settingsApi } from '../api';
import echarts from '../utils/echarts';
import { parseScoreText } from '../utils/scoreParser';
import SubjectBadge from '../components/SubjectBadge.vue';

// 页面基础状态
const examList = ref([]);
const subjects = ref([]);
const weakSubjects = ref([]);
const examLoading = ref(false);
const examLoadError = ref(false);
// 成长页与今天、作业一样，首屏直接呈现内容；按钮只负责收起长内容。
const showInsights = ref(true);

// 折线图状态
const trendChartRef = ref(null);
let trendChartInstance = null;
const selectedSubjectId = ref(null);
const selectedSubjectName = ref('全科总分');
const trendItems = ref([]);

// 雷达图状态
const radarChartRef = ref(null);
let radarChartInstance = null;
const selectedRadarExamId = ref(null);
const radarAbsentSubjects = ref([]);
const radarMessage = ref(null);

// 家长门禁口令状态
const showPinModal = ref(false);
const parentPinInput = ref('');
let pendingAction = null; // 'create' or { type: 'edit', exam: ... }

// 录入/编辑弹窗状态
const showEditModal = ref(false);
const isEditing = ref(false);
const editingExamId = ref(null);
const submitting = ref(false);

const formData = ref({
  title: '',
  exam_type: '期中',
  exam_date: new Date().toISOString().split('T')[0],
  class_rank: null,
  grade_rank: null,
  remarks: '',
  scores: []
});

// 大段成绩文本智能识别
const rawScoreText = ref('');

const fillSampleText = () => {
  rawScoreText.value = `各位家长好，初一上学期期中考试成绩已出：
语文：108/120
数学：116/120
英语：112/120
道法：89/100
历史：92/100
地理：85/100
生物：90/100
班级排名：5，年级排名：28`;
};

const handleParseAndFill = () => {
  if (!rawScoreText.value.trim()) return;
  const parsed = parseScoreText(rawScoreText.value, subjects.value);
  if (!parsed || (parsed.matchedCount === 0 && !parsed.title)) {
    showToast('未能识别出成绩信息，请检查文本格式');
    return;
  }

  if (parsed.title) formData.value.title = parsed.title;
  if (parsed.exam_type) formData.value.exam_type = parsed.exam_type;
  if (parsed.exam_date) formData.value.exam_date = parsed.exam_date;
  if (parsed.class_rank !== null) formData.value.class_rank = parsed.class_rank;
  if (parsed.grade_rank !== null) formData.value.grade_rank = parsed.grade_rank;
  if (parsed.remarks) formData.value.remarks = parsed.remarks;

  let fillCount = 0;
  // 遍历匹配到的科目，覆盖到 formData.value.scores
  parsed.parsedScores.forEach(ps => {
    const targetItem = formData.value.scores.find(s =>
      (ps.subject_id && s.subject_id === ps.subject_id) ||
      s.subject_name === ps.subject_name ||
      (ps.subject_name.includes(s.subject_name) || s.subject_name.includes(ps.subject_name))
    );
    if (targetItem) {
      targetItem.is_absent = !!ps.is_absent;
      targetItem.score = ps.score;
      if (ps.full_score) targetItem.full_score = ps.full_score;
      fillCount++;
    }
  });

  showToast({
    type: 'success',
    message: `已自动识别 ${fillCount} 门学科成绩与考试信息！`,
    icon: 'success'
  });
};

// 计算属性
const coreSubjects = computed(() => {
  return subjects.value.filter(s =>
    ['语文', '数学', '英语', '道法', '历史', '地理', '生物'].includes(s.name)
  );
});

const latestExam = computed(() => {
  return examList.value.length > 0 ? examList.value[0] : null;
});

const latestRate = computed(() => {
  if (!latestExam.value) return null;
  return latestExam.value.rate;
});

const weakSubjectsCount = computed(() => {
  return weakSubjects.value.filter(s => s.is_weak).length;
});

// 录入弹窗实时计算（缺考跳过分子分母）
const liveTotalScore = computed(() => {
  let sum = 0;
  let hasValid = false;
  for (const s of formData.value.scores) {
    if (!s.is_absent && s.score !== null && s.score !== '' && !isNaN(Number(s.score))) {
      sum += Number(s.score);
      hasValid = true;
    }
  }
  return hasValid ? Math.round(sum * 10) / 10 : 0;
});

const liveTotalFull = computed(() => {
  let sum = 0;
  let hasValid = false;
  for (const s of formData.value.scores) {
    if (!s.is_absent && s.score !== null && s.score !== '' && !isNaN(Number(s.score))) {
      sum += Number(s.full_score || 100);
      hasValid = true;
    }
  }
  return hasValid ? Math.round(sum * 10) / 10 : 0;
});

const liveAbsentCount = computed(() => {
  return formData.value.scores.filter(s => s.is_absent).length;
});

const liveRate = computed(() => {
  if (liveTotalFull.value <= 0) return null;
  return Math.round((liveTotalScore.value / liveTotalFull.value) * 1000) / 10;
});

const toggleInsights = async () => {
  showInsights.value = !showInsights.value;
  if (showInsights.value) {
    await nextTick();
    await fetchTrendData();
    await fetchRadarData();
  }
};

// 页面初始化
onMounted(async () => {
  await fetchSubjects();
  await fetchExamList();
  await fetchWeaknesses();
  await fetchTrendData();
  await fetchRadarData();

  window.addEventListener('resize', handleResize);
  window.addEventListener('zhixueji:action', onGlobalAction);
  if (new URLSearchParams(window.location.search).get('action') === 'add') openCreateModal();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  window.removeEventListener('zhixueji:action', onGlobalAction);
  if (trendChartInstance) trendChartInstance.dispose();
  if (radarChartInstance) radarChartInstance.dispose();
});

const handleResize = () => {
  if (trendChartInstance) trendChartInstance.resize();
  if (radarChartInstance) radarChartInstance.resize();
};

// 数据加载
const fetchSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    subjects.value = res.data || [];
  } catch (err) {
    console.error('获取科目列表失败', err);
  }
};

const fetchExamList = async () => {
  examLoading.value = true;
  examLoadError.value = false;
  try {
    const res = await examApi.getList();
    examList.value = res.data || [];
  } catch (err) {
    console.error('获取考试列表失败', err);
    examLoadError.value = true;
  } finally {
    examLoading.value = false;
  }
};

const reloadScoreData = async () => {
  await fetchExamList();
  if (!examLoadError.value) {
    await Promise.all([fetchWeaknesses(), fetchTrendData(), fetchRadarData()]);
  }
};

const fetchWeaknesses = async () => {
  try {
    const res = await examApi.getWeaknesses();
    weakSubjects.value = res.data.filter(s => s.is_weak) || [];
  } catch (err) {
    console.error('获取薄弱学科诊断失败', err);
  }
};

// 折线走势图交互与渲染
const changeTrendSubject = (subId, subName) => {
  selectedSubjectId.value = subId;
  selectedSubjectName.value = subName;
  fetchTrendData();
};

const fetchTrendData = async () => {
  try {
    const res = await examApi.getTrends(selectedSubjectId.value);
    trendItems.value = res.data?.items || [];
    renderTrendChart();
  } catch (err) {
    console.error('获取走势数据失败', err);
  }
};

const renderTrendChart = () => {
  nextTick(() => {
    if (!trendChartRef.value) return;
    if (!trendChartInstance) {
      trendChartInstance = echarts.init(trendChartRef.value);
    }

    if (trendItems.value.length === 0) {
      trendChartInstance.clear();
      return;
    }

    const xDates = trendItems.value.map(i => `${i.exam_date}\n(${i.exam_type})`);
    const rates = trendItems.value.map(i => (i.is_absent ? null : i.rate));
    const scores = trendItems.value.map(i => (i.is_absent ? '缺考' : `${i.score}/${i.full_score}`));

    const option = {
      tooltip: {
        trigger: 'axis',
        textStyle: { fontSize: 12 },
        formatter: (params) => {
          const p = params[0];
          const item = trendItems.value[p.dataIndex];
          if (item.is_absent) {
            return `<b>${item.title}</b><br/>状态：缺考`;
          }
          return `<b>${item.title}</b><br/>日期：${item.exam_date}<br/>实得分：${item.score} / ${item.full_score}<br/>满分率：${item.rate}%`;
        }
      },
      grid: {
        top: 30,
        right: 20,
        bottom: 48,
        left: 50
      },
      xAxis: {
        type: 'category',
        data: xDates,
        axisLabel: {
          fontSize: 12,
          interval: 'auto',
          color: '#64748b'
        },
        axisLine: { lineStyle: { color: '#e2e8f0' } }
      },
      yAxis: {
        type: 'value',
        name: '满分率(%)',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%',
          fontSize: 12,
          color: '#64748b'
        },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
      },
      series: [
        {
          name: '得分率',
          type: 'line',
          data: rates,
          smooth: true,
          showSymbol: true,
          symbolSize: 8,
          itemStyle: { color: '#2563eb' },
          lineStyle: { width: 3, color: '#2563eb' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(37, 99, 235, 0.25)' },
              { offset: 1, color: 'rgba(37, 99, 235, 0.01)' }
            ])
          },
          label: {
            show: true,
            position: 'top',
            formatter: (p) => `${p.value}%`,
            fontSize: 12,
            color: '#1e293b'
          }
        }
      ]
    };

    trendChartInstance.setOption(option, true);
  });
};

// 雷达图交互与渲染（核心缺考动态轴防御）
const fetchRadarData = async () => {
  try {
    const res = await examApi.getRadar(selectedRadarExamId.value || undefined);
    const data = res.data;
    radarAbsentSubjects.value = data?.absent_subjects || [];
    radarMessage.value = data?.message || null;
    if (data?.exam_id) {
      selectedRadarExamId.value = data.exam_id;
    }

    renderRadarChart(data);
  } catch (err) {
    console.error('获取雷达图数据失败', err);
  }
};

const renderRadarChart = (data) => {
  nextTick(() => {
    if (!radarChartRef.value) return;
    if (!radarChartInstance) {
      radarChartInstance = echarts.init(radarChartRef.value);
    }

    if (radarMessage.value || !data?.indicators || data.indicators.length < 3) {
      radarChartInstance.clear();
      return;
    }

    const indicatorOptions = data.indicators.map(ind => ({
      name: ind.name,
      max: 100
    }));

    const option = {
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          const list = data.indicators.map((ind, i) => `${ind.name}: ${params.value[i]}%`);
          return `<b>${data.exam_title || '学力均衡'}</b><br/>${list.join('<br/>')}`;
        }
      },
      radar: {
        indicator: indicatorOptions,
        radius: '68%',
        splitNumber: 4,
        axisName: {
          color: '#334155',
          fontSize: 12,
          fontWeight: 500
        },
        splitLine: {
          lineStyle: { color: ['#e2e8f0', '#cbd5e1'] }
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: ['rgba(248,250,252,0.8)', 'rgba(241,245,249,0.8)']
          }
        }
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: data.values,
              name: '得分率 (%)',
              symbolSize: 6,
              itemStyle: { color: '#0ea5e9' },
              lineStyle: { width: 2, color: '#0ea5e9' },
              areaStyle: {
                color: 'rgba(14, 165, 233, 0.3)'
              }
            }
          ]
        }
      ]
    };

    radarChartInstance.setOption(option, true);
  });
};

// 家长门禁逻辑
const checkParentUnlocked = () => {
  return !!sessionStorage.getItem('parent_pin');
};

const handleRequestCreate = () => {
  openCreateModal();
};

const handleRequestEdit = (exam) => {
  openEditModal(exam);
};

const handleConfirmPin = async () => {
  if (!parentPinInput.value) {
    showToast('请输入口令');
    return;
  }
  try {
    await settingsApi.verifyPin(parentPinInput.value);
    sessionStorage.setItem('parent_pin', parentPinInput.value);
    sessionStorage.setItem('parent_unlocked', 'true');
    showToast({ message: '验证成功', icon: 'success' });
    showPinModal.value = false;

    if (pendingAction?.type === 'delete') {
      handleDeleteExam(pendingAction.exam);
    }
  } catch (err) {
    const msg = err.response?.data?.detail || '口令错误';
    showToast({ message: msg, icon: 'cross' });
  }
};

// 打开创建模态框：排齐初一 7 科
const openCreateModal = () => {
  isEditing.value = false;
  editingExamId.value = null;

  const order7 = ['语文', '数学', '英语', '道法', '历史', '地理', '生物'];
  const sortedSubs = [...subjects.value].sort((a, b) => {
    const ia = order7.indexOf(a.name);
    const ib = order7.indexOf(b.name);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.id - b.id;
  });

  const initScores = sortedSubs.map(sub => ({
    subject_id: sub.id,
    subject_name: sub.name,
    score: null,
    full_score: ['语文', '数学', '英语'].includes(sub.name) ? 120 : (sub.full_score || 100),
    is_absent: false
  }));

  rawScoreText.value = '';

  formData.value = {
    title: '',
    exam_type: '期中',
    exam_date: new Date().toISOString().split('T')[0],
    class_rank: null,
    grade_rank: null,
    remarks: '',
    scores: initScores
  };

  showEditModal.value = true;
};

// 打开编辑模态框
const openEditModal = (exam) => {
  isEditing.value = true;
  editingExamId.value = exam.id;

  const order7 = ['语文', '数学', '英语', '道法', '历史', '地理', '生物'];
  const sortedSubs = [...subjects.value].sort((a, b) => {
    const ia = order7.indexOf(a.name);
    const ib = order7.indexOf(b.name);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.id - b.id;
  });

  const scoresMap = {};
  for (const s of exam.scores) {
    scoresMap[s.subject_id] = s;
  }

  const scoresList = sortedSubs.map(sub => {
    const exist = scoresMap[sub.id];
    return {
      subject_id: sub.id,
      subject_name: sub.name,
      score: exist && !exist.is_absent ? exist.score : null,
      full_score: exist ? exist.full_score : (['语文', '数学', '英语'].includes(sub.name) ? 120 : 100),
      is_absent: exist ? !!exist.is_absent : false
    };
  });

  formData.value = {
    title: exam.title,
    exam_type: exam.exam_type || '期中',
    exam_date: exam.exam_date,
    class_rank: exam.class_rank,
    grade_rank: exam.grade_rank,
    remarks: exam.remarks || '',
    scores: scoresList
  };

  showEditModal.value = true;
};

const onAbsentChange = (val, s) => {
  if (val) {
    s.score = null;
  }
};

// 提交表单（创建或更新）
const submitExamForm = async () => {
  if (!formData.value.title.trim()) {
    showToast('请填写考试名称');
    return;
  }
  if (!formData.value.exam_date) {
    showToast('请选择考试日期');
    return;
  }

  submitting.value = true;
  try {
    const validScores = formData.value.scores
      .filter(s => s.is_absent || (s.score !== null && s.score !== '' && !isNaN(Number(s.score))))
      .map(s => ({
        subject_id: s.subject_id,
        score: s.is_absent ? null : Number(s.score),
        full_score: Number(s.full_score || 100),
        is_absent: !!s.is_absent
      }));

    if (validScores.length === 0) {
      showToast('请至少录入一门科目的成绩或缺考状态');
      submitting.value = false;
      return;
    }

    const payload = {
      title: formData.value.title.trim(),
      exam_type: formData.value.exam_type || '期中',
      exam_date: formData.value.exam_date,
      class_rank: formData.value.class_rank ? Number(formData.value.class_rank) : null,
      grade_rank: formData.value.grade_rank ? Number(formData.value.grade_rank) : null,
      remarks: formData.value.remarks || null,
      scores: validScores
    };

    if (isEditing.value) {
      await examApi.update(editingExamId.value, payload);
      showToast({ message: '考试成绩已更新', icon: 'success' });
    } else {
      await examApi.create(payload);
      showToast({ message: '成绩录入成功', icon: 'success' });
    }

    showEditModal.value = false;
    await fetchExamList();
    await fetchWeaknesses();
    await fetchTrendData();
    await fetchRadarData();
  } catch (err) {
    const msg = err.response?.data?.detail || '保存失败，请检查数据格式';
    showToast({ message: msg, icon: 'cross' });
  } finally {
    submitting.value = false;
  }
};

// 删除考试
const handleDeleteExam = (exam) => {
  if (!checkParentUnlocked()) {
    pendingAction = { type: 'delete', exam }; // 先验证 PIN
    parentPinInput.value = '';
    showPinModal.value = true;
    return;
  }

  showConfirmDialog({
    title: '确认删除考试',
    message: `确定要删除「${exam.title}」及其所有科目成绩吗？此操作不可恢复。`,
    confirmButtonColor: '#ef4444'
  }).then(async () => {
    try {
      await examApi.delete(exam.id);
      showToast({ message: '已删除', icon: 'success' });
      await fetchExamList();
      await fetchWeaknesses();
      await fetchTrendData();
      await fetchRadarData();
    } catch (err) {
      showToast('删除失败');
    }
  }).catch(() => {});
};

const onGlobalAction = (event) => {
  if (event.detail === 'score') handleRequestCreate();
};
</script>

<style scoped>
.score-view {
  flex: 1;
  background-color: var(--st-bg-page);
  padding-bottom: 92px;
}

.score-content {
  padding: var(--st-space-4) var(--st-space-5);
  display: flex;
  flex-direction: column;
  gap: var(--st-space-4);
}

/* 概览卡片 */
.summary-card {
  padding: var(--st-space-card) var(--st-space-5);
  color: var(--st-text-primary);
}

.growth-next-step { display: flex; width: 100%; min-height: 60px; align-items: center; justify-content: space-between; padding: var(--st-space-4) var(--st-space-5); border: 1px solid var(--st-border-focus); border-radius: var(--st-radius-lg); background: var(--st-primary-light); color: var(--st-primary); text-align: left; }
.growth-next-step b, .growth-next-step small { display: block; }
.growth-next-step b { color: var(--st-text-primary); font-size: var(--st-font-md); font-weight: 600; }
.growth-next-step small { margin-top: 3px; color: var(--st-text-secondary); font-size: var(--st-font-xs); }

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--st-space-4);
}

.student-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.student-name {
  font-size: var(--st-font-xl);
  font-weight: 600;
  color: var(--st-text-primary);
}

.student-sub {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin-top: 2px;
}

.latest-badge {
  text-align: right;
  background: var(--st-primary-light, #eff6ff);
  padding: 6px 12px;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.15);
}

.badge-label {
  display: block;
  font-size: var(--st-font-xs);
  color: var(--st-primary, #2563eb);
}

.badge-val {
  font-size: var(--st-font-xl);
  font-weight: 700;
  color: var(--st-primary, #2563eb);
}

.badge-val small {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.summary-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--st-space-3);
  background: var(--st-bg-subtle);
  padding: var(--st-space-3);
  border-radius: var(--st-radius-md);
  border: 1px solid var(--st-border);
  text-align: center;
}

.stat-cell {
  display: flex;
  flex-direction: column;
}

.stat-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--st-text-primary);
}

.stat-tit {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin-top: 2px;
}

.text-warn {
  color: var(--st-danger, #ef4444) !important;
}

.text-succ {
  color: var(--st-success, #10b981) !important;
}

/* 薄弱预警诊断 */
.weak-diagnostic-box {
  background: var(--st-bg-card);
  border-radius: var(--st-radius-lg);
  padding: var(--st-space-4);
  border: 1px solid #fecaca;
  box-shadow: var(--st-shadow-card);
}

.diag-title-row {
  display: flex;
  align-items: center;
  gap: var(--st-space-2);
  flex: 0 0 auto;   /* 标题不参与压缩，否则 "(3 门)" 会被挤到第二行 */
}

.diagnostic-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  column-gap: var(--st-space-3);
  row-gap: var(--st-space-2);
  margin-bottom: var(--st-space-3);
}

.diag-title {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: #b91c1c;
  white-space: nowrap;
}

.diag-tip {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  line-height: var(--st-leading-normal);
}

.weak-tags-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.weak-tag-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: var(--st-danger-light, #fef2f2);
  border: 1px solid #fecaca;
  border-radius: var(--st-radius-md, 8px);
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.weak-tag-card:active {
  opacity: 0.88;
  transform: translateY(1px);
}

.weak-card-badge-col {
  flex-shrink: 0;
  margin-top: 1px;
}

.weak-card-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.weak-card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.weak-card-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.weak-sub-name {
  font-size: var(--st-font-sm, 14px);
  font-weight: 600;
  color: #991b1b;
  line-height: 1.2;
}

.weak-focus-pill {
  font-size: 11px;
  font-weight: 500;
  color: #dc2626;
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.25);
  border-radius: 4px;
  padding: 1px 6px;
  line-height: 1.25;
  white-space: nowrap;
}

.weak-card-action {
  font-size: var(--st-font-xs, 12px);
  color: #2563eb;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
  flex-shrink: 0;
}

.weak-card-action .action-arrow {
  font-size: 11px;
  margin-top: 1px;
}

.weak-card-desc {
  font-size: var(--st-font-xs, 12px);
  color: #b91c1c;
  line-height: 1.4;
  margin: 0;
}

.weak-good-box {
  background: var(--st-success-light);
  border: 1px solid #bbf7d0;
  border-radius: var(--st-radius-lg);
  padding: var(--st-space-3) var(--st-space-4);
  display: flex;
  align-items: center;
  gap: 8px;
}

.good-icon {
  font-size: 18px;
}

.good-text {
  font-size: var(--st-font-xs);
  color: #166534;
  font-weight: 500;
}

/* 图表卡片通用样式 */
.chart-card {
  padding: var(--st-space-card) var(--st-space-5);
}

.chart-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--st-space-4);
}

.card-title-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-icon {
  font-size: var(--st-font-xl);
}

.card-title {
  font-size: var(--st-font-lg);
  font-weight: 600;
  color: #0f172a;
  white-space: nowrap !important;
}

.card-sub {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

/* 科目滚动切换 Pills */
.subject-pills-scroll {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 8px;
  margin-bottom: 4px;
  scrollbar-width: none;
}

.subject-pills-scroll::-webkit-scrollbar {
  display: none;
}

.pill-btn {
  white-space: nowrap;
  padding: 4px 10px;
  font-size: var(--st-font-xs);
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pill-btn.active {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
  font-weight: 600;
}

.echarts-container {
  width: 100%;
  height: 250px;
}

.radar-height {
  height: 270px;
}

.chart-footnote {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  background: #f1f5f9;
  padding: 6px 10px;
  border-radius: 8px;
  margin-top: 6px;
}

.chart-empty-tip {
  text-align: center;
  padding: 40px 0;
  font-size: var(--st-font-sm);
  color: var(--st-text-muted);
}

.custom-select {
  font-size: var(--st-font-xs);
  padding: 6px 8px;
  border-radius: var(--st-radius-sm);
  border: 1px solid var(--st-border-bold);
  background: var(--st-bg-subtle);
  color: var(--st-text-regular);
  outline: none;
  max-width: 150px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.absent-warning-banner {
  margin-top: 6px;
  padding: 8px 10px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-size: var(--st-font-xs);
  color: #b45309;
  display: flex;
  align-items: center;
  gap: 6px;
}

.radar-fallback-box {
  text-align: center;
  padding: 30px 10px;
  background: #f8fafc;
  border-radius: 12px;
  margin-top: 8px;
}

.fallback-icon {
  font-size: 28px;
}

.fallback-title {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: #475569;
  margin: 6px 0 2px;
}

.fallback-sub {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
}

/* 考试历史台账 */
.ledger-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ledger-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 2px;
}

.ledger-count {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.ledger-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.exam-card {
  padding: var(--st-space-4) var(--st-space-5);
}

.exam-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.exam-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.exam-type-badge {
  font-size: var(--st-font-xs);
  font-weight: 600;
  background: var(--st-primary-light);
  color: var(--st-primary);
  padding: 2px 6px;
  border-radius: var(--st-radius-sm);
}

.exam-title {
  font-size: var(--st-font-md);
  font-weight: 600;
  color: var(--st-text-primary);
}

.exam-date-row {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin: 6px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.rank-tag {
  background: var(--st-bg-subtle);
  color: var(--st-text-secondary);
  padding: 1px 6px;
  border-radius: var(--st-radius-sm);
  font-size: var(--st-font-xs);
}

.exam-score-banner {
  background: var(--st-bg-subtle);
  border-radius: var(--st-radius-md);
  padding: var(--st-space-3) var(--st-space-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.total-label {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.total-num {
  font-size: var(--st-font-xl);
  font-weight: 700;
  color: var(--st-text-primary);
  font-variant-numeric: tabular-nums;
}

.total-full {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
}

.subject-chips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(105px, 1fr));
  gap: 6px;
}

.sub-score-chip {
  background: var(--st-bg-subtle);
  border-radius: var(--st-radius-sm);
  padding: 4px var(--st-space-2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--st-font-xs);
}

.sub-score-chip.chip-absent {
  background: #fef2f2;
}

.chip-name {
  color: var(--st-text-secondary);
}

.chip-score {
  color: var(--st-text-primary);
}

.chip-score small {
  color: var(--st-text-muted);
}

.absent-text {
  color: #ef4444;
  font-weight: 500;
}

.empty-ledger-box {
  background: var(--st-bg-card);
  border: 1px solid var(--st-border);
  border-radius: var(--st-radius-lg);
}

.ledger-state-box {
  padding: var(--st-space-6) var(--st-space-5);
  background: var(--st-bg-card);
  border: 1px solid var(--st-border);
  border-radius: var(--st-radius-lg);
}

.ledger-error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.ledger-state-icon {
  margin-bottom: var(--st-space-3);
  color: var(--st-warning-dark);
  font-size: 30px;
}

.ledger-retry-btn {
  min-height: 42px;
  margin-top: var(--st-space-4);
  padding: 0 var(--st-space-5);
  border: 0;
  border-radius: var(--st-radius-full);
  background: var(--st-primary);
  color: #ffffff;
  font: inherit;
  font-size: var(--st-font-md);
  font-weight: 600;
}

.empty-ledger-box .custom-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 30px 16px;
}

.empty-ledger-box .custom-empty-icon {
  color: var(--st-primary);
  font-size: 40px;
  line-height: 1;
  margin-bottom: 14px;
}

.empty-ledger-box .custom-empty-title {
  font-size: var(--st-font-lg);
  font-weight: 600;
  color: var(--st-text-primary);
  margin: 0 0 6px;
}

.empty-ledger-box .custom-empty-subtitle {
  font-size: var(--st-font-sm);
  color: var(--st-text-secondary);
  margin: 0;
  max-width: 220px;
  line-height: 1.5;
}

/* 录入/编辑弹窗 */
.popup-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--st-space-4) var(--st-space-5);
  border-bottom: 1px solid var(--st-border);
  background: var(--st-bg-card);
}

.popup-title {
  font-size: var(--st-font-xl);
  font-weight: 600;
  color: var(--st-text-primary);
}

.popup-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding-bottom: calc(var(--st-space-6) + max(env(safe-area-inset-bottom, 0px), var(--st-keyboard-inset)));
  background: var(--st-bg-page);
}

/* 智能大段文字识别填表卡片 */
.smart-parse-card {
  margin: var(--st-space-4) var(--st-space-4) var(--st-space-2);
  background: var(--st-bg-subtle);
  border: 1px solid var(--st-border);
  border-radius: var(--st-radius-lg);
  padding: var(--st-space-4);
  box-shadow: var(--st-shadow-card);
}

.smart-parse-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.smart-parse-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: #1e293b;
}

.smart-parse-icon-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: #2563eb;
  color: #ffffff;
  font-size: var(--st-font-xs);
}

.smart-parse-tag {
  font-size: var(--st-font-xs);
  color: #2563eb;
  background: #dbeafe;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.smart-parse-input-box {
  background: var(--st-bg-card);
  border-radius: var(--st-radius-sm);
  border: 1px solid var(--st-border);
  overflow: hidden;
  margin-bottom: 8px;
}

.smart-parse-textarea {
  font-size: var(--st-font-sm);
  line-height: var(--st-leading-normal);
  padding: 8px 10px;
}

.smart-parse-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sample-btn {
  background: transparent;
  border: 1px dashed #94a3b8;
  color: var(--st-text-secondary);
  font-size: var(--st-font-xs);
  border-radius: 14px;
  padding: 3px 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  transition: all 0.2s;
}

.sample-btn:active {
  background: #e2e8f0;
  color: #334155;
}

.actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.clear-text-btn {
  background: transparent;
  border: none;
  color: var(--st-text-muted);
  font-size: var(--st-font-xs);
  cursor: pointer;
  padding: 4px 6px;
}

.clear-text-btn:active {
  color: var(--st-text-secondary);
}

.parse-submit-btn {
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

.live-calc-bar {
  margin: var(--st-space-3) var(--st-space-4);
  padding: var(--st-space-3) var(--st-space-4);
  background: var(--st-primary-light);
  border-radius: var(--st-radius-md);
  border: 1px solid var(--st-border-focus);
}

.calc-label {
  font-size: var(--st-font-xs);
  color: var(--st-primary-dark);
  font-weight: 500;
}

.calc-values {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-top: 4px;
}

.calc-main {
  font-size: var(--st-font-lg);
  color: var(--st-text-primary);
}

.calc-main b {
  font-size: var(--st-font-xl);
  color: var(--st-primary);
}

.calc-sub {
  font-size: var(--st-font-xs);
  color: #3b82f6;
}

.subject-edit-item {
  padding: var(--st-space-3) var(--st-space-4);
  border-bottom: 1px solid var(--st-border);
}

.sub-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.sub-name-tag {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
}

.sub-absent-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toggle-label {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.sub-inputs-row {
  display: flex;
  gap: 8px;
}

.score-input-field,
.full-input-field {
  padding: 4px 8px;
  background: var(--st-bg-subtle);
  border-radius: var(--st-radius-sm);
}

.popup-bottom-actions {
  padding: var(--st-space-4);
}

.score-pin-sheet {
  padding: var(--st-space-4) var(--st-space-5) calc(var(--st-space-6) + env(safe-area-inset-bottom, 0px));
  background: var(--st-bg-card);
}

.sheet-grabber {
  width: 36px;
  height: 4px;
  margin: 0 auto var(--st-space-4);
  border-radius: var(--st-radius-full);
  background: var(--st-border-bold);
}

.score-pin-header, .score-pin-title-row, .score-pin-actions {
  display: flex;
  align-items: center;
}

.score-pin-header { justify-content: space-between; margin-bottom: var(--st-space-3); }
.score-pin-title-row { gap: var(--st-space-2); }
.score-pin-title { font-size: var(--st-font-xl); font-weight: 600; color: var(--st-text-primary); }
.score-pin-close { cursor: pointer; color: var(--st-text-muted); }
.score-pin-copy { margin: 0 0 var(--st-space-4); font-size: var(--st-font-sm); color: var(--st-text-secondary); line-height: var(--st-leading-normal); }
.score-pin-input { margin-bottom: var(--st-space-4); background: var(--st-bg-subtle); border: 1px solid var(--st-border); border-radius: var(--st-radius-md); }
.score-pin-actions { gap: var(--st-space-3); }

/* 左滑操作与底部常驻悬浮栏 */
.exam-swipe-cell {
  border-radius: var(--st-radius-md, 14px);
  overflow: hidden;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}

.exam-swipe-cell .exam-card {
  border-radius: 0;
  box-shadow: none;
  margin-bottom: 0;
}

.swipe-actions-box {
  display: flex;
  height: 100%;
}

.swipe-action-btn {
  border: none;
  height: 100%;
  padding: 0 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #ffffff;
  font-size: var(--st-font-xs);
  font-weight: 500;
  cursor: pointer;
}

.swipe-action-btn.btn-edit {
  background-color: var(--st-warning, #f59e0b);
}

.swipe-action-btn.btn-delete {
  background-color: var(--st-danger, #ef4444);
}

.floating-bottom-bar {
  position: fixed;
  bottom: calc(50px + env(safe-area-inset-bottom, 0px));
  left: 0;
  right: 0;
  max-width: 500px;
  margin: 0 auto;
  padding: 8px 16px;
  background: linear-gradient(to top, rgba(248, 250, 252, 0.96) 80%, rgba(248, 250, 252, 0));
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 40;
}

.add-score-btn {
  font-weight: 700;
  height: 46px;
  font-size: 15px;
  border-radius: var(--st-radius-full, 9999px);
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
}

.floating-bottom-bar { display: none; }
</style>

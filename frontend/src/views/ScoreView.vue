<template>
  <div class="score-view">
    <!-- 顶部导航栏 -->
    <van-nav-bar
      title="学情成绩分析"
      left-arrow
      right-text="录入成绩"
      @click-left="$router.push('/')"
      @click-right="handleRequestCreate"
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
              <div class="student-name">初一学情档案</div>
              <div class="student-sub">已记录 {{ examList.length }} 场考试 · 7 科均衡追踪</div>
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

      <!-- 薄弱学科诊断预警条 -->
      <div v-if="weakSubjects.length > 0" class="weak-diagnostic-box">
        <div class="diagnostic-header">
          <div class="diag-title-row">
            <span class="st-icon-badge st-icon-badge--danger" style="width: 22px; height: 22px; font-size: 12px;">
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
            <div class="weak-card-top">
              <span class="weak-sub-name">{{ item.subject_name }}</span>
              <van-tag type="danger" plain size="medium">重点关注</van-tag>
            </div>
            <div class="weak-card-desc">{{ item.reason }}</div>
            <div class="weak-card-action">
              <span>前往错题本复习 &gt;</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="weak-good-box">
        <span class="st-icon-badge st-icon-badge--success" style="width: 22px; height: 22px; font-size: 12px; margin-right: 6px;">
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
            <span class="card-title">成绩走势分析</span>
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
            <span class="card-title">7 科均衡学力雷达</span>
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
          <div class="card-title-group">
            <span class="st-icon-badge st-icon-badge--neutral">
              <van-icon name="orders-o" />
            </span>
            <span class="card-title">考试历史台账</span>
            <span class="ledger-count">({{ examList.length }} 场)</span>
          </div>
          <van-button
            size="mini"
            type="primary"
            plain
            round
            icon="plus"
            style="padding: 0 10px; height: 26px; font-weight: 600;"
            @click="handleRequestCreate"
          >
            录入考试
          </van-button>
        </div>

        <div v-if="examList.length > 0" class="ledger-list">
          <div
            v-for="exam in examList"
            :key="exam.id"
            class="st-card exam-card"
          >
            <div class="exam-card-top">
              <div class="exam-meta">
                <span class="exam-type-badge">{{ exam.exam_type }}</span>
                <span class="exam-title">{{ exam.title }}</span>
              </div>
              <div class="exam-card-actions">
                <van-button
                  size="mini"
                  icon="edit"
                  type="primary"
                  plain
                  round
                  @click="handleRequestEdit(exam)"
                >
                  编辑
                </van-button>
                <van-button
                  size="mini"
                  icon="delete-o"
                  type="danger"
                  plain
                  round
                  style="margin-left: 6px;"
                  @click="handleDeleteExam(exam)"
                >
                  删除
                </van-button>
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
                <span class="chip-name">{{ s.subject_name }}</span>
                <span v-if="s.is_absent" class="chip-score absent-text">缺考</span>
                <span v-else class="chip-score">
                  <b>{{ s.score }}</b>
                  <small>/{{ s.full_score }}</small>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-ledger-box">
          <van-empty description="暂无考试记录，点击右上角录入第一场考试吧" />
        </div>
      </div>
    </div>

    <!-- 家长 PIN 码门禁抽屉（保护录入与修改） -->
    <van-popup
      v-model:show="showPinModal"
      position="bottom"
      round
      class="bottom-sheet-modal"
      :style="{ padding: '16px 20px 32px' }"
    >
      <div style="width: 36px; height: 4px; background: #e2e8f0; border-radius: 2px; margin: 0 auto 16px;"></div>
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="st-icon-badge st-icon-badge--warning">
            <van-icon name="lock" />
          </span>
          <span style="font-size: 16px; font-weight: 600; color: #0f172a;">家长身份验证</span>
        </div>
        <van-icon name="cross" size="18" color="#94a3b8" style="cursor: pointer;" @click="showPinModal = false" />
      </div>
      <p style="font-size: 13px; color: #64748b; margin-bottom: 16px; line-height: 1.5;">
        考试成绩录入与修改属于家长权限，请输入 6 位管理口令：
      </p>
      <van-field
        v-model="parentPinInput"
        type="password"
        maxlength="6"
        placeholder="请输入口令 (默认 888888)"
        center
        style="background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 16px;"
      />
      <div style="display: flex; gap: 10px;">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { showToast, showConfirmDialog } from 'vant';
import { examApi, settingsApi } from '../api';
import echarts from '../utils/echarts';

// 页面基础状态
const examList = ref([]);
const subjects = ref([]);
const weakSubjects = ref([]);

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

// 计算属性
const coreSubjects = computed(() => {
  return subjects.value.filter(s =>
    ['语文', '数学', '英语', '道德与法治', '历史', '地理', '生物'].includes(s.name)
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

// 页面初始化
onMounted(async () => {
  await fetchSubjects();
  await fetchExamList();
  await fetchWeaknesses();
  await fetchTrendData();
  await fetchRadarData();

  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
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
  try {
    const res = await examApi.getList();
    examList.value = res.data || [];
  } catch (err) {
    console.error('获取考试列表失败', err);
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
        right: 15,
        bottom: 40,
        left: 45
      },
      xAxis: {
        type: 'category',
        data: xDates,
        axisLabel: {
          fontSize: 11,
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
          fontSize: 11,
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
            fontSize: 10,
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
  if (checkParentUnlocked()) {
    openCreateModal();
  } else {
    pendingAction = 'create';
    parentPinInput.value = '';
    showPinModal.value = true;
  }
};

const handleRequestEdit = (exam) => {
  if (checkParentUnlocked()) {
    openEditModal(exam);
  } else {
    pendingAction = { type: 'edit', exam };
    parentPinInput.value = '';
    showPinModal.value = true;
  }
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

    if (pendingAction === 'create') {
      openCreateModal();
    } else if (pendingAction?.type === 'edit') {
      openEditModal(pendingAction.exam);
    } else if (pendingAction?.type === 'delete') {
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

  const order7 = ['语文', '数学', '英语', '道德与法治', '历史', '地理', '生物'];
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

  const order7 = ['语文', '数学', '英语', '道德与法治', '历史', '地理', '生物'];
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
</script>

<style scoped>
.score-view {
  min-height: 100vh;
  background-color: #f8fafc;
  padding-bottom: 70px;
}

.score-content {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 概览卡片 */
.summary-card {
  background: var(--st-bg-card, #ffffff);
  border-radius: var(--st-radius-md, 14px);
  padding: 16px;
  color: var(--st-text-primary, #0f172a);
  box-shadow: var(--st-shadow-card);
  border: 1px solid var(--st-border, #f1f5f9);
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.student-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.student-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--st-text-primary, #0f172a);
}

.student-sub {
  font-size: 11px;
  color: var(--st-text-secondary, #64748b);
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
  font-size: 10px;
  color: var(--st-primary, #2563eb);
}

.badge-val {
  font-size: 16px;
  font-weight: 700;
  color: var(--st-primary, #2563eb);
}

.badge-val small {
  font-size: 11px;
  color: var(--st-text-secondary, #64748b);
}

.summary-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  background: var(--st-bg-page, #f8fafc);
  padding: 10px;
  border-radius: 10px;
  border: 1px solid var(--st-border, #f1f5f9);
  text-align: center;
}

.stat-cell {
  display: flex;
  flex-direction: column;
}

.stat-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--st-text-primary, #0f172a);
}

.stat-tit {
  font-size: 11px;
  color: var(--st-text-secondary, #64748b);
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
  background: #fff;
  border-radius: var(--st-radius-md, 14px);
  padding: 12px;
  border-left: 4px solid var(--st-danger, #ef4444);
  box-shadow: var(--st-shadow-card);
  border-top: 1px solid var(--st-border, #f1f5f9);
  border-right: 1px solid var(--st-border, #f1f5f9);
  border-bottom: 1px solid var(--st-border, #f1f5f9);
}

.diag-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.diagnostic-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.diag-title {
  font-size: 13px;
  font-weight: 600;
  color: #b91c1c;
}

.diag-tip {
  font-size: 10px;
  color: #94a3b8;
}

.weak-tags-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.weak-tag-card {
  background: #fef2f2;
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
}

.weak-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.weak-sub-name {
  font-size: 13px;
  font-weight: 600;
  color: #991b1b;
}

.weak-card-desc {
  font-size: 12px;
  color: #dc2626;
  margin: 4px 0;
}

.weak-card-action {
  font-size: 11px;
  color: #2563eb;
  text-align: right;
  font-weight: 500;
}

.weak-good-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.good-icon {
  font-size: 18px;
}

.good-text {
  font-size: 12px;
  color: #166534;
  font-weight: 500;
}

/* 图表卡片通用样式 */
.chart-card {
  background: #fff;
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.chart-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-title-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-icon {
  font-size: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.card-sub {
  font-size: 11px;
  color: #64748b;
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
  font-size: 11px;
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
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  padding: 6px 10px;
  border-radius: 8px;
  margin-top: 6px;
}

.chart-empty-tip {
  text-align: center;
  padding: 40px 0;
  font-size: 13px;
  color: #94a3b8;
}

.custom-select {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  outline: none;
}

.absent-warning-banner {
  margin-top: 6px;
  padding: 8px 10px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-size: 11px;
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
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin: 6px 0 2px;
}

.fallback-sub {
  font-size: 11px;
  color: #94a3b8;
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
  font-size: 12px;
  color: #64748b;
}

.ledger-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.exam-card {
  background: #fff;
  border-radius: 14px;
  padding: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
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
  font-size: 11px;
  font-weight: 600;
  background: #eff6ff;
  color: #2563eb;
  padding: 2px 6px;
  border-radius: 6px;
}

.exam-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.exam-date-row {
  font-size: 11px;
  color: #64748b;
  margin: 6px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.rank-tag {
  background: #f1f5f9;
  color: #475569;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
}

.exam-score-banner {
  background: #f8fafc;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.total-label {
  font-size: 12px;
  color: #64748b;
}

.total-num {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.total-full {
  font-size: 12px;
  color: #94a3b8;
}

.subject-chips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(105px, 1fr));
  gap: 6px;
}

.sub-score-chip {
  background: #f1f5f9;
  border-radius: 6px;
  padding: 4px 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
}

.sub-score-chip.chip-absent {
  background: #fef2f2;
}

.chip-name {
  color: #475569;
}

.chip-score {
  color: #0f172a;
}

.chip-score small {
  color: #94a3b8;
}

.absent-text {
  color: #ef4444;
  font-weight: 500;
}

.empty-ledger-box {
  background: #fff;
  border-radius: 14px;
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
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.popup-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.popup-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 24px;
}

.live-calc-bar {
  margin: 10px 16px;
  padding: 10px 14px;
  background: #eff6ff;
  border-radius: 10px;
  border: 1px solid #bfdbfe;
}

.calc-label {
  font-size: 11px;
  color: #1d4ed8;
  font-weight: 500;
}

.calc-values {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-top: 4px;
}

.calc-main {
  font-size: 15px;
  color: #1e3a8a;
}

.calc-main b {
  font-size: 18px;
  color: #2563eb;
}

.calc-sub {
  font-size: 11px;
  color: #3b82f6;
}

.subject-edit-item {
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
}

.sub-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.sub-name-tag {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.sub-absent-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toggle-label {
  font-size: 11px;
  color: #64748b;
}

.sub-inputs-row {
  display: flex;
  gap: 8px;
}

.score-input-field,
.full-input-field {
  padding: 4px 8px;
  background: #f8fafc;
  border-radius: 6px;
}

.popup-bottom-actions {
  padding: 16px;
}
</style>

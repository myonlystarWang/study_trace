<template>
  <div class="paper-center-view">
    <!-- 顶部导航 -->
    <van-nav-bar
      title="A4 周末重练组卷"
      left-arrow
      right-text="历史记录"
      @click-left="$router.back()"
      @click-right="openHistorySheet"
      fixed
      placeholder
      z-index="100"
    />

    <div class="paper-center-body">
      <!-- 预设快捷模式卡片 -->
      <div class="st-card section-card preset-card">
        <div class="st-section-header" style="margin-bottom: 12px;">
          <span class="st-icon-badge st-icon-badge--primary">
            <van-icon name="fire-o" />
          </span>
          <span class="section-title">一键快捷组卷预设</span>
        </div>
        <div class="preset-grid">
          <div
            v-for="p in presets"
            :key="p.key"
            class="preset-item"
            :class="{ active: currentPreset === p.key }"
            @click="switchPreset(p.key)"
          >
            <div class="preset-icon">
              <span :class="['st-icon-badge', `st-icon-badge--${p.badgeColor}`]">
                <van-icon :name="p.icon" />
              </span>
            </div>
            <div class="preset-name">{{ p.name }}</div>
            <div class="preset-desc">{{ p.desc }}</div>
          </div>
        </div>
      </div>

      <!-- 学科过滤滑动条 -->
      <div class="st-card section-card filter-card">
        <div class="filter-header" style="margin-bottom: 12px;">
          <div class="st-section-header" style="margin-bottom: 0;">
            <span class="st-icon-badge st-icon-badge--info">
              <van-icon name="filter-o" />
            </span>
            <span class="section-title">学科筛选</span>
          </div>
          <div class="select-actions">
            <span class="action-link" @click="selectAllCandidates">全选本页</span>
            <span class="action-divider">|</span>
            <span class="action-link" @click="clearSelection">清空已选</span>
          </div>
        </div>
        <div class="subject-chips st-scroll-x">
          <span
            class="st-chip"
            :class="{ active: selectedSubjectId === null }"
            @click="filterBySubject(null)"
          >
            全部 ({{ candidates.length }})
          </span>
          <span
            v-for="sub in subjects"
            :key="sub.id"
            class="st-chip"
            :class="{ active: selectedSubjectId === sub.id }"
            @click="filterBySubject(sub.id)"
          >
            {{ sub.name }} ({{ getSubjectCount(sub.id) }})
          </span>
        </div>
        <div class="filter-footer-row">
          <van-checkbox v-model="includeAllSubjects" @change="() => fetchCandidates(false)" shape="square">
            <span class="extra-sub-label">包含非核心7科（艺术/信息等错题归入综合）</span>
          </van-checkbox>
        </div>
      </div>


      <!-- 错题选择列表 -->
      <div class="st-card section-card questions-card">
        <div class="list-summary">
          <span>待选题目 (当前展示 {{ filteredCandidates.length }} 题 · 累计已选 {{ selectedIds.length }} 题)</span>
        </div>

        <van-empty v-if="filteredCandidates.length === 0" description="当前条件下暂无匹配错题" />

        <div v-else class="candidate-list">
          <div
            v-for="item in filteredCandidates"
            :key="item.id"
            class="candidate-item"
            :class="{ selected: selectedIds.includes(item.id) }"
            @click="toggleSelect(item.id)"
          >
            <div class="candidate-checkbox" @click.stop>
              <van-checkbox :model-value="selectedIds.includes(item.id)" @change="toggleSelect(item.id)" />
            </div>
            <div class="candidate-info">
              <div class="candidate-tags" style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                <span class="st-subject-tag" :class="getSubjectTagClass(item.subject_name)">{{ item.subject_name }}</span>
                <span v-if="item.error_type" class="st-status-tag st-status-tag--warning">{{ item.error_type }}</span>
                <span v-if="item.is_ebbinghaus" class="st-status-tag st-status-tag--purple">艾宾浩斯</span>
                <span v-if="item.is_unmastered" class="st-status-tag st-status-tag--danger">高频未掌握</span>
                <span v-if="item.is_this_week" class="st-status-tag st-status-tag--success">本周新增</span>
              </div>
              <div class="candidate-text">
                {{ item.extracted_text || '（图片题目，点击右侧预览）' }}
              </div>
              <div class="candidate-meta">
                <span>复习 {{ item.review_count }} 次 · {{ item.mastery_status }}</span>
              </div>
            </div>
            <div v-if="item.thumbnail_path || item.original_image_path" class="candidate-thumb" @click.stop="previewImage(item.original_image_path || item.thumbnail_path)">
              <img :src="item.thumbnail_path || item.original_image_path" alt="题图" />
            </div>
          </div>
        </div>
      </div>

      <!-- 试卷排版与外观配置 -->
      <div class="st-card section-card config-card">
        <div class="st-section-header" style="margin-bottom: 14px;">
          <span class="st-icon-badge st-icon-badge--neutral">
            <van-icon name="setting-o" />
          </span>
          <span class="section-title">试卷排版规范配置</span>
        </div>

        <div class="config-row">
          <div class="config-label">试卷主标题</div>
          <van-field v-model="paperConfig.title" placeholder="如：初一错题周末重练卷" />
        </div>

        <div class="config-row">
          <div class="config-label">副标题与提示</div>
          <van-field v-model="paperConfig.subtitle" placeholder="如：满分: 100分 · 建议用时: 45分钟" />
        </div>

        <div class="config-row">
          <div class="config-label">题目排列顺序</div>
          <van-radio-group v-model="paperConfig.sort_by" direction="horizontal">
            <van-radio name="subject">按科目分大题</van-radio>
            <van-radio name="order">连续统一编号</van-radio>
            <van-radio name="random">随机乱序</van-radio>
          </van-radio-group>
        </div>

        <div class="config-row">
          <div class="config-label">答题留白整体松紧</div>
          <div class="config-sublabel">
            已按题型自动分级：选择 16mm / 默写 24mm / 简答·解答 48mm，此处用于整卷统一缩放
          </div>
          <van-radio-group v-model="paperConfig.space_level" direction="horizontal">
            <van-radio name="compact">紧凑 ×0.7</van-radio>
            <van-radio name="standard">标准 ×1</van-radio>
            <van-radio name="spacious">宽松 ×1.35</van-radio>
          </van-radio-group>
        </div>

        <div class="config-row">
          <div class="config-label">留白答题底纹</div>
          <van-radio-group v-model="paperConfig.style_mode" direction="horizontal">
            <van-radio name="grid">8mm方格网格</van-radio>
            <van-radio name="lined">经典横线</van-radio>
            <van-radio name="blank">纯白无底纹</van-radio>
          </van-radio-group>
        </div>

        <div class="config-row flex-between">
          <div>
            <div class="config-label">显示错因提示</div>
            <div class="config-sublabel">默认关闭以还原真实考场自测环境</div>
          </div>
          <van-switch v-model="paperConfig.show_error_type" size="22px" />
        </div>
      </div>
    </div>

    <!-- 底部常驻操作栏 -->
    <div class="bottom-compose-bar">
      <div class="compose-stats">
        <div class="main-stat">
          已勾选 <span class="highlight">{{ selectedIds.length }}</span> 题
        </div>
        <div class="sub-stat">
          预计约 <span class="highlight">{{ estimatedPages }}</span> 页 A4 纸
          <span v-if="selectedIds.length > 30" class="warn-hint">（题量较多，建议分批打印）</span>
        </div>
      </div>
      <van-button
        type="primary"
        round
        size="large"
        class="compose-submit-btn"
        icon="description"
        :loading="generating"
        :disabled="selectedIds.length === 0"
        @click="generatePaper"
      >
        一键生成 A4 重练卷
      </van-button>
    </div>

    <!-- 图片大图预览 -->
    <van-popup v-model:show="showImgPreview" round :style="{ padding: '10px', maxWidth: '90%' }">
      <img :src="previewImgUrl" style="max-width: 100%; max-height: 80vh; object-fit: contain; border-radius: 8px;" />
    </van-popup>

    <!-- 历史组卷记录抽屉 -->
    <van-popup
      v-model:show="showHistorySheet"
      position="bottom"
      round
      closeable
      class="bottom-sheet-modal"
      :style="{ height: '70%', display: 'flex', flexDirection: 'column' }"
    >
      <div class="history-sheet-header">
        <div class="st-section-header">
          <span class="st-icon-badge st-icon-badge--neutral">
            <van-icon name="records-o" />
          </span>
          <h3 class="section-title history-sheet-title">历史组卷记录</h3>
        </div>
        <span class="history-sheet-subtitle">已生成的周末重练卷可重新预览、补打或打卡</span>
      </div>
      <div class="history-sheet-content">
        <van-loading v-if="historyLoading" size="24px" vertical style="padding: 30px 0;">加载中...</van-loading>
        <van-empty v-else-if="historyList.length === 0" description="暂无历史组卷记录" />
        <div v-else class="history-sheet-list">
          <van-swipe-cell
            v-for="item in historyList"
            :key="item.id"
            :ref="(el) => setSwipeRef(item.id, el)"
            class="history-swipe-cell"
          >
            <div class="history-card" @click="onHistoryCardClick(item)">
              <div class="history-card-header">
                <span class="history-card-title">{{ item.title || '初一错题周末重练卷' }}</span>
                <van-tag v-if="item.status === 'reviewed'" type="success" size="medium">已打卡完成</van-tag>
                <van-tag v-else-if="item.status === 'printed'" color="#d97706" plain size="medium">已打印·待打卡</van-tag>
                <van-tag v-else type="primary" plain size="medium">未打印·草稿</van-tag>
              </div>
              <div class="history-card-desc">
                <span>共 {{ item.total_questions }} 题</span>
                <span class="dot">·</span>
                <span>预估 {{ item.estimated_pages }} 页</span>
                <span class="dot">·</span>
                <span>{{ formatHistoryTime(item.created_at) }}</span>
              </div>
              <div class="history-card-footer">
                <van-button size="mini" type="primary" plain @click.stop="router.push(`/paper/print?id=${item.id}`)">
                  查看试卷 / 打印
                </van-button>
                <van-button
                  v-if="item.status !== 'reviewed'"
                  size="mini"
                  type="warning"
                  plain
                  @click.stop="router.push(`/paper/print?id=${item.id}&action=review`)"
                >
                  去打卡
                </van-button>
              </div>
            </div>
            <template #right>
              <van-button
                square
                type="danger"
                class="history-delete-action"
                icon="delete-o"
                text="删除"
                @click="confirmDeletePaper(item)"
              />
            </template>
          </van-swipe-cell>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast, showConfirmDialog } from 'vant';
import { paperApi, settingsApi } from '../api';

const router = useRouter();

const presets = [
  { key: 'this_week', name: '本周新增', desc: '周一至今录入', icon: 'star-o', badgeColor: 'warning' },
  { key: 'ebbinghaus', name: '艾宾浩斯', desc: '临界待复习题', icon: 'replay', badgeColor: 'purple' },
  { key: 'unmastered', name: '高频未掌握', desc: '复习≥2次顽固题', icon: 'warning-o', badgeColor: 'danger' },
  { key: 'all', name: '全库自选', desc: '自由筛选勾选', icon: 'notes-o', badgeColor: 'primary' },
];

const currentPreset = ref('this_week');
const subjects = ref([]);
const selectedSubjectId = ref(null);
const includeAllSubjects = ref(false);
const candidates = ref([]);
const selectedIds = ref([]);
const generating = ref(false);

const showImgPreview = ref(false);
const previewImgUrl = ref('');

const showHistorySheet = ref(false);
const historyList = ref([]);
const historyLoading = ref(false);

// 函数式 ref 收集各 SwipeCell 实例：既能读滑动位移，也能主动 close()
const swipeRefs = {};
const setSwipeRef = (id, el) => {
  if (el) {
    swipeRefs[id] = el;
  } else {
    delete swipeRefs[id];
  }
};
/**
 * 判断某条记录的 SwipeCell 是否处于滑开状态。
 * 直接读 wrapper 的 transform，而不依赖 @open/@close 事件：
 * 点击右侧「删除」插槽时 Vant 会先派发 click、再自动收起并触发 @close
 * （源码 getClickHandler → onClick → callInterceptor → close(position)），
 * 事件时序会让外部维护的 openedId 提前失效。
 * 注意 Vant 写入的是 translate3d(x px, 0, 0)，不是 translateX。
 */
const isSwipeOpen = (id) => {
  const rootEl = swipeRefs[id] && swipeRefs[id].$el;
  const wrapper = rootEl && rootEl.querySelector('.van-swipe-cell__wrapper');
  if (!wrapper) return false;
  const m = /(-?[\d.]+)px/.exec(wrapper.style.transform || '');
  return Boolean(m) && Math.abs(parseFloat(m[1])) > 1;
};

const paperConfig = ref({
  title: '初一错题周末重练卷',
  subtitle: '满分: 100分 · 建议用时: 45分钟',
  sort_by: 'subject',
  space_level: 'standard',
  style_mode: 'grid',
  show_error_type: false,
});

// 学科标签颜色映射
const getSubjectTagClass = (name) => {
  if (!name) return 'st-subject-tag--neutral';
  switch (name) {
    case '数学': return 'st-subject-tag--primary';
    case '英语': return 'st-subject-tag--purple';
    case '语文': return 'st-subject-tag--success';
    case '物理':
    case '化学': return 'st-subject-tag--info';
    case '生物':
    case '地理': return 'st-subject-tag--warning';
    case '历史':
    case '道法':
    case '道法': return 'st-subject-tag--danger';
    default: return 'st-subject-tag--neutral';
  }
};

// 加载学科列表
const fetchSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    subjects.value = res.data;
  } catch (err) {
    console.error('获取学科失败', err);
  }
};

// 加载候选错题
const fetchCandidates = async (isInitial = false) => {
  try {
    const res = await paperApi.getCandidates({
      preset: currentPreset.value,
      include_all_subjects: includeAllSubjects.value,
    });
    candidates.value = res.data;

    // 仅在首次进入且尚未选中任何题目时，默认勾选前 25 道
    if (isInitial && selectedIds.value.length === 0) {
      selectedIds.value = res.data.slice(0, 25).map((q) => q.id);
    }
  } catch (err) {
    showToast('加载候选题目失败');
  }
};

const switchPreset = async (presetKey) => {
  if (currentPreset.value === presetKey) return;
  currentPreset.value = presetKey;
  selectedSubjectId.value = null;
  // 切换预设时不重置用户已勾选的题目（跨预设持久保留已选）
  await fetchCandidates(false);
};

const openHistorySheet = async () => {
  showHistorySheet.value = true;
  historyLoading.value = true;
  try {
    const res = await paperApi.getHistory({ limit: 30 });
    historyList.value = res.data;
  } catch (err) {
    showToast('获取历史记录失败');
  } finally {
    historyLoading.value = false;
  }
};

const onHistoryCardClick = (item) => {
  // 已滑开时点击只收起删除按钮，避免误触跳转
  if (isSwipeOpen(item.id)) {
    swipeRefs[item.id]?.close?.();
    return;
  }
  router.push(`/paper/print?id=${item.id}`);
};

const confirmDeletePaper = async (item) => {
  try {
    await showConfirmDialog({
      title: '删除组卷记录',
      message: `确认删除「${item.title || '初一错题周末重练卷'}」？\n共 ${item.total_questions} 题 · ${formatHistoryTime(
        item.created_at
      )}\n\n删除后无法恢复；错题原文与复习打卡进度不受影响。`,
      confirmButtonText: '删除',
      confirmButtonColor: '#dc2626',
      cancelButtonText: '取消',
    });
  } catch (e) {
    return; // 用户取消
  }

  try {
    await paperApi.deletePaper(item.id);
    historyList.value = historyList.value.filter((p) => p.id !== item.id);
    showToast('已删除');
  } catch (err) {
    showToast(err.response?.data?.detail || '删除失败，请稍后重试');
  }
};

const formatHistoryTime = (isoString) => {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${m}-${day} ${h}:${min}`;
  } catch (e) {
    return isoString;
  }
};

const filterBySubject = (subId) => {
  selectedSubjectId.value = subId;
};

const getSubjectCount = (subId) => {
  return candidates.value.filter((c) => c.subject_id === subId).length;
};

const filteredCandidates = computed(() => {
  if (selectedSubjectId.value === null) {
    return candidates.value;
  }
  return candidates.value.filter((c) => c.subject_id === selectedSubjectId.value);
});

const toggleSelect = (id) => {
  const idx = selectedIds.value.indexOf(id);
  if (idx > -1) {
    selectedIds.value.splice(idx, 1);
  } else {
    selectedIds.value.push(id);
  }
};

const selectAllCandidates = () => {
  const currentFilteredIds = filteredCandidates.value.map((c) => c.id);
  const union = Array.from(new Set([...selectedIds.value, ...currentFilteredIds]));
  selectedIds.value = union;
};

const clearSelection = () => {
  selectedIds.value = [];
};

// 页数预估：调后端 /api/paper/estimate，与真实出卷共用同一套留白与排版规则。
// 此前前端自持一份 round(题数/4)+ceil(图数/6) 的副本；留白改为逐题分级后，
// 同一张卷在两处会算出不同页数，故统一收敛到后端。
const estimatedPages = ref(1);
let estimateTimer = null;

const refreshEstimatedPages = () => {
  if (estimateTimer) clearTimeout(estimateTimer);
  const ids = [...selectedIds.value];
  if (ids.length === 0) {
    estimatedPages.value = 1;
    return;
  }
  // 连续勾选时防抖，只发最后一次；失败保留上次结果，不打断操作
  estimateTimer = setTimeout(async () => {
    try {
      const res = await paperApi.estimatePages(ids, paperConfig.value.space_level);
      estimatedPages.value = res.data.estimated_pages;
    } catch (err) {
      // 静默容错：保留上一次的预估页数
    }
  }, 250);
};

watch(selectedIds, refreshEstimatedPages, { deep: true });
watch(() => paperConfig.value.space_level, refreshEstimatedPages);

const previewImage = (url) => {
  if (!url) return;
  previewImgUrl.value = url;
  showImgPreview.value = true;
};

const generatePaper = async () => {
  if (selectedIds.value.length === 0) {
    showToast('请至少勾选 1 道题目');
    return;
  }
  generating.value = true;
  try {
    const payload = {
      mistake_ids: selectedIds.value,
      title: paperConfig.value.title || '初一错题周末重练卷',
      subtitle: paperConfig.value.subtitle || '满分: 100分 · 建议用时: 45分钟',
      sort_by: paperConfig.value.sort_by,
      space_level: paperConfig.value.space_level,
      style_mode: paperConfig.value.style_mode,
      show_error_type: paperConfig.value.show_error_type,
    };
    const res = await paperApi.compose(payload);
    const paperId = res.data.paper_id;
    // 写入 sessionStorage 作为容错兜底
    sessionStorage.setItem('current_paper_id', String(paperId));
    // 直接跳转带 query 的打印预览页
    router.push({ path: '/paper/print', query: { id: paperId } });
  } catch (err) {
    showToast(err.response?.data?.detail || '组卷失败，请稍后重试');
  } finally {
    generating.value = false;
  }
};

onMounted(async () => {
  await fetchSubjects();
  await fetchCandidates(true);
});
</script>

<style scoped>
.paper-center-view {
  min-height: 100vh;
  background-color: #f8fafc;
  padding-bottom: 90px;
}

.paper-center-body {
  padding: 12px;
}

.section-card {
  background: var(--st-bg-card);
  border-radius: var(--st-radius-md);
  padding: var(--st-space-card);
  margin-bottom: var(--st-space-4);
  border: 1px solid var(--st-border);
  box-shadow: var(--st-shadow-card);
}

/* .section-title 不再在此重复定义：design-tokens.css 已提供全局规范
   （15px / 600 / --st-text-primary / margin 0 / leading-tight）。
   原来此处写了 700 字重 + 10px 下边距，与全局冲突，是"同一标题在不同页面粗细不一"的根源。 */

/* 预设卡片 */
.preset-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.preset-item {
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #f8fafc;
}

.preset-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.preset-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.preset-name {
  font-size: var(--st-font-md);
  font-weight: 600;
  color: #1e293b;
}

.preset-desc {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin-top: 2px;
}

/* 学科筛选 */
.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.select-actions {
  font-size: var(--st-font-xs);
  color: #2563eb;
}

.action-link {
  cursor: pointer;
}

.action-divider {
  margin: 0 6px;
  color: #cbd5e1;
}

.subject-chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
  padding-bottom: 4px;
}

.subject-chips::-webkit-scrollbar {
  display: none;
}

.sub-chip {
  padding: 4px 12px;
  border-radius: 16px;
  font-size: var(--st-font-xs);
  background: #f1f5f9;
  color: #475569;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s;
}

.sub-chip.active {
  background: #2563eb;
  color: #ffffff;
  font-weight: 600;
}

.filter-footer-row {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
}

.extra-sub-label {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

/* 错题列表 */

.list-summary {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin-bottom: 8px;
}

.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.candidate-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  transition: all 0.2s;
  cursor: pointer;
}

.candidate-item.selected {
  border-color: #93c5fd;
  background: #f0f7ff;
}

.candidate-checkbox {
  margin-top: 2px;
}

.candidate-info {
  flex: 1;
  min-width: 0;
}

.candidate-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}

.candidate-text {
  font-size: var(--st-font-sm);
  color: #1e293b;
  line-height: var(--st-leading-tight);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 6px;
}

.candidate-meta {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
}

.candidate-thumb {
  width: 54px;
  height: 54px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.candidate-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 配置行
   节奏铁律：标签→控件 6px（组内），控件→下一组 16px（组间），两者必须有明显落差，
   否则整张卡片会糊成一片 —— 这是"看起来不舒服"的主要来源之一。 */
.config-row {
  margin-bottom: var(--st-space-5);
}

.config-row:last-child {
  margin-bottom: 0;
}

.config-row.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-label {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-regular);
  margin-bottom: var(--st-space-2);
  line-height: var(--st-leading-tight);
}

.config-sublabel {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  line-height: var(--st-leading-normal);
  margin-bottom: var(--st-space-2);
}

/* 配置卡片内的表单控件：去掉 Vant Cell 默认的 16px 横向内边距，
   使输入文字与上方标签左对齐（否则会出现"标签在 x=0、输入框在 x=16"的错位）。 */
.config-card :deep(.van-field) {
  padding-left: 0;
  padding-right: 0;
  padding-top: 0;
}

.config-card :deep(.van-field::after) {
  display: none;
}

/* 单选组：用 gap 统一间距，并去掉 Vant 默认的逐项 margin-right。
   原因（实测）：336px 可用宽度下，「按科目分大题/连续统一编号/随机乱序」三项实际需要 344px，
   而其中 12px 是**末项的右边距** —— flex 换行会把这项也计入行长，导致本可放下的三项被挤到第二行。
   改用 column-gap 后行长 324px < 336px，三项回归一行。 */
.config-card :deep(.van-radio-group--horizontal) {
  column-gap: var(--st-space-3);
  row-gap: var(--st-space-3);
}

.config-card :deep(.van-radio--horizontal) {
  margin-right: 0;
}

.config-card :deep(.van-radio),
.config-card :deep(.van-checkbox) {
  font-size: var(--st-font-md);
  color: var(--st-text-primary);
}

/* 底部常驻栏 */
.bottom-compose-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-width: 500px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid #e2e8f0;
  padding: 8px 16px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom, 0px));
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  z-index: 99;
}

.compose-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.main-stat {
  font-size: var(--st-font-md);
  font-weight: 600;
  color: #0f172a;
}

.sub-stat {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.highlight {
  color: #2563eb;
  font-weight: 700;
}

.warn-hint {
  color: #d97706;
}

.compose-submit-btn {
  height: 42px;
  font-size: var(--st-font-md);
  font-weight: 600;
  background: var(--st-primary, #2563eb);
  border: none;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
}

/* 历史记录抽屉样式 */
.history-sheet-header {
  padding: 16px 16px 10px;
  border-bottom: 1px solid #f1f5f9;
}

/* 抽屉内的页面级标题：比卡片区标题高一档（17px），用类名承载而不是写在模板 style 里，
   避免出现"同一个 section-title 在模板里又被临时改字号"的第二处定义。 */
.history-sheet-title {
  margin: 0;
  font-size: var(--st-font-xl);
  color: var(--st-text-primary);
}

.history-sheet-subtitle {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.history-sheet-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px 24px;
}

.history-sheet-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 左滑删除：外层裁圆角，使删除按钮与卡片视觉一体 */
.history-swipe-cell {
  border-radius: 10px;
  overflow: hidden;
}

.history-delete-action {
  height: 100%;
  min-width: 76px;
  font-size: var(--st-font-sm);
  border-radius: 0;
}

.history-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-card:active {
  background: #f1f5f9;
}

.history-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.history-card-title {
  font-size: var(--st-font-md);
  font-weight: 600;
  color: #1e293b;
}

.history-card-desc {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.history-card-desc .dot {
  color: #cbd5e1;
}

.history-card-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
}

/* 窄屏下按钮文字不竖排；真放不下就整体换行 */
.history-card-footer :deep(.van-button) {
  white-space: nowrap;
  flex-shrink: 0;
}
</style>

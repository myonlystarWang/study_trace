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
      <div class="section-card preset-card">
        <div class="section-title">⚡ 一键快捷组卷预设</div>
        <div class="preset-grid">
          <div
            v-for="p in presets"
            :key="p.key"
            class="preset-item"
            :class="{ active: currentPreset === p.key }"
            @click="switchPreset(p.key)"
          >
            <div class="preset-icon">{{ p.icon }}</div>
            <div class="preset-name">{{ p.name }}</div>
            <div class="preset-desc">{{ p.desc }}</div>
          </div>
        </div>
      </div>

      <!-- 学科过滤滑动条 -->
      <div class="section-card filter-card">
        <div class="filter-header">
          <div class="section-title">📚 学科筛选</div>
          <div class="select-actions">
            <span class="action-link" @click="selectAllCandidates">全选本页</span>
            <span class="action-divider">|</span>
            <span class="action-link" @click="clearSelection">清空已选</span>
          </div>
        </div>
        <div class="subject-chips">
          <div
            class="sub-chip"
            :class="{ active: selectedSubjectId === null }"
            @click="filterBySubject(null)"
          >
            全部 ({{ candidates.length }})
          </div>
          <div
            v-for="sub in subjects"
            :key="sub.id"
            class="sub-chip"
            :class="{ active: selectedSubjectId === sub.id }"
            @click="filterBySubject(sub.id)"
          >
            {{ sub.name }} ({{ getSubjectCount(sub.id) }})
          </div>
        </div>
        <div class="filter-footer-row">
          <van-checkbox v-model="includeAllSubjects" @change="() => fetchCandidates(false)" shape="square">
            <span class="extra-sub-label">包含非核心7科（艺术/信息等错题归入综合）</span>
          </van-checkbox>
        </div>
      </div>


      <!-- 错题选择列表 -->
      <div class="section-card questions-card">
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
              <div class="candidate-tags">
                <van-tag type="primary" size="medium">{{ item.subject_name }}</van-tag>
                <van-tag v-if="item.error_type" type="warning" plain size="medium">{{ item.error_type }}</van-tag>
                <van-tag v-if="item.is_ebbinghaus" color="#7c3aed" plain size="medium">艾宾浩斯</van-tag>
                <van-tag v-if="item.is_unmastered" color="#ef4444" plain size="medium">高频未掌握</van-tag>
                <van-tag v-if="item.is_this_week" color="#10b981" plain size="medium">本周新增</van-tag>
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
      <div class="section-card config-card">
        <div class="section-title">⚙️ 试卷排版规范配置</div>

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
          <div class="config-label">答题留白高度</div>
          <van-radio-group v-model="paperConfig.space_level" direction="horizontal">
            <van-radio name="compact">紧凑 (30mm)</van-radio>
            <van-radio name="standard">标准 (45mm)</van-radio>
            <van-radio name="spacious">宽敞 (60mm)</van-radio>
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
        :loading="generating"
        :disabled="selectedIds.length === 0"
        @click="generatePaper"
      >
        📄 一键生成 A4 重练卷
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
      :style="{ height: '70%', display: 'flex', flexDirection: 'column' }"
    >
      <div class="history-sheet-header">
        <h3>📋 历史组卷记录</h3>
        <span class="history-sheet-subtitle">已生成的周末重练卷可重新预览、补打或打卡</span>
      </div>
      <div class="history-sheet-content">
        <van-loading v-if="historyLoading" size="24px" vertical style="padding: 30px 0;">加载中...</van-loading>
        <van-empty v-else-if="historyList.length === 0" description="暂无历史组卷记录" />
        <div v-else class="history-sheet-list">
          <div
            v-for="item in historyList"
            :key="item.id"
            class="history-card"
            @click="router.push(`/paper/print?id=${item.id}`)"
          >
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
                style="margin-left: 6px;"
                @click.stop="router.push(`/paper/print?id=${item.id}&action=review`)"
              >
                去打卡
              </van-button>
            </div>
          </div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { paperApi, settingsApi } from '../api';

const router = useRouter();

const presets = [
  { key: 'this_week', name: '本周新增', desc: '周一至今录入', icon: '🌟' },
  { key: 'ebbinghaus', name: '艾宾浩斯', desc: '临界待复习题', icon: '🧠' },
  { key: 'unmastered', name: '高频未掌握', desc: '复习≥2次顽固题', icon: '⚠️' },
  { key: 'all', name: '全库自选', desc: '自由筛选勾选', icon: '📚' },
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

const allCandidatesMap = ref({});

const paperConfig = ref({
  title: '初一错题周末重练卷',
  subtitle: '满分: 100分 · 建议用时: 45分钟',
  sort_by: 'subject',
  space_level: 'standard',
  style_mode: 'grid',
  show_error_type: false,
});

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
    // 缓存所有加载过的题目对象，以便跨预设计算图片与信息
    res.data.forEach((c) => {
      allCandidatesMap.value[c.id] = c;
    });

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

// 极简粗略估算公式：max(1, round(total/4) + ceil(img/6))，从全量已勾选池中计算
const estimatedPages = computed(() => {
  const count = selectedIds.value.length;
  if (count <= 0) return 1;
  const selectedItems = selectedIds.value
    .map((id) => allCandidatesMap.value[id] || candidates.value.find((c) => c.id === id))
    .filter(Boolean);
  const imgCount = selectedItems.filter((c) => c.thumbnail_path || c.original_image_path).length;
  return Math.max(1, Math.round(count / 4) + Math.ceil(imgCount / 6));
});

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
  background: #ffffff;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 10px;
}

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
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.preset-desc {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

/* 学科筛选 */
.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.select-actions {
  font-size: 12px;
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
  font-size: 12px;
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
  font-size: 12px;
  color: #64748b;
}

/* 错题列表 */

.list-summary {
  font-size: 12px;
  color: #64748b;
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
  font-size: 13px;
  color: #1e293b;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 6px;
}

.candidate-meta {
  font-size: 11px;
  color: #94a3b8;
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

/* 配置行 */
.config-row {
  margin-bottom: 12px;
}

.config-row.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 4px;
}

.config-sublabel {
  font-size: 11px;
  color: #94a3b8;
}

/* 底部常驻栏 */
.bottom-compose-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-width: 500px;
  margin: 0 auto;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  padding: 10px 14px;
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
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.sub-stat {
  font-size: 12px;
  color: #64748b;
}

.highlight {
  color: #2563eb;
  font-weight: 700;
}

.warn-hint {
  color: #d97706;
}

.compose-submit-btn {
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  border: none;
}

/* 历史记录抽屉样式 */
.history-sheet-header {
  padding: 16px 16px 10px;
  border-bottom: 1px solid #f1f5f9;
}

.history-sheet-header h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #0f172a;
}

.history-sheet-subtitle {
  font-size: 12px;
  color: #64748b;
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
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.history-card-desc {
  font-size: 12px;
  color: #64748b;
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
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
}
</style>

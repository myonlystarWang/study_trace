<template>
  <van-popup
    :show="show"
    position="bottom"
    round
    class="bottom-sheet-modal"
    :style="{ maxHeight: '88%' }"
    @update:show="(v) => emit('update:show', v)"
  >
    <div class="quick-add">
      <div class="sheet-grabber"></div>
      
      <div class="modal-header-row">
        <div class="st-section-header" style="margin-bottom: 0;">
          <span class="st-icon-badge st-icon-badge--primary">
            <van-icon name="plus" />
          </span>
          <span class="section-title">录入新作业</span>
        </div>
        <span v-if="isSmartMode" class="st-status-tag st-status-tag--info">
          智能多科模式
        </span>
      </div>

      <!-- 模式切换：手动输入 / 拍照识别 -->
      <div class="mode-tabs">
        <div class="mode-tab" :class="{ active: mode === 'manual' }" @click="mode = 'manual'">
          <van-icon name="edit" /> 手动输入
        </div>
        <div class="mode-tab" :class="{ active: mode === 'camera' }" @click="mode = 'camera'">
          <van-icon name="photograph" /> 拍照识别
        </div>
      </div>

      <!-- 拍照识别模式 -->
      <div v-if="mode === 'camera'" class="camera-box">
        <div class="camera-uploader-row">
          <van-uploader
            v-model="cameraFileList"
            :after-read="onOcrUpload"
            :max-count="1"
            preview-size="76px"
            :capture="'environment'"
          />
          <div class="uploader-hint" v-if="cameraFileList.length === 0">
            拍照或选取作业照片，自动提取并智能归组到各学科
          </div>
        </div>
        <div v-if="ocrLoading" class="ocr-loading">
          <van-skeleton title :row="2" />
          <p class="ocr-tip">正在智能识别并拆解作业内容，耗时约 0.5~1.5s…</p>
        </div>
      </div>

      <!-- 传统单学科模式下的选择胶囊 -->
      <div class="single-subject-section" v-if="!isSmartMode">
        <div class="chips-label">选择作业所属学科：</div>
        <div class="sheet-subject-chips">
          <span
            v-for="sub in subjects"
            :key="sub.id"
            class="st-chip"
            :class="{ active: selectedSubject === sub.id }"
            @click="selectedSubject = sub.id"
          >
            {{ sub.name }}
          </span>
        </div>
      </div>

      <!-- 可编辑文本框 -->
      <van-field
        v-model="inputText"
        type="textarea"
        rows="4"
        autosize
        class="homework-input-field"
        placeholder="直接粘贴微信群大段作业、拍照识别或手动输入。支持“语文：1. ... 数学：...”跨科多行智能拆分"
      />

      <!-- 模式 1: 智能多学科拆解分组预览 -->
      <div class="smart-parsed-section" v-if="isSmartMode">
        <div class="smart-header">
          <div class="smart-header-left">
            <span class="st-icon-badge st-icon-badge--success" style="width: 22px; height: 22px; font-size: 11px;">
              <van-icon name="passed" />
            </span>
            <span class="smart-header-title">
              已识别 {{ activeParsedGroups.length }} 个学科，共 {{ totalSmartCount }} 项作业
            </span>
          </div>
          <button class="clear-text-btn" @click="clearInput">清空内容</button>
        </div>

        <div class="smart-groups-container">
          <div
            v-for="(group, gIdx) in activeParsedGroups"
            :key="group.subject.id"
            class="smart-group-card"
          >
            <div class="smart-group-head">
              <div class="smart-group-title">
                <span class="group-subject-tag">{{ group.subject.name }}</span>
                <span class="group-item-count">{{ group.items.length }} 项</span>
              </div>
            </div>
            <div class="smart-items-list">
              <div
                v-for="(item, iIdx) in group.items"
                :key="iIdx"
                class="smart-item-row"
              >
                <span class="smart-item-dot"></span>
                <span class="smart-item-text">{{ item }}</span>
                <button class="smart-item-del" @click="removeItem(gIdx, iIdx)" title="删除此项">
                  <van-icon name="cross" size="11" />
                </button>
              </div>
            </div>
          </div>

          <!-- 未识别学科的杂项内容收拢 -->
          <div class="smart-group-card smart-group-card--unassigned" v-if="activeUnassigned.length > 0">
            <div class="smart-group-head">
              <div class="smart-group-title">
                <span class="group-subject-tag group-subject-tag--unassigned">未指定学科</span>
                <span class="group-item-count">{{ activeUnassigned.length }} 项</span>
              </div>
              <div class="assign-dropdown-wrap">
                <span class="assign-label">归入：</span>
                <select v-model="unassignedTargetSubjectId" class="assign-select">
                  <option v-for="sub in subjects" :key="sub.id" :value="sub.id">{{ sub.name }}</option>
                </select>
              </div>
            </div>
            <div class="smart-items-list">
              <div
                v-for="(item, uIdx) in activeUnassigned"
                :key="uIdx"
                class="smart-item-row"
              >
                <span class="smart-item-dot smart-item-dot--amber"></span>
                <span class="smart-item-text">{{ item }}</span>
                <button class="smart-item-del" @click="removeUnassignedItem(uIdx)" title="删除此项">
                  <van-icon name="cross" size="11" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 模式 2: 传统单学科拆分预览 -->
      <div class="split-preview" v-else-if="lines.length > 1">
        <div class="split-head">将按 {{ lines.length }} 行存入「{{ currentSubjectName }}」：</div>
        <div class="split-list">
          <div v-for="(ln, i) in lines" :key="i" class="split-item">· {{ ln }}</div>
        </div>
      </div>

      <!-- 底部动作按钮 -->
      <div class="modal-btns">
        <van-button block round @click="close">取消</van-button>
        <van-button
          v-if="isSmartMode"
          type="primary"
          block
          round
          :loading="saving"
          @click="submitSmartBatch"
        >
          一键录入全部作业（{{ totalSmartCount }} 项）
        </van-button>
        <van-button
          v-else
          type="primary"
          block
          round
          :loading="saving"
          @click="submitBatch"
        >
          {{ lines.length <= 1 ? '添加作业' : `批量添加（${lines.length}）` }}
        </van-button>
      </div>
    </div>
  </van-popup>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { showToast } from 'vant';
import { homeworkApi, ocrApi } from '../api';
import { compressImage } from '../utils/imageCompress';

const props = defineProps({
  show: Boolean,
  subjects: { type: Array, default: () => [] },
  dateStr: { type: String, default: () => new Date().toISOString().split('T')[0] }
});
const emit = defineEmits(['update:show', 'added']);

const mode = ref('manual');
const inputText = ref('');
const selectedSubject = ref(null);
const saving = ref(false);
const ocrLoading = ref(false);
const cameraFileList = ref([]);
let pollTimer = null;

// 智能多学科解析出的响应式组与未分配列表
const activeParsedGroups = ref([]);
const activeUnassigned = ref([]);
const unassignedTargetSubjectId = ref(null);

const currentSubjectName = computed(() => {
  const found = props.subjects.find((s) => s.id === selectedSubject.value);
  return found ? found.name : '当前学科';
});

// 普通单学科按行划分
const lines = computed(() =>
  inputText.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
);

// 计算智能模式总作业项
const totalSmartCount = computed(() => {
  let count = 0;
  activeParsedGroups.value.forEach((g) => {
    count += g.items.length;
  });
  if (unassignedTargetSubjectId.value) {
    count += activeUnassigned.value.length;
  }
  return count;
});

// 是否处于智能多学科模式
const isSmartMode = computed(() => {
  return activeParsedGroups.value.length > 0;
});

// 学科同义词与别名分组矩阵（支持双向任意别名无缝互通）
const aliasGroups = [
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

// 为学科获取全部同义词与别名列表
const getAliasesForSubject = (subjectName) => {
  const clean = (subjectName || '').trim();
  for (const group of aliasGroups) {
    if (group.includes(clean) || group.some((alias) => clean.includes(alias) || alias.includes(clean))) {
      return Array.from(new Set([...group, clean]));
    }
  }
  return [clean];
};

// 识别行首学科标记
const matchSubjectHeader = (line, subjectsList) => {
  const trimmed = line.trim();
  if (!trimmed) return null;

  for (const sub of subjectsList) {
    const aliases = getAliasesForSubject(sub.name);
    for (const alias of aliases) {
      // 匹配：语文：作业 / 【语文】作业 / 语文 练习册 / 语文:
      const regex = new RegExp(`^[\\s【\\[（(]*(${alias})[\\s】\\]）)]*[:：\\s]\\s*(.*)$`);
      const m = trimmed.match(regex);
      if (m) {
        return {
          subject: sub,
          remainder: m[2] ? m[2].trim() : ''
        };
      }
      // 匹配独占一行的学科名：语文 / 【语文】
      const exactRegex = new RegExp(`^[\\s【\\[（(]*(${alias})[\\s】\\]）)]*$`);
      if (exactRegex.test(trimmed)) {
        return {
          subject: sub,
          remainder: ''
        };
      }
    }
  }

  // 匹配以学科名直接起头的内容
  for (const sub of subjectsList) {
    const aliases = getAliasesForSubject(sub.name);
    for (const alias of aliases) {
      if (trimmed.startsWith(alias)) {
        const remainder = trimmed.slice(alias.length).replace(/^[:：\s]+/, '').trim();
        return {
          subject: sub,
          remainder
        };
      }
    }
  }

  return null;
};

// 清理单条作业文字（去除序号、日期标记与纯杂项前缀）
const cleanTaskContent = (content) => {
  if (!content) return '';
  let cleaned = content.trim();
  // 去除常见序号: 1. / 1、 / 1) / ① / (1) / - / ·
  cleaned = cleaned.replace(/^(\d+[\.、\s\)\-]+|[①②③④⑤⑥⑦⑧⑨⑩]+|\(\d+\)|[-*·•]\s*)/, '').trim();
  return cleaned;
};

// 是否是无意义杂质行（如 "9月4日 (周五)", "今日作业", "作业布置"）
const isNoiseLine = (line) => {
  const trimmed = line.trim();
  if (!trimmed) return true;
  if (/^\d{1,2}月\d{1,2}日.*$/.test(trimmed)) return true; // 日期行
  if (/^(今日作业|作业布置|家庭作业|各科作业|作业清单)[:：\s]*$/.test(trimmed)) return true;
  if (/^(大家好|收到请回复|家长您好|温馨提示).*$/.test(trimmed)) return true;
  return false;
};

// 核心智能解析执行
const parseHomeworkText = (text, subjectsList) => {
  const rawLines = (text || '').split('\n').map((l) => l.trim()).filter(Boolean);
  if (rawLines.length === 0) {
    return { groups: [], unassigned: [] };
  }

  const groupsMap = new Map();
  const unassigned = [];
  let currentSubject = null;
  let detectedSubjectCount = 0;

  for (const line of rawLines) {
    if (isNoiseLine(line)) continue;

    const matched = matchSubjectHeader(line, subjectsList);
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
        const cleaned = cleanTaskContent(matched.remainder);
        if (cleaned) {
          groupsMap.get(currentSubject.id).items.push(cleaned);
        }
      }
    } else {
      const cleaned = cleanTaskContent(line);
      if (!cleaned) continue;

      if (currentSubject) {
        groupsMap.get(currentSubject.id).items.push(cleaned);
      } else {
        unassigned.push(cleaned);
      }
    }
  }

  const groups = Array.from(groupsMap.values()).filter((g) => g.items.length > 0);
  
  // 命中至少 1 个显式学科头时开启智能多科模式
  if (detectedSubjectCount >= 1 && groups.length > 0) {
    return { groups, unassigned };
  }

  return { groups: [], unassigned: [] };
};

// 监听输入文本实时解析
watch(
  () => inputText.value,
  (val) => {
    if (!val || !val.trim()) {
      activeParsedGroups.value = [];
      activeUnassigned.value = [];
      return;
    }
    const result = parseHomeworkText(val, props.subjects);
    activeParsedGroups.value = result.groups;
    activeUnassigned.value = result.unassigned;
    if (result.unassigned.length > 0 && !unassignedTargetSubjectId.value && props.subjects.length > 0) {
      unassignedTargetSubjectId.value = props.subjects[0].id;
    }
  }
);

watch(
  () => props.subjects,
  (subs) => {
    if (subs && subs.length > 0) {
      if (!selectedSubject.value) {
        selectedSubject.value = subs[0].id;
      }
      if (!unassignedTargetSubjectId.value) {
        unassignedTargetSubjectId.value = subs[0].id;
      }
    }
  },
  { immediate: true }
);

const removeItem = (gIdx, iIdx) => {
  activeParsedGroups.value[gIdx].items.splice(iIdx, 1);
  if (activeParsedGroups.value[gIdx].items.length === 0) {
    activeParsedGroups.value.splice(gIdx, 1);
  }
};

const removeUnassignedItem = (uIdx) => {
  activeUnassigned.value.splice(uIdx, 1);
};

const clearInput = () => {
  inputText.value = '';
  activeParsedGroups.value = [];
  activeUnassigned.value = [];
};

const close = () => {
  stopPoll();
  clearInput();
  cameraFileList.value = [];
  ocrLoading.value = false;
  mode.value = 'manual';
  emit('update:show', false);
};

const stopPoll = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const pollTask = (taskId) => {
  stopPoll();
  pollTimer = setInterval(async () => {
    try {
      const res = await ocrApi.getTask(taskId);
      const t = res.data;
      if (t.status === 'succeeded') {
        stopPoll();
        ocrLoading.value = false;
        inputText.value = t.result.text;
        showToast({ message: `识别完成（${t.result.engine} · ${t.result.cost_ms}ms）`, icon: 'success' });
      } else if (t.status === 'failed') {
        stopPoll();
        ocrLoading.value = false;
        showToast('识别失败，请手动输入或重试');
      }
    } catch (e) {
      stopPoll();
      ocrLoading.value = false;
      showToast('查询识别状态失败');
    }
  }, 600);
};

const onOcrUpload = async (fileItem) => {
  ocrLoading.value = true;
  try {
    const compressed = await compressImage(fileItem.file, 1600, 0.82);
    const fd = new FormData();
    fd.append('file', compressed.file);
    fd.append('mode', 'auto');
    const res = await ocrApi.createTask(fd);
    await pollTask(res.data.task_id);
  } catch (e) {
    ocrLoading.value = false;
    showToast('提交识别失败');
  }
};

// 智能多学科并发录入
const submitSmartBatch = async () => {
  const itemsToCreate = [];

  for (const group of activeParsedGroups.value) {
    for (const itemText of group.items) {
      itemsToCreate.push({
        subject_id: group.subject.id,
        date: props.dateStr,
        content: itemText,
        is_completed: false
      });
    }
  }

  if (activeUnassigned.value.length > 0 && unassignedTargetSubjectId.value) {
    for (const itemText of activeUnassigned.value) {
      itemsToCreate.push({
        subject_id: unassignedTargetSubjectId.value,
        date: props.dateStr,
        content: itemText,
        is_completed: false
      });
    }
  }

  if (itemsToCreate.length === 0) {
    showToast('请先输入或确认作业内容');
    return;
  }

  saving.value = true;
  try {
    await Promise.all(itemsToCreate.map((payload) => homeworkApi.create(payload)));
    showToast({ message: `智能录入完成！共添加 ${itemsToCreate.length} 项作业`, icon: 'success' });
    emit('added');
    close();
  } catch (e) {
    showToast('批量添加失败，请重试');
  } finally {
    saving.value = false;
  }
};

// 传统单学科批量录入
const submitBatch = async () => {
  if (!selectedSubject.value) {
    showToast('请选择学科');
    return;
  }
  if (lines.value.length === 0) {
    showToast('请先输入或识别作业内容');
    return;
  }
  saving.value = true;
  try {
    for (const line of lines.value) {
      await homeworkApi.create({
        subject_id: selectedSubject.value,
        date: props.dateStr,
        content: line,
        is_completed: false
      });
    }
    showToast({ message: `已添加 ${lines.value.length} 项作业`, icon: 'success' });
    emit('added');
    close();
  } catch (e) {
    showToast('添加失败');
  } finally {
    saving.value = false;
  }
};
</script>

<style scoped>
.quick-add {
  padding: 1rem 1.25rem 1.75rem;
}

.sheet-grabber {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background-color: var(--st-border-bold, #e2e8f0);
  margin: 0 auto 12px;
}

.modal-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.mode-tabs {
  display: flex;
  background-color: var(--st-bg-subtle, #f1f5f9);
  border-radius: var(--st-radius-md, 10px);
  padding: 3px;
  gap: 4px;
  margin-bottom: 12px;
}

.mode-tab {
  flex: 1;
  text-align: center;
  padding: 6px 12px;
  border-radius: var(--st-radius-sm, 6px);
  font-size: 13px;
  font-weight: 500;
  color: var(--st-text-secondary, #64748b);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.mode-tab.active {
  background: #ffffff;
  color: var(--st-text-primary, #0f172a);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.camera-box {
  margin-bottom: 12px;
}

.camera-uploader-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.uploader-hint {
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
}

.ocr-loading {
  margin-top: 0.75rem;
}

.ocr-tip {
  font-size: 12px;
  color: #64748b;
  margin-top: 0.5rem;
}

.single-subject-section {
  margin-bottom: 10px;
}

.chips-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--st-text-secondary, #64748b);
  margin-bottom: 6px;
}

.sheet-subject-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.homework-input-field {
  background: #f8fafc;
  border: 1px solid var(--st-border, #e2e8f0);
  border-radius: var(--st-radius-sm, 8px);
  padding: 8px 10px;
  font-size: 13px;
  margin-bottom: 12px;
}

/* 智能多学科拆分展示 */
.smart-parsed-section {
  background: #f8fafc;
  border: 1px solid var(--st-border, #e2e8f0);
  border-radius: var(--st-radius-md, 10px);
  padding: 10px 12px;
  margin-bottom: 12px;
}

.smart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--st-border, #e2e8f0);
}

.smart-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.smart-header-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--st-text-primary, #0f172a);
}

.clear-text-btn {
  background: transparent;
  border: none;
  font-size: 11px;
  color: var(--st-text-muted, #94a3b8);
  cursor: pointer;
  padding: 2px 4px;
}

.clear-text-btn:hover {
  color: #ef4444;
}

.smart-groups-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
}

.smart-group-card {
  background: #ffffff;
  border: 1px solid var(--st-border, #e2e8f0);
  border-radius: var(--st-radius-sm, 8px);
  padding: 8px 10px;
}

.smart-group-card--unassigned {
  background: #fffbeb;
  border-color: #fde68a;
}

.smart-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.smart-group-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.group-subject-tag {
  font-size: 11px;
  font-weight: 700;
  color: #ffffff;
  background: var(--st-primary, #2563eb);
  padding: 2px 8px;
  border-radius: var(--st-radius-full, 9999px);
}

.group-subject-tag--unassigned {
  background: #f59e0b;
}

.group-item-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--st-text-secondary, #64748b);
}

.assign-dropdown-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}

.assign-label {
  font-size: 11px;
  color: #b45309;
}

.assign-select {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid #fcd34d;
  background: #ffffff;
  color: #b45309;
}

.smart-items-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.smart-item-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: var(--st-text-primary, #0f172a);
  line-height: 1.4;
  padding: 2px 0;
}

.smart-item-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--st-primary, #2563eb);
  margin-top: 6px;
  flex-shrink: 0;
}

.smart-item-dot--amber {
  background: #f59e0b;
}

.smart-item-text {
  flex: 1;
  word-break: break-all;
}

.smart-item-del {
  background: transparent;
  border: none;
  color: var(--st-text-muted, #94a3b8);
  cursor: pointer;
  padding: 2px;
  line-height: 1;
  display: flex;
  align-items: center;
}

.smart-item-del:hover {
  color: #ef4444;
}

/* 传统单学科拆分预览 */
.split-preview {
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid var(--st-border, #e2e8f0);
  border-radius: var(--st-radius-sm, 8px);
  padding: 8px 10px;
}

.split-head {
  font-size: 12px;
  font-weight: 600;
  color: var(--st-text-secondary, #64748b);
  margin-bottom: 4px;
}

.split-list {
  max-height: 120px;
  overflow-y: auto;
}

.split-item {
  font-size: 12px;
  color: var(--st-text-primary, #0f172a);
  padding: 2px 0;
}

.modal-btns {
  display: flex;
  gap: 0.75rem;
  margin-top: 6px;
}
</style>

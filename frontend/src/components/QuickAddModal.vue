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
        <div class="st-section-header quick-add-title-row">
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
            v-for="sub in availableSubjects"
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
            <span class="st-icon-badge st-icon-badge--success" style="width: 22px; height: 22px; font-size: var(--st-font-xs);">
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
                  <option v-for="sub in availableSubjects" :key="sub.id" :value="sub.id">{{ sub.name }}</option>
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
          type="primary"
          block
          round
          :loading="saving"
          @mousedown.prevent
          @click="handleSubmit"
        >
          {{ isSmartMode ? `一键录入（${totalSmartCount} 项）` : (lines.length <= 1 ? '添加作业' : `批量添加（${lines.length}）`) }}
        </van-button>
      </div>
    </div>
  </van-popup>

  <!-- 作业拍照框选裁剪弹窗（与错题录入共用 ImageCropper，这里覆盖为作业场景文案） -->
  <ImageCropper
    v-if="showCropper"
    v-model:show="showCropper"
    :image-url="cropperImageUrl"
    title="框选作业内容"
    tip="拖拽四周框选要识别的作业区域，排除桌面与无关背景"
    confirm-text="确认并识别作业"
    @crop="onCropConfirm"
    @skip="onCropSkip"
    @cancel="onCropCancel"
  />
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { showToast } from 'vant';
import { homeworkApi, ocrApi, settingsApi } from '../api';
import { compressImage } from '../utils/imageCompress';
import ImageCropper from './ImageCropper.vue';
import { parseHomeworkText, DEFAULT_FALLBACK_SUBJECTS } from '../utils/homeworkParser';

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

// 拍照框选裁剪状态
const showCropper = ref(false);
const cropperImageUrl = ref('');
const pendingCameraFile = ref(null);
const internalSubjects = ref([]);
let pollTimer = null;

// 自主向后端拉取学科（双重保障）
const fetchInternalSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    if (res.data && res.data.length > 0) {
      internalSubjects.value = res.data;
    }
  } catch (err) {
    console.error('QuickAddModal load subjects fallback:', err);
  }
};

// 统一可信学科数据源：优先外部 props，次选自身拉取，底线使用系统预置标准学科
const availableSubjects = computed(() => {
  if (props.subjects && props.subjects.length > 0) {
    return props.subjects;
  }
  if (internalSubjects.value && internalSubjects.value.length > 0) {
    return internalSubjects.value;
  }
  return DEFAULT_FALLBACK_SUBJECTS;
});

// 智能多学科解析出的响应式组与未分配列表
const activeParsedGroups = ref([]);
const activeUnassigned = ref([]);
const unassignedTargetSubjectId = ref(null);

const currentSubjectName = computed(() => {
  const found = availableSubjects.value.find((s) => s.id === selectedSubject.value);
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

// 智能多学科拆解解析由 ../utils/homeworkParser.js 统一提供


// 监听输入文本实时解析
watch(
  () => inputText.value,
  (val) => {
    if (!val || !val.trim()) {
      activeParsedGroups.value = [];
      activeUnassigned.value = [];
      return;
    }
    const result = parseHomeworkText(val, availableSubjects.value);
    activeParsedGroups.value = result.groups;
    activeUnassigned.value = result.unassigned;
    if (result.unassigned.length > 0 && !unassignedTargetSubjectId.value && availableSubjects.value.length > 0) {
      unassignedTargetSubjectId.value = availableSubjects.value[0].id;
    }
  }
);

watch(
  availableSubjects,
  (subs) => {
    if (subs && subs.length > 0) {
      if (!selectedSubject.value || !subs.some(s => s.id === selectedSubject.value)) {
        selectedSubject.value = subs[0].id;
      }
      if (!unassignedTargetSubjectId.value || !subs.some(s => s.id === unassignedTargetSubjectId.value)) {
        unassignedTargetSubjectId.value = subs[0].id;
      }
    }
  },
  { immediate: true }
);

watch(
  () => props.show,
  (val) => {
    if (val) {
      fetchInternalSubjects();
      if (inputText.value && inputText.value.trim()) {
        const result = parseHomeworkText(inputText.value, availableSubjects.value);
        activeParsedGroups.value = result.groups;
        activeUnassigned.value = result.unassigned;
      }
    }
  },
  { immediate: true }
);

onMounted(() => {
  fetchInternalSubjects();
});

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

const onOcrUpload = (fileItem) => {
  pendingCameraFile.value = fileItem;
  cropperImageUrl.value = fileItem.content || (fileItem.file ? URL.createObjectURL(fileItem.file) : '');
  showCropper.value = true;
};

const executeOcrWithFile = async (targetFile) => {
  ocrLoading.value = true;
  try {
    const compressed = await compressImage(targetFile, 1600, 0.82);
    const fd = new FormData();
    fd.append('file', compressed.file || targetFile);
    fd.append('mode', 'auto');
    const res = await ocrApi.createTask(fd);
    await pollTask(res.data.task_id);
  } catch (e) {
    ocrLoading.value = false;
    showToast('提交识别失败');
  }
};

const onCropConfirm = async (cropData) => {
  showCropper.value = false;
  if (cropData?.file) {
    if (cropData.blobUrl) {
      cameraFileList.value = [{ url: cropData.blobUrl }];
    }
    await executeOcrWithFile(cropData.file);
  }
};

const onCropSkip = async () => {
  showCropper.value = false;
  if (pendingCameraFile.value?.file) {
    await executeOcrWithFile(pendingCameraFile.value.file);
  }
};

const onCropCancel = () => {
  showCropper.value = false;
  cameraFileList.value = [];
  pendingCameraFile.value = null;
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

const handleSubmit = () => {
  if (isSmartMode.value) {
    submitSmartBatch();
  } else {
    submitBatch();
  }
};
</script>

<style scoped>
.quick-add {
  padding: var(--st-space-3) var(--st-space-5) calc(var(--st-space-6) + max(env(safe-area-inset-bottom, 0px), var(--st-keyboard-inset)));
}

.sheet-grabber {
  width: 36px;
  height: 4px;
  border-radius: var(--st-radius-full);
  background-color: var(--st-border-bold);
  margin: 0 auto var(--st-space-4);
}

.quick-add-title-row { margin-bottom: 0; }

.modal-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.mode-tabs {
  display: flex;
  background-color: var(--st-bg-subtle);
  border-radius: var(--st-radius-md);
  padding: var(--st-space-1);
  gap: var(--st-space-1);
  margin-bottom: var(--st-space-4);
}

.mode-tab {
  flex: 1;
  text-align: center;
  padding: var(--st-space-2) var(--st-space-4);
  border-radius: var(--st-radius-sm);
  font-size: var(--st-font-sm);
  font-weight: 500;
  color: var(--st-text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.mode-tab.active {
  background: var(--st-bg-card);
  color: var(--st-text-primary);
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
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  line-height: var(--st-leading-tight);
}

.ocr-loading {
  margin-top: 0.75rem;
}

.ocr-tip {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin-top: 0.5rem;
}

.single-subject-section {
  margin-bottom: 10px;
}

.chips-label {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: var(--st-text-secondary);
  margin-bottom: 6px;
}

.sheet-subject-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.homework-input-field {
  background: var(--st-bg-subtle);
  border: 1px solid var(--st-border);
  border-radius: var(--st-radius-md);
  padding: var(--st-space-3) var(--st-space-4);
  font-size: var(--st-font-sm);
  margin-bottom: 12px;
}

/* 智能多学科拆分展示 */
.smart-parsed-section {
  background: var(--st-bg-subtle);
  border: 1px solid var(--st-border);
  border-radius: var(--st-radius-md);
  padding: var(--st-space-3) var(--st-space-4);
  margin-bottom: var(--st-space-4);
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
  font-size: var(--st-font-xs);
  font-weight: 700;
  color: var(--st-text-primary);
}

.clear-text-btn {
  background: transparent;
  border: none;
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  cursor: pointer;
  padding: 2px 4px;
}

.clear-text-btn:hover {
  color: var(--st-danger);
}

.smart-groups-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
}

.smart-group-card {
  background: var(--st-bg-card);
  border: 1px solid var(--st-border);
  border-radius: var(--st-radius-sm);
  padding: var(--st-space-3) var(--st-space-4);
}

.smart-group-card--unassigned {
  background: var(--st-warning-light);
  border-color: var(--st-warning);
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
  font-size: var(--st-font-xs);
  font-weight: 700;
  color: #ffffff;
  background: var(--st-primary, #2563eb);
  padding: 2px 8px;
  border-radius: var(--st-radius-full, 9999px);
}

.group-subject-tag--unassigned {
  background: var(--st-warning);
}

.group-item-count {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: var(--st-text-secondary);
}

.assign-dropdown-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}

.assign-label {
  font-size: var(--st-font-xs);
  color: var(--st-warning-dark);
}

.assign-select {
  font-size: var(--st-font-xs);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--st-warning);
  background: var(--st-bg-card);
  color: var(--st-warning-dark);
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
  font-size: var(--st-font-xs);
  color: var(--st-text-primary);
  line-height: var(--st-leading-tight);
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
  background: var(--st-warning);
}

.smart-item-text {
  flex: 1;
  word-break: break-all;
}

.smart-item-del {
  background: transparent;
  border: none;
  color: var(--st-text-muted);
  cursor: pointer;
  padding: 2px;
  line-height: 1;
  display: flex;
  align-items: center;
}

.smart-item-del:hover {
  color: var(--st-danger);
}

/* 传统单学科拆分预览 */
.split-preview {
  margin-bottom: 12px;
  background: var(--st-bg-subtle);
  border: 1px solid var(--st-border);
  border-radius: var(--st-radius-sm);
  padding: var(--st-space-3) var(--st-space-4);
}

.split-head {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: var(--st-text-secondary);
  margin-bottom: 4px;
}

.split-list {
  max-height: 120px;
  overflow-y: auto;
}

.split-item {
  font-size: var(--st-font-xs);
  color: var(--st-text-primary);
  padding: 2px 0;
}

.modal-btns {
  display: flex;
  gap: var(--st-space-4);
  margin-top: 6px;
}
</style>

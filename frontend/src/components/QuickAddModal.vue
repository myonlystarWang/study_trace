<template>
  <van-popup
    :show="show"
    position="bottom"
    round
    class="bottom-sheet-modal"
    :style="{ maxHeight: '85%' }"
    @update:show="(v) => emit('update:show', v)"
  >
    <div class="quick-add">
      <div class="sheet-grabber"></div>
      <div class="st-section-header">
        <span class="st-icon-badge st-icon-badge--primary">
          <van-icon name="plus" />
        </span>
        <span class="section-title">录入新作业</span>
      </div>

      <!-- 模式切换 -->
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
            preview-size="80px"
            :capture="'environment'"
          />
          <div class="uploader-hint" v-if="cameraFileList.length === 0">
            点击上方拍照或选取作业照片，自动提取题干
          </div>
        </div>
        <div v-if="ocrLoading" class="ocr-loading">
          <van-skeleton title :row="2" />
          <p class="ocr-tip">正在识别题干，耗时约 0.5~1.5s…</p>
        </div>
      </div>

      <!-- 学科选择 -->
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

      <!-- 可编辑文本（手动或 OCR 回填） -->
      <van-field
        v-model="inputText"
        type="textarea"
        rows="4"
        autosize
        placeholder="填写或拍照识别作业内容，每行一条可批量添加"
      />

      <!-- 按换行拆分预览 -->
      <div class="split-preview" v-if="lines.length > 1">
        <div class="split-head">将按 {{ lines.length }} 行拆分为多条作业：</div>
        <div class="split-list">
          <div v-for="(ln, i) in lines" :key="i" class="split-item">· {{ ln }}</div>
        </div>
      </div>

      <div class="modal-btns">
        <van-button block @click="close">取消</van-button>
        <van-button type="primary" block :loading="saving" @click="submitBatch">
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

const lines = computed(() =>
  inputText.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
);

watch(
  () => props.subjects,
  (subs) => {
    if (subs && subs.length > 0 && !selectedSubject.value) {
      selectedSubject.value = subs[0].id;
    }
  },
  { immediate: true }
);

const close = () => {
  stopPoll();
  inputText.value = '';
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
  margin: 0 auto 14px;
}

.mode-tabs {
  display: flex;
  background-color: var(--st-bg-subtle, #f1f5f9);
  border-radius: var(--st-radius-md, 10px);
  padding: 3px;
  gap: 4px;
  margin-bottom: 1rem;
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
  margin-bottom: 1rem;
  min-height: 60px;
}

.camera-uploader-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.uploader-hint {
  font-size: 0.8rem;
  color: #64748b;
  line-height: 1.4;
}

.ocr-loading {
  margin-top: 0.75rem;
}

.ocr-tip {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 0.5rem;
}

.sheet-subject-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 1rem;
}
.split-preview {
  margin-top: 0.75rem;
  background: #f8fafc;
  border-radius: 8px;
  padding: 0.6rem 0.8rem;
}
.split-head {
  font-size: 0.8rem;
  color: #64748b;
  margin-bottom: 0.3rem;
}
.split-list {
  max-height: 120px;
  overflow-y: auto;
}
.split-item {
  font-size: 0.85rem;
  color: #334155;
  padding: 0.15rem 0;
}
.modal-btns {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.25rem;
}
</style>

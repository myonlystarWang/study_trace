<template>
  <div class="mistake-view">
    <!-- 顶部主标签页切换与周末组卷快捷入口 -->
    <div class="mistake-header-bar">
      <van-tabs v-model:active="activeTab" color="#2563eb" line-width="40px" @change="onTabChange" class="mistake-tabs">
        <van-tab title="今日复习" name="review">
          <template #title>
            <span>今日待复习</span>
            <van-badge v-if="reviewQueueCount > 0" :content="reviewQueueCount" />
          </template>
        </van-tab>
        <van-tab title="错题总库" name="all"></van-tab>
      </van-tabs>
      <div class="paper-quick-btn" @click="$router.push('/paper')">
        <van-icon name="notes-o" />
        <span>周末组卷</span>
      </div>
    </div>

    <!-- 学科与状态筛选栏 (Chips) -->
    <div class="filter-section">
      <div class="chips-row">
        <span
          class="st-chip"
          :class="{ active: selectedSubject === null }"
          @click="selectSubject(null)"
        >
          全部学科
        </span>
        <span
          v-for="sub in subjects"
          :key="sub.id"
          class="st-chip"
          :class="{ active: selectedSubject === sub.id }"
          @click="selectSubject(sub.id)"
        >
          {{ sub.name }}
        </span>
      </div>

      <!-- 状态过滤（仅在总库标签下展示） -->
      <div class="chips-row status-row" v-if="activeTab === 'all'">
        <span
          v-for="status in ['全部状态', '未掌握', '待复习', '已掌握']"
          :key="status"
          class="st-chip"
          :class="{ active: selectedStatus === (status === '全部状态' ? null : status) }"
          @click="selectedStatus = (status === '全部状态' ? null : status); fetchMistakes()"
        >
          {{ status }}
        </span>
      </div>
    </div>

    <!-- 错题列表 -->
    <van-pull-refresh v-model="refreshing" @refresh="fetchMistakes">
      <div class="mistake-list" v-if="mistakes.length > 0">
        <div
          v-for="item in mistakes"
          :key="item.id"
          class="st-card mistake-card"
        >
          <div class="card-header">
            <div class="header-left">
              <span class="st-subject-tag" :class="getSubjectTagClass(item.subject_name)">
                {{ item.subject_name }}
              </span>
              <span class="source-text" v-if="item.source_reference">
                {{ item.source_reference }}
              </span>
            </div>
            <span class="hw-status-tag" :class="getStatusClass(item.mastery_status)">
              {{ item.mastery_status }}
            </span>
          </div>

          <!-- 缩略图展示 (点击可放大原图预览) -->
          <div class="card-image-box" v-if="item.thumbnail_path" @click="previewImage(item.original_image_path || item.thumbnail_path)">
            <img :src="item.thumbnail_path" alt="题目图" />
            <span class="img-preview-tag">
              <van-icon name="search" /> 点击放大原图
            </span>
          </div>

          <!-- 题目文本内容 -->
          <div class="card-body">
            <p class="question-text">{{ item.extracted_text || '暂无文字题干，请查看配图' }}</p>
            <div class="tags-row" v-if="item.error_type">
              <span class="error-tag">
                <van-icon name="warning-o" /> {{ item.error_type }}
              </span>
            </div>
          </div>

          <!-- 艾宾浩斯复习操作区（在今日复习模式或未完全掌握时醒目展示） -->
          <div class="review-action-bar" v-if="activeTab === 'review' || item.mastery_status !== '已掌握'">
            <div class="review-stat">
              <span class="st-icon-badge st-icon-badge--purple" style="width: 20px; height: 20px; font-size: 11px;">
                <van-icon name="replay" />
              </span>
              <span>第 <b>{{ item.review_count || 0 }}</b> 轮复习</span>
              <span v-if="item.next_review_date" class="next-date">
                (下次: {{ item.next_review_date }})
              </span>
            </div>
            <div class="action-buttons">
              <van-button
                size="small"
                plain
                type="danger"
                icon="cross"
                class="rev-btn"
                @click="submitReview(item.id, 'forgotten')"
              >
                又忘了
              </van-button>
              <van-button
                size="small"
                type="success"
                icon="passed"
                class="rev-btn"
                @click="submitReview(item.id, 'remembered')"
              >
                掌握啦
              </van-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 清爽空状态 -->
      <div class="empty-state" v-else>
        <van-empty :description="activeTab === 'review' ? '今日推荐复习已全部完成！太棒了' : '暂无相关错题'" />
      </div>
    </van-pull-refresh>

    <!-- 底部常驻磨砂悬浮录入栏 -->
    <div class="floating-bottom-bar st-frosted-bar">
      <van-button
        type="primary"
        round
        block
        icon="plus"
        class="add-mistake-btn"
        @click="showAddModal = true"
      >
        录入新错题
      </van-button>
    </div>

    <!-- 录入错题底部半屏抽屉 (Bottom Sheet) -->
    <van-popup
      v-model:show="showAddModal"
      position="bottom"
      round
      class="bottom-sheet-modal"
      :style="{ maxHeight: '85%' }"
    >
      <div class="add-modal-body">
        <div class="sheet-grabber"></div>
        <div class="st-section-header">
          <span class="st-icon-badge st-icon-badge--primary">
            <van-icon name="plus" />
          </span>
          <span class="section-title">录入新错题</span>
        </div>

        <div class="form-group">
          <label class="form-label">学科</label>
          <div class="sheet-subject-chips">
            <span
              v-for="sub in subjects"
              :key="sub.id"
              class="st-chip"
              :class="{ active: newMistake.subject_id === sub.id }"
              @click="newMistake.subject_id = sub.id"
            >
              {{ sub.name }}
            </span>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">来源说明（选填）</label>
          <van-field
            v-model="newMistake.source_reference"
            placeholder="如：第三单元测验 / 周练习册 P20"
            class="sheet-input-field"
          />
        </div>

        <div class="form-group">
          <label class="form-label">错因分类</label>
          <div class="sheet-subject-chips">
            <span
              v-for="err in ['概念模糊', '粗心大意', '计算错误', '思路卡壳']"
              :key="err"
              class="st-chip"
              :class="{ active: newMistake.error_type === err }"
              @click="newMistake.error_type = err"
            >
              {{ err }}
            </span>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">拍照或上传错题图片</label>
          <van-uploader
            :after-read="handleUpload"
            v-model="fileList"
            max-count="1"
            preview-size="80px"
          />
        </div>

        <div class="form-group">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <label class="form-label" style="margin-bottom: 0;">题干文字（可编辑）</label>
            <van-button
              size="small"
              type="primary"
              plain
              icon="scan"
              :loading="ocrLoading"
              :disabled="!uploadedFile"
              class="ocr-extract-btn"
              @click="extractText"
            >
              智能提取题干
            </van-button>
          </div>
          <van-field
            v-model="newMistake.extracted_text"
            type="textarea"
            rows="3"
            autosize
            placeholder="填写、粘贴，或先上传图片后点「智能提取题干」"
            class="sheet-input-field"
          />
        </div>

        <div class="modal-footer-btns">
          <van-button block round @click="closeAddModal">取消</van-button>
          <van-button type="primary" block round :loading="submitting" @click="submitAddMistake">保存入册</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 原图预览弹窗 -->
    <van-popup v-model:show="showPreview" round :style="{ padding: '10px', maxWidth: '90%' }">
      <img :src="previewUrl" style="max-width: 100%; max-height: 80vh; object-fit: contain; border-radius: 8px;" alt="原图" />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { showToast } from 'vant';
import { mistakeApi, settingsApi, ocrApi } from '../api';
import { compressImage } from '../utils/imageCompress';

const activeTab = ref('review');
const subjects = ref([]);
const selectedSubject = ref(null);
const selectedStatus = ref(null);
const mistakes = ref([]);
const reviewQueueCount = ref(0);
const refreshing = ref(false);

const showAddModal = ref(false);
const submitting = ref(false);
const fileList = ref([]);
const showPreview = ref(false);
const previewUrl = ref('');
const ocrLoading = ref(false);
const uploadedFile = ref(null);
let pollTimerM = null;

const newMistake = ref({
  subject_id: 1,
  source_reference: '',
  error_type: '概念模糊',
  extracted_text: '',
  original_image_path: null,
  thumbnail_path: null,
  storage_key: null
});

const onTabChange = () => {
  fetchMistakes();
};

const selectSubject = (subId) => {
  selectedSubject.value = subId;
  fetchMistakes();
};

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
    case '道德与法治':
    case '道法': return 'st-subject-tag--danger';
    default: return 'st-subject-tag--neutral';
  }
};

const getStatusClass = (status) => {
  if (status === '已掌握') return 'done';
  return '';
};

const fetchSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    subjects.value = res.data;
    if (subjects.value.length > 0 && !newMistake.value.subject_id) {
      newMistake.value.subject_id = subjects.value[0].id;
    }
  } catch (e) {
    console.error(e);
  }
};

const fetchReviewQueueCount = async () => {
  try {
    const res = await mistakeApi.getReviewQueue();
    reviewQueueCount.value = res.data.length;
  } catch (e) {
    console.error(e);
  }
};

const fetchMistakes = async () => {
  refreshing.value = true;
  try {
    if (activeTab.value === 'review') {
      const res = await mistakeApi.getReviewQueue(selectedSubject.value);
      mistakes.value = res.data;
      reviewQueueCount.value = res.data.length;
    } else {
      const res = await mistakeApi.getList({
        subject_id: selectedSubject.value,
        mastery_status: selectedStatus.value
      });
      mistakes.value = res.data;
      fetchReviewQueueCount();
    }
  } catch (e) {
    showToast('获取错题列表失败');
  } finally {
    refreshing.value = false;
  }
};

const submitReview = async (id, result) => {
  try {
    await mistakeApi.submitReview(id, result);
    if (result === 'remembered') {
      showToast({ message: '掌握啦！记忆周期自动顺延', icon: 'passed' });
    } else {
      showToast({ message: '已重置艾宾浩斯复习周期，明天将再次提醒', icon: 'replay' });
    }
    fetchMistakes();
  } catch (e) {
    showToast('提交复习结果失败');
  }
};

const handleUpload = async (file) => {
  uploadedFile.value = file;
  try {
    showToast({ type: 'loading', message: '处理并上传中...', forbidClick: true, duration: 0 });
    const compressed = await compressImage(file.file);
    const res = await ocrApi.upload(compressed);
    newMistake.value.original_image_path = res.data.original_image_path;
    newMistake.value.thumbnail_path = res.data.thumbnail_path;
    newMistake.value.storage_key = res.data.storage_key;
    showToast({ type: 'success', message: '图片上传成功' });
  } catch (e) {
    showToast('图片上传失败，请重试');
  }
};

const extractText = async () => {
  if (!newMistake.value.storage_key) {
    showToast('请先上传错题图片');
    return;
  }

  ocrLoading.value = true;
  try {
    const res = await ocrApi.createTask(newMistake.value.storage_key);
    const taskId = res.data.task_id;
    pollTimerM = setInterval(async () => {
      try {
        const statusRes = await ocrApi.getTask(taskId);
        if (statusRes.data.status === 'completed') {
          clearInterval(pollTimerM);
          ocrLoading.value = false;
          newMistake.value.extracted_text = statusRes.data.extracted_text;
          showToast({ message: '识别成功，题干已自动提取！', icon: 'success' });
        } else if (statusRes.data.status === 'failed') {
          clearInterval(pollTimerM);
          ocrLoading.value = false;
          showToast('题干提取失败，请手动输入');
        }
      } catch (err) {
        clearInterval(pollTimerM);
        ocrLoading.value = false;
      }
    }, 500);
  } catch (e) {
    ocrLoading.value = false;
    showToast('发起识别任务失败');
  }
};

const submitAddMistake = async () => {
  if (!newMistake.value.subject_id) {
    showToast('请选择学科');
    return;
  }
  if (!newMistake.value.extracted_text && !newMistake.value.thumbnail_path) {
    showToast('请至少填写题干文字或上传错题图片');
    return;
  }

  submitting.value = true;
  try {
    await mistakeApi.create({
      subject_id: newMistake.value.subject_id,
      source_reference: newMistake.value.source_reference,
      error_type: newMistake.value.error_type,
      extracted_text: newMistake.value.extracted_text,
      original_image_path: newMistake.value.original_image_path,
      thumbnail_path: newMistake.value.thumbnail_path
    });
    showToast({ message: '错题录入成功！', icon: 'success' });
    closeAddModal();
    fetchMistakes();
  } catch (e) {
    showToast('录入失败');
  } finally {
    submitting.value = false;
  }
};

const closeAddModal = () => {
  showAddModal.value = false;
  fileList.value = [];
  uploadedFile.value = null;
  newMistake.value = {
    subject_id: subjects.value.length > 0 ? subjects.value[0].id : 1,
    source_reference: '',
    error_type: '概念模糊',
    extracted_text: '',
    original_image_path: null,
    thumbnail_path: null,
    storage_key: null
  };
};

const previewImage = (url) => {
  if (url) {
    previewUrl.value = url;
    showPreview.value = true;
  }
};

onMounted(async () => {
  await fetchSubjects();
  await fetchMistakes();
});
</script>

<style scoped>
.mistake-view {
  min-height: 100vh;
  background-color: var(--st-bg-page, #f8fafc);
  padding: 14px 16px 84px;
}

/* 顶部导航与组卷入口 */
.mistake-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  background: var(--st-bg-card, #ffffff);
  border-radius: var(--st-radius-lg, 14px);
  padding: 4px 12px;
  border: 1px solid var(--st-border, #f1f5f9);
  box-shadow: var(--st-shadow-card, 0 1px 3px rgba(15, 23, 42, 0.04));
}

.mistake-tabs {
  flex: 1;
}

.paper-quick-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--st-primary-light, #eff6ff);
  color: var(--st-primary, #2563eb);
  padding: 6px 12px;
  border-radius: var(--st-radius-full, 9999px);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid rgba(37, 99, 235, 0.2);
  white-space: nowrap;
  transition: all 0.15s ease;
}

.paper-quick-btn:active {
  background: #dbeafe;
  transform: scale(0.97);
}

/* 筛选栏 */
.filter-section {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chips-row {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 2px;
  scrollbar-width: none;
}

.chips-row::-webkit-scrollbar {
  display: none;
}

/* 错题列表 */
.mistake-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mistake-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-text {
  font-size: 11px;
  color: var(--st-text-secondary, #64748b);
}

/* 略缩图容器 */
.card-image-box {
  position: relative;
  width: 100%;
  max-height: 160px;
  border-radius: var(--st-radius-md, 10px);
  overflow: hidden;
  cursor: pointer;
  background: var(--st-bg-subtle, #f1f5f9);
  display: flex;
  justify-content: center;
  align-items: center;
}

.card-image-box img {
  width: 100%;
  max-height: 160px;
  object-fit: cover;
}

.img-preview-tag {
  position: absolute;
  right: 8px;
  bottom: 8px;
  background: rgba(15, 23, 42, 0.7);
  color: #ffffff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--st-radius-full, 9999px);
  backdrop-filter: blur(4px);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.question-text {
  font-size: 14px;
  color: var(--st-text-primary, #0f172a);
  line-height: 1.5;
  margin: 0 0 6px 0;
}

.tags-row {
  display: flex;
  gap: 6px;
}

.error-tag {
  background: var(--st-warning-light, #fffbeb);
  color: var(--st-warning-dark, #d97706);
  font-size: 11px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: var(--st-radius-sm, 6px);
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

/* 艾宾浩斯复习操作区 */
.review-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px solid var(--st-border, #f1f5f9);
}

.review-stat {
  font-size: 12px;
  color: var(--st-text-secondary, #64748b);
  display: flex;
  align-items: center;
  gap: 6px;
}

.next-date {
  color: var(--st-purple, #7c3aed);
  font-size: 11px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.rev-btn {
  font-weight: 600;
}

.empty-state {
  padding: 40px 0;
}

/* 底部常驻悬浮栏 */
.floating-bottom-bar {
  position: fixed;
  bottom: 50px;
  left: 0;
  right: 0;
  max-width: 500px;
  margin: 0 auto;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom));
  z-index: 40;
}

.add-mistake-btn {
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
}

/* 弹窗抽屉 */
.add-modal-body {
  padding: 1rem 1.25rem 1.75rem;
}

.sheet-grabber {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background-color: var(--st-border-bold, #e2e8f0);
  margin: 0 auto 14px;
}

.form-group {
  margin-bottom: 14px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--st-text-regular, #334155);
  margin-bottom: 8px;
}

.sheet-subject-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sheet-input-field {
  background-color: var(--st-bg-subtle, #f1f5f9);
  border-radius: var(--st-radius-md, 10px);
  border: 1px solid var(--st-border, #f1f5f9);
  padding: 8px 12px;
}

.modal-footer-btns {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}
</style>

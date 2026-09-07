<template>
  <div class="mistake-view">
    <!-- 顶部导航栏 (支持常规与批量管理双模切换) -->
    <van-nav-bar
      :title="isBatchMode ? `批量管理 (${selectedIds.length}/${mistakes.length})` : '错题复习本'"
      :left-text="isBatchMode ? '退出' : (mistakes.length > 0 ? '批量管理' : '')"
      :right-text="isBatchMode ? (selectedIds.length === mistakes.length && mistakes.length > 0 ? '取消全选' : '全选') : '周末组卷'"
      @click-left="toggleBatchMode"
      @click-right="onNavRightClick"
    />

    <div class="mistake-content">
      <!-- 顶部主标签页切换 -->
      <div class="mistake-header-bar">
        <van-tabs v-model:active="activeTab" color="#2563eb" line-width="36px" @change="onTabChange" class="mistake-tabs">
          <van-tab
            title="今日复习"
            :badge="reviewQueueCount > 0 ? reviewQueueCount : null"
            name="review"
          />
          <van-tab title="错题总库" name="all" />
        </van-tabs>
      </div>

    <!-- 学科与状态筛选栏 (Chips) -->
    <div class="filter-section">
      <div class="chips-row st-scroll-x">
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
    <van-pull-refresh v-model="refreshing" @refresh="fetchMistakes" :disabled="isBatchMode">
      <div class="mistake-list" v-if="mistakes.length > 0">
        <van-swipe-cell
          v-for="item in mistakes"
          :key="item.id"
          :disabled="isBatchMode"
          class="mistake-swipe-cell"
        >
          <div
            class="st-card mistake-card"
            :class="{ 'is-selected-card': isBatchMode && selectedIds.includes(item.id) }"
            @click="isBatchMode ? toggleSelectItem(item.id) : null"
          >
            <div class="card-main-layout">
              <!-- 批量选择勾选框 -->
              <div class="batch-checkbox-col" v-if="isBatchMode">
                <van-checkbox
                  :model-value="selectedIds.includes(item.id)"
                  @click.stop="toggleSelectItem(item.id)"
                />
              </div>

              <div class="card-inner-content">
                <div class="card-header">
                  <div class="header-left">
                    <span class="st-subject-tag" :class="getSubjectTagClass(item.subject_name)">
                      {{ item.subject_name }}
                    </span>
                    <span class="source-text" v-if="item.source_reference">
                      {{ item.source_reference }}
                    </span>
                  </div>
                  <div class="header-right">
                    <span class="st-status-tag" :class="getMasteryStatusTagClass(item.mastery_status)">
                      {{ item.mastery_status }}
                    </span>
                    <button
                      v-if="!isBatchMode"
                      class="card-del-btn"
                      title="删除错题"
                      @click.stop="handleSingleDelete(item)"
                    >
                      <van-icon name="delete-o" />
                    </button>
                  </div>
                </div>

                <!-- 缩略图展示 (点击可放大原图预览) -->
                <div class="card-image-box" v-if="item.thumbnail_path" @click.stop="previewImage(item.original_image_path || item.thumbnail_path)">
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

                <!-- 艾宾浩斯复习操作区（上下两层分明，大拇指热区充分，彻底消除挤压折行） -->
                <div class="review-action-bar" v-if="!isBatchMode && (activeTab === 'review' || item.mastery_status !== '已掌握')">
                  <div class="review-stat-row">
                    <div class="review-round-info">
                      <span class="st-icon-badge st-icon-badge--purple" style="width: 20px; height: 20px; font-size: 11px;">
                        <van-icon name="replay" />
                      </span>
                      <span>第 <b>{{ item.review_count || 0 }}</b> 轮复习</span>
                    </div>
                    <span v-if="item.next_review_date" class="next-date-tag">
                      下次: {{ item.next_review_date }}
                    </span>
                  </div>
                  <div class="review-buttons-row">
                    <van-button
                      size="small"
                      plain
                      type="danger"
                      icon="cross"
                      class="rev-action-btn"
                      @click.stop="submitReview(item.id, 'forgotten')"
                    >
                      又忘了
                    </van-button>
                    <van-button
                      size="small"
                      type="success"
                      icon="passed"
                      class="rev-action-btn"
                      @click.stop="submitReview(item.id, 'remembered')"
                    >
                      掌握啦
                    </van-button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 左滑呼出的删除操作抽屉 -->
          <template #right>
            <div class="swipe-actions-box">
              <button class="swipe-action-btn btn-delete" @click.stop="handleSingleDelete(item)">
                <van-icon name="delete-o" size="16" />
                <span>删除</span>
              </button>
            </div>
          </template>
        </van-swipe-cell>
      </div>

      <!-- 清爽空状态 -->
      <div class="empty-state" v-else>
        <van-empty :description="activeTab === 'review' ? '今日推荐复习已全部完成！太棒了' : '暂无相关错题'" />
      </div>
    </van-pull-refresh>
    </div>

    <!-- 批量操作常驻磨砂悬浮栏 -->
    <div class="floating-bottom-bar st-frosted-bar batch-bottom-bar" v-if="isBatchMode">
      <div class="batch-left-info">
        已选 <b>{{ selectedIds.length }}</b> / {{ mistakes.length }} 项
      </div>
      <div class="batch-right-actions">
        <van-button
          size="small"
          round
          plain
          @click="toggleSelectAll"
        >
          {{ selectedIds.length === mistakes.length && mistakes.length > 0 ? '取消全选' : '全选全部' }}
        </van-button>
        <van-button
          type="danger"
          size="small"
          round
          icon="delete-o"
          :disabled="selectedIds.length === 0"
          :loading="batchDeleting"
          class="batch-del-btn"
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedIds.length }})
        </van-button>
      </div>
    </div>

    <!-- 常规录入常驻磨砂悬浮栏 -->
    <div class="floating-bottom-bar st-frosted-bar" v-else>
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
import { useRouter } from 'vue-router';
import { showToast, showConfirmDialog } from 'vant';
import { mistakeApi, settingsApi, ocrApi } from '../api';
import { compressImage } from '../utils/imageCompress';

const router = useRouter();

const activeTab = ref('review');
const subjects = ref([]);
const selectedSubject = ref(null);
const selectedStatus = ref(null);
const mistakes = ref([]);
const reviewQueueCount = ref(0);
const refreshing = ref(false);

// 批量管理模式与多选状态
const isBatchMode = ref(false);
const selectedIds = ref([]);
const batchDeleting = ref(false);

const toggleBatchMode = () => {
  if (!isBatchMode.value && mistakes.value.length === 0) {
    showToast('当前列表暂无错题可管理');
    return;
  }
  isBatchMode.value = !isBatchMode.value;
  selectedIds.value = [];
};

const onNavRightClick = () => {
  if (isBatchMode.value) {
    toggleSelectAll();
  } else {
    router.push('/paper');
  }
};

const toggleSelectItem = (id) => {
  const idx = selectedIds.value.indexOf(id);
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1);
  } else {
    selectedIds.value.push(id);
  }
};

const toggleSelectAll = () => {
  if (selectedIds.value.length === mistakes.value.length) {
    selectedIds.value = [];
  } else {
    selectedIds.value = mistakes.value.map((m) => m.id);
  }
};

const handleSingleDelete = (item) => {
  showConfirmDialog({
    title: '确认删除错题',
    message: `确定要删除此条错题吗？\n「${(item.extracted_text || item.source_reference || '该错题').substring(0, 30)}...」`,
    confirmButtonText: '删除',
    confirmButtonColor: '#ef4444'
  }).then(async () => {
    try {
      await mistakeApi.delete(item.id);
      showToast({ message: '已删除', position: 'bottom' });
      fetchMistakes();
      fetchReviewQueueCount();
    } catch (err) {
      showToast('删除失败');
    }
  }).catch(() => {});
};

const handleBatchDelete = () => {
  if (selectedIds.value.length === 0) return;
  showConfirmDialog({
    title: '批量删除确认',
    message: `确定要彻底删除已选中的 ${selectedIds.value.length} 项错题吗？\n删除后不可恢复。`,
    confirmButtonText: '彻底删除',
    confirmButtonColor: '#ef4444'
  }).then(async () => {
    batchDeleting.value = true;
    try {
      const res = await mistakeApi.batchDelete(selectedIds.value);
      showToast({
        message: `已成功删除 ${res.data?.deleted_count ?? selectedIds.value.length} 项错题`,
        icon: 'passed'
      });
      selectedIds.value = [];
      isBatchMode.value = false;
      fetchMistakes();
      fetchReviewQueueCount();
    } catch (err) {
      showToast('批量删除失败');
    } finally {
      batchDeleting.value = false;
    }
  }).catch(() => {});
};

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
  isBatchMode.value = false;
  selectedIds.value = [];
  mistakes.value = [];
  fetchMistakes();
};

const selectSubject = (subId) => {
  selectedSubject.value = subId;
  selectedIds.value = [];
  mistakes.value = [];
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
    case '道法':
    case '道法': return 'st-subject-tag--danger';
    default: return 'st-subject-tag--neutral';
  }
};

const getMasteryStatusTagClass = (status) => {
  switch (status) {
    case '已掌握': return 'st-status-tag--success';
    case '待复习': return 'st-status-tag--warning';
    case '未掌握': return 'st-status-tag--danger';
    default: return 'st-status-tag--neutral';
  }
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
    const res = await mistakeApi.submitReview(id, result);
    const updated = res.data;
    if (result === 'remembered') {
      if (updated.mastery_status === '已掌握') {
        showToast({ message: '太棒了！已完成 4 轮复习，彻底掌握并进入长效库！', icon: 'passed', duration: 2500 });
      } else {
        const nextDate = updated.next_review_date ? `下次: ${updated.next_review_date}` : '';
        showToast({ message: `掌握啦！推进至第 ${updated.review_count} 轮 (${nextDate})`, icon: 'passed', duration: 2500 });
      }
    } else {
      showToast({ message: '已重置艾宾浩斯复习周期，明天将再次提醒', icon: 'replay', duration: 2000 });
    }
    fetchMistakes();
  } catch (e) {
    const msg = e.response?.data?.detail || '提交复习结果失败';
    showToast(msg);
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
    const msg = e.response?.data?.detail || '错题录入失败，请检查填写内容';
    showToast(msg);
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
  flex: 1;
  background-color: var(--st-bg-page, #f8fafc);
  display: flex;
  flex-direction: column;
}

.mistake-content {
  padding: 12px 14px 100px;
}

/* 顶部标签页切换条 */
.mistake-header-bar {
  margin-bottom: 12px;
  background: var(--st-bg-card, #ffffff);
  border-radius: var(--st-radius-lg, 14px);
  padding: 2px 6px;
  border: 1px solid var(--st-border, #f1f5f9);
  box-shadow: var(--st-shadow-card, 0 1px 3px rgba(15, 23, 42, 0.04));
}

.mistake-tabs {
  width: 100%;
}

.mistake-tabs :deep(.van-tabs__nav) {
  padding-left: 0;
}

.mistake-tabs :deep(.van-tab) {
  padding: 0 16px;
  font-size: 15px;
  font-weight: 500;
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
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--st-border, #f1f5f9);
}

.review-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.review-round-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--st-text-secondary, #64748b);
}

.next-date-tag {
  font-size: 11px;
  color: var(--st-purple, #7c3aed);
  background: var(--st-purple-light, #f5f3ff);
  padding: 2px 6px;
  border-radius: var(--st-radius-sm, 4px);
  font-weight: 500;
}

.review-buttons-row {
  display: flex;
  gap: 10px;
}

.rev-action-btn {
  flex: 1;
  font-weight: 600;
  white-space: nowrap !important;
}

.empty-state {
  padding: 40px 0;
}

/* 底部常驻悬浮栏 */
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

.add-mistake-btn {
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
}

/* 滑动与批量管理样式 */
.mistake-swipe-cell {
  border-radius: var(--st-radius-md, 14px);
  overflow: hidden;
  margin-bottom: 12px;
}

.card-main-layout {
  display: flex;
  align-items: flex-start;
  width: 100%;
}

.batch-checkbox-col {
  padding: 16px 8px 16px 14px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.card-inner-content {
  flex: 1;
  min-width: 0;
}

.is-selected-card {
  border-color: var(--st-primary, #2563eb) !important;
  background-color: #f8faff !important;
  box-shadow: 0 3px 12px rgba(37, 99, 235, 0.15) !important;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-del-btn {
  border: none;
  background: transparent;
  padding: 2px;
  font-size: 16px;
  color: var(--st-text-muted, #94a3b8);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.card-del-btn:hover {
  color: var(--st-danger, #ef4444);
  background-color: #fef2f2;
}

.swipe-actions-box {
  display: flex;
  height: 100%;
}

.swipe-action-btn {
  border: none;
  height: 100%;
  padding: 0 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.swipe-action-btn.btn-delete {
  background-color: var(--st-danger, #ef4444);
}

.batch-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.batch-left-info {
  font-size: 13px;
  font-weight: 600;
  color: var(--st-text-primary, #0f172a);
}

.batch-left-info b {
  color: var(--st-primary, #2563eb);
  font-size: 15px;
}

.batch-right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.batch-del-btn {
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.25);
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

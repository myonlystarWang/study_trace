<template>
  <div class="mistake-view">
    <!-- 顶部主标签页切换 -->
    <van-tabs v-model:active="activeTab" color="#2563eb" line-width="40px" @change="onTabChange">
      <van-tab title="今日复习" name="review">
        <template #title>
          <span>今日待复习</span>
          <van-badge v-if="reviewQueueCount > 0" :content="reviewQueueCount" />
        </template>
      </van-tab>
      <van-tab title="错题总库" name="all"></van-tab>
    </van-tabs>

    <!-- 学科与筛选过滤器 -->
    <div class="filter-section">
      <div class="chips-row">
        <div
          class="chip"
          :class="{ active: selectedSubject === null }"
          @click="selectSubject(null)"
        >
          全部学科
        </div>
        <div
          v-for="sub in subjects"
          :key="sub.id"
          class="chip"
          :class="{ active: selectedSubject === sub.id }"
          @click="selectSubject(sub.id)"
        >
          {{ sub.name }}
        </div>
      </div>

      <!-- 状态过滤（仅在总库标签下展示） -->
      <div class="chips-row" v-if="activeTab === 'all'">
        <div
          v-for="status in ['全部状态', '未掌握', '待复习', '已掌握']"
          :key="status"
          class="status-chip"
          :class="{ active: selectedStatus === (status === '全部状态' ? null : status) }"
          @click="selectedStatus = (status === '全部状态' ? null : status); fetchMistakes()"
        >
          {{ status }}
        </div>
      </div>
    </div>

    <!-- 错题列表 -->
    <van-pull-refresh v-model="refreshing" @refresh="fetchMistakes">
      <div class="mistake-list" v-if="mistakes.length > 0">
        <div
          v-for="item in mistakes"
          :key="item.id"
          class="mistake-card"
        >
          <div class="card-header">
            <div class="header-left">
              <span class="sub-badge">{{ item.subject_name }}</span>
              <span class="source-text" v-if="item.source_reference">{{ item.source_reference }}</span>
            </div>
            <span class="status-tag" :class="getStatusClass(item.mastery_status)">
              {{ item.mastery_status }}
            </span>
          </div>

          <!-- 缩略图展示 -->
          <div class="card-image-box" v-if="item.thumbnail_path">
            <img :src="item.thumbnail_path" @click="previewImage(item.original_image_path || item.thumbnail_path)" alt="题目图" />
          </div>

          <!-- 题目文本内容 -->
          <div class="card-body">
            <p class="question-text">{{ item.extracted_text || '暂无文字题干，请查看图片' }}</p>
            <div class="tags-row" v-if="item.error_type">
              <span class="error-tag">{{ item.error_type }}</span>
            </div>
          </div>

          <!-- 艾宾浩斯复习操作区（在今日复习模式或待复习时醒目展示） -->
          <div class="review-action-bar" v-if="activeTab === 'review' || item.mastery_status !== '已掌握'">
            <div class="review-stat">
              复习次数: <b>{{ item.review_count || 0 }}</b> 次
              <span v-if="item.next_review_date" class="next-date">下次: {{ item.next_review_date }}</span>
            </div>
            <div class="action-buttons">
              <button class="rev-btn forget-btn" @click="submitReview(item.id, 'forgotten')">
                ✕ 又忘了
              </button>
              <button class="rev-btn remember-btn" @click="submitReview(item.id, 'remembered')">
                ✓ 掌握啦
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="empty-state" v-else>
        <van-empty :description="activeTab === 'review' ? '今日推荐复习已全部完成！太棒了' : '暂无相关错题'" />
      </div>
    </van-pull-refresh>

    <!-- 底部悬浮添加按钮 -->
    <div class="fab-add" @click="showAddModal = true">
      <span>＋ 录入错题</span>
    </div>

    <!-- 录入错题弹窗 -->
    <van-popup v-model:show="showAddModal" position="bottom" round :style="{ maxHeight: '85%' }">
      <div class="add-modal-body">
        <h3>录入错题</h3>
        
        <div class="form-group">
          <label>学科</label>
          <div class="sub-grid">
            <div
              v-for="sub in subjects"
              :key="sub.id"
              class="sub-item"
              :class="{ active: newMistake.subject_id === sub.id }"
              @click="newMistake.subject_id = sub.id"
            >
              {{ sub.name }}
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>来源说明（选填）</label>
          <van-field v-model="newMistake.source_reference" placeholder="如：第三单元测验 / 周练习册 P20" />
        </div>

        <div class="form-group">
          <label>错因分类</label>
          <div class="error-types-grid">
            <div
              v-for="err in ['概念模糊', '粗心大意', '计算错误', '思路卡壳']"
              :key="err"
              class="err-item"
              :class="{ active: newMistake.error_type === err }"
              @click="newMistake.error_type = err"
            >
              {{ err }}
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>拍照或上传错题图片</label>
          <van-uploader
            :after-read="handleUpload"
            v-model="fileList"
            max-count="1"
            preview-size="80px"
          />
        </div>

        <div class="form-group">
          <label>题干文字（可编辑）</label>
          <van-button
            size="small"
            type="primary"
            plain
            :loading="ocrLoading"
            :disabled="!uploadedFile"
            class="ocr-extract-btn"
            @click="extractText"
          >
            🔍 一键提取题干
          </van-button>
          <van-field
            v-model="newMistake.extracted_text"
            type="textarea"
            rows="3"
            autosize
            placeholder="填写、粘贴，或先上传图片后点「一键提取题干」"
          />
        </div>

        <div class="modal-footer-btns">
          <van-button block @click="showAddModal = false">取消</van-button>
          <van-button type="primary" block :loading="submitting" @click="submitAddMistake">保存入册</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 原图预览弹窗 -->
    <van-popup v-model:show="showPreview" round :style="{ padding: '10px', maxWidth: '90%' }">
      <img :src="previewUrl" style="max-width: 100%; max-height: 80vh; object-fit: contain; border-radius: 8px;" />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
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
  thumbnail_path: null
});

const onTabChange = () => {
  fetchMistakes();
};

const selectSubject = (subId) => {
  selectedSubject.value = subId;
  fetchMistakes();
};

const getStatusClass = (status) => {
  if (status === '已掌握') return 'status-mastered';
  if (status === '待复习') return 'status-review';
  return 'status-unmastered';
};

const fetchSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    subjects.value = res.data;
    if (subjects.value.length > 0) {
      newMistake.value.subject_id = subjects.value[0].id;
    }
  } catch (e) {
    console.error(e);
  }
};

const fetchMistakes = async () => {
  refreshing.value = true;
  try {
    const params = {
      subject_id: selectedSubject.value || undefined,
      ebbinghaus_today: activeTab.value === 'review',
      mastery_status: activeTab.value === 'all' ? (selectedStatus.value || undefined) : undefined
    };
    const res = await mistakeApi.getList(params);
    mistakes.value = res.data;

    // 如果在全部标签，额外获取一下今日待复习数量
    if (activeTab.value === 'all') {
      const revRes = await mistakeApi.getList({ ebbinghaus_today: true });
      reviewQueueCount.value = revRes.data.length;
    } else {
      reviewQueueCount.value = res.data.length;
    }
  } catch (e) {
    showToast('加载错题失败');
  } finally {
    refreshing.value = false;
  }
};

const submitReview = async (id, result) => {
  try {
    await mistakeApi.review(id, result);
    if (result === 'remembered') {
      showToast({ message: '太棒了！已推进复习进度', icon: 'passed' });
    } else {
      showToast({ message: '已重设为明日复习', icon: 'replay' });
    }
    fetchMistakes();
  } catch (e) {
    showToast('记录复习失败');
  }
};

const handleUpload = async (fileItem) => {
  showToast({ message: '正在压缩图片...', duration: 1000 });
  try {
    const compressed = await compressImage(fileItem.file, 1600, 0.82);
    uploadedFile.value = compressed.file;
    const formData = new FormData();
    formData.append('file', compressed.file);
    const res = await mistakeApi.uploadImage(formData);
    newMistake.value.original_image_path = res.data.original_url;
    newMistake.value.thumbnail_path = res.data.thumbnail_url;
    showToast({ message: '图片上传成功', icon: 'success' });
  } catch (e) {
    showToast('上传失败');
  }
};

const extractText = async () => {
  if (!uploadedFile.value) {
    showToast('请先上传错题图片');
    return;
  }
  ocrLoading.value = true;
  if (pollTimerM) clearInterval(pollTimerM);
  try {
    const fd = new FormData();
    fd.append('file', uploadedFile.value);
    fd.append('mode', 'auto');
    const res = await ocrApi.createTask(fd);
    const taskId = res.data.task_id;
    pollTimerM = setInterval(async () => {
      try {
        const r = await ocrApi.getTask(taskId);
        const t = r.data;
        if (t.status === 'succeeded') {
          clearInterval(pollTimerM);
          pollTimerM = null;
          ocrLoading.value = false;
          newMistake.value.extracted_text = t.result.text;
          showToast({ message: `识别完成（${t.result.engine}）`, icon: 'success' });
        } else if (t.status === 'failed') {
          clearInterval(pollTimerM);
          pollTimerM = null;
          ocrLoading.value = false;
          showToast('识别失败，请手动输入题干');
        }
      } catch (e) {
        clearInterval(pollTimerM);
        pollTimerM = null;
        ocrLoading.value = false;
        showToast('查询识别状态失败');
      }
    }, 600);
  } catch (e) {
    ocrLoading.value = false;
    showToast('提交识别失败');
  }
};

const submitAddMistake = async () => {
  if (!newMistake.value.extracted_text.trim() && !newMistake.value.original_image_path) {
    showToast('请至少输入题干文字或上传图片');
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
    showToast({ message: '错题已归入艾宾浩斯复习流', icon: 'success' });
    showAddModal.value = false;
    fileList.value = [];
    newMistake.value.extracted_text = '';
    newMistake.value.source_reference = '';
    newMistake.value.original_image_path = null;
    fetchMistakes();
  } catch (e) {
    showToast('保存错题失败');
  } finally {
    submitting.value = false;
  }
};

const previewImage = (url) => {
  previewUrl.value = url;
  showPreview.value = true;
};

watch(showAddModal, (v) => {
  if (!v && pollTimerM) {
    clearInterval(pollTimerM);
    pollTimerM = null;
    ocrLoading.value = false;
  }
});

onMounted(async () => {
  await fetchSubjects();
  await fetchMistakes();
});
</script>

<style scoped>
.mistake-view {
  padding: 0.5rem 1rem 6rem;
  background: #f8fafc;
  min-height: 100vh;
}

.filter-section {
  margin: 0.75rem 0;
}

.chips-row {
  display: flex;
  gap: 0.4rem;
  overflow-x: auto;
  padding-bottom: 0.4rem;
  scrollbar-width: none;
}

.chips-row::-webkit-scrollbar {
  display: none;
}

.chip, .status-chip {
  padding: 0.3rem 0.75rem;
  background: #f1f5f9;
  border-radius: 16px;
  font-size: 0.8rem;
  color: #475569;
  white-space: nowrap;
  cursor: pointer;
}

.chip.active, .status-chip.active {
  background: #2563eb;
  color: white;
  font-weight: 600;
}

.mistake-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.mistake-card {
  background: white;
  border-radius: 16px;
  padding: 1rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
}

.sub-badge {
  background: #eff6ff;
  color: #2563eb;
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
  font-weight: 600;
  margin-right: 0.5rem;
}

.source-text {
  font-size: 0.75rem;
  color: #64748b;
}

.status-tag {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
  font-weight: 600;
}

.status-unmastered {
  background: #fee2e2;
  color: #ef4444;
}

.status-review {
  background: #fef3c7;
  color: #d97706;
}

.status-mastered {
  background: #d1fae5;
  color: #059669;
}

.card-image-box {
  margin-bottom: 0.6rem;
  max-height: 160px;
  overflow: hidden;
  border-radius: 8px;
  background: #f1f5f9;
  display: flex;
  justify-content: center;
}

.card-image-box img {
  width: 100%;
  object-fit: cover;
}

.question-text {
  font-size: 0.95rem;
  color: #1e293b;
  line-height: 1.5;
  margin-bottom: 0.5rem;
}

.tags-row {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.error-tag {
  background: #f3f4f6;
  color: #4b5563;
  font-size: 0.75rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.review-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #f1f5f9;
}

.review-stat {
  font-size: 0.8rem;
  color: #64748b;
}

.next-date {
  margin-left: 0.4rem;
  color: #ea580c;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
}

.rev-btn {
  border: none;
  padding: 0.35rem 0.8rem;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.forget-btn {
  background: #fff7ed;
  color: #ea580c;
}

.remember-btn {
  background: #ecfdf5;
  color: #059669;
}

.fab-add {
  position: fixed;
  bottom: 70px;
  right: 20px;
  background: #2563eb;
  color: white;
  padding: 0.75rem 1.25rem;
  border-radius: 30px;
  font-size: 0.95rem;
  font-weight: 600;
  box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
  cursor: pointer;
  z-index: 99;
}

.add-modal-body {
  padding: 1.5rem;
}

.add-modal-body h3 {
  margin-bottom: 1.25rem;
  font-size: 1.15rem;
  color: #0f172a;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.4rem;
}

.ocr-extract-btn {
  margin-bottom: 0.5rem;
}

.sub-grid, .error-types-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.sub-item, .err-item {
  padding: 0.35rem 0.75rem;
  background: #f1f5f9;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #475569;
  cursor: pointer;
}

.sub-item.active, .err-item.active {
  background: #2563eb;
  color: white;
  font-weight: 600;
}

.modal-footer-btns {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
}
</style>

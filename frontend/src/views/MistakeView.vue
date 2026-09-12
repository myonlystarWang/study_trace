<template>
  <div class="mistake-view">
    <!-- 顶部导航栏 (常规与批量双模切换，纯净无冗余文字) -->
    <van-nav-bar
      :title="isBatchMode ? `批量管理 (已选 ${selectedIds.length}/${mistakes.length} 项)` : '错题复习本'"
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
                  <span class="st-status-tag" :class="getMasteryStatusTagClass(item.mastery_status)">
                    {{ item.mastery_status }}
                  </span>
                </div>

                <!-- 缩略图展示 (点击可放大原图预览) -->
                <div class="card-image-box" v-if="item.thumbnail_path" @click.stop="previewImage(item.original_image_path || item.thumbnail_path)">
                  <img :src="item.thumbnail_path" alt="题目图" />
                  <span class="img-preview-tag">
                    <van-icon name="search" /> 点击放大原图
                  </span>
                </div>

                <!-- 题目配图（数轴/几何图），不含批改订正笔迹，复习与打印都用它 -->
                <div
                  class="card-diagram-box"
                  v-if="item.cropped_diagram_path"
                  @click.stop="previewImage(item.cropped_diagram_path)"
                >
                  <img :src="item.cropped_diagram_path" alt="题目配图" />
                  <span class="img-preview-tag">
                    <van-icon name="search" /> 题目配图
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
                      <span class="st-icon-badge st-icon-badge--purple" style="width: 20px; height: 20px; font-size: var(--st-font-xs);">
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
                    <van-button
                      size="small"
                      plain
                      type="primary"
                      class="rev-action-btn btn-answer"
                      :icon="openedAnswerIds.includes(item.id) ? 'eye-o' : 'closed-eye'"
                      @click.stop="toggleAnswer(item.id)"
                    >
                      {{ openedAnswerIds.includes(item.id) ? '收起答案' : '查看答案' }}
                    </van-button>
                  </div>
                </div>

                <!-- 针对已掌握状态的轻量答案查看栏 -->
                <div class="mastered-answer-bar" v-if="!isBatchMode && activeTab !== 'review' && item.mastery_status === '已掌握'">
                  <button class="toggle-answer-pill" @click.stop="toggleAnswer(item.id)">
                    <van-icon :name="openedAnswerIds.includes(item.id) ? 'eye-o' : 'closed-eye'" />
                    <span>{{ openedAnswerIds.includes(item.id) ? '收起答案' : '查看答案与解析' }}</span>
                  </button>
                </div>

                <!-- 隐藏答案平滑滑动展开面板 -->
                <transition name="van-slide-down">
                  <div class="card-answer-panel" v-if="openedAnswerIds.includes(item.id)">
                    <div class="answer-header">
                      <span class="st-icon-badge st-icon-badge--info" style="width: 18px; height: 18px; font-size: var(--st-font-xs);">
                        <van-icon name="notes-o" />
                      </span>
                      <span class="answer-title">参考答案与解析</span>
                    </div>
                    <div class="answer-body">
                      <p class="answer-text">{{ item.answer || '暂无详细答案与解析，可左滑点击「编辑」进行补充。' }}</p>
                    </div>
                  </div>
                </transition>
              </div>
            </div>
          </div>

          <!-- 左滑呼出的操作抽屉（编辑 + 删除） -->
          <template #right>
            <div class="swipe-actions-box">
              <button class="swipe-action-btn btn-edit" @click.stop="openEditMistake(item)">
                <van-icon name="edit" size="16" />
                <span>编辑</span>
              </button>
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

    <!-- 批量管理模式：底部三合一操作栏 [退出] [全选/取消全选] [批量删除 (X)] -->
    <div class="floating-bottom-bar st-frosted-bar" v-if="isBatchMode">
      <div class="mistake-bottom-actions">
        <van-button
          round
          icon="cross"
          class="action-btn-secondary st-action-btn st-action-btn--secondary"
          @click="toggleBatchMode"
        >
          退出
        </van-button>
        <van-button
          round
          :icon="selectedIds.length === mistakes.length && mistakes.length > 0 ? 'passed' : 'circle'"
          class="action-btn-secondary st-action-btn st-action-btn--secondary"
          @click="toggleSelectAll"
        >
          {{ selectedIds.length === mistakes.length && mistakes.length > 0 ? '取消全选' : '全选' }}
        </van-button>
        <van-button
          type="danger"
          round
          icon="delete-o"
          :disabled="selectedIds.length === 0"
          :loading="batchDeleting"
          class="action-btn-primary action-btn-danger st-action-btn st-action-btn--danger"
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedIds.length }})
        </van-button>
      </div>
    </div>

    <!-- 常规模式：底部三合一操作栏 [+ 录入新错题] [批量管理] [周末组卷] -->
    <div class="floating-bottom-bar st-frosted-bar" v-else>
      <div class="mistake-bottom-actions">
        <van-button
          type="primary"
          round
          icon="plus"
          class="action-btn-primary st-action-btn st-action-btn--primary"
          @click="showAddModal = true"
        >
          录入新错题
        </van-button>
        <van-button
          round
          icon="apps-o"
          class="action-btn-secondary st-action-btn st-action-btn--secondary"
          @click="toggleBatchMode"
        >
          批量管理
        </van-button>
        <van-button
          round
          icon="notes-o"
          class="action-btn-secondary action-btn-paper st-action-btn st-action-btn--accent"
          @click="router.push('/paper')"
        >
          组卷
        </van-button>
      </div>
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
          <p class="upload-hint">拍完会自动进入框选裁剪，确认后立即识别题干</p>
        </div>

        <div class="form-group">
          <label class="form-label">题目配图（选填）</label>
          <div class="diagram-picker">
            <div class="diagram-thumb" v-if="newMistake.cropped_diagram_path">
              <img
                :src="newMistake.cropped_diagram_path"
                alt="题目配图"
                @click="previewImage(newMistake.cropped_diagram_path)"
              />
              <div class="diagram-thumb-actions">
                <button class="mini-btn" @click="openDiagramCropper">重框</button>
                <button class="mini-btn mini-btn--danger" @click="removeNewDiagram">删除</button>
              </div>
            </div>
            <van-button
              v-else
              size="small"
              type="primary"
              plain
              icon="photograph"
              :disabled="!pendingUploadFile"
              class="diagram-add-btn"
              @click="openDiagramCropper"
            >
              框选图形
            </van-button>
            <p class="upload-hint">
              数轴、几何图等图形无法被文字识别保留，单独框出来存成配图；不添加则复习打印只出文字
            </p>
          </div>
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
              loading-text="识别中..."
              :disabled="!newMistake.original_image_path"
              class="ocr-extract-btn"
              @click="extractText"
            >
              重新识别题干
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

        <div class="form-group">
          <label class="form-label">参考答案与解析（选填，用于复习对照）</label>
          <van-field
            v-model="newMistake.answer"
            type="textarea"
            rows="2"
            autosize
            placeholder="填写参考答案、解题思路或易错点（默认隐藏，复习时可随时展开查看）"
            class="sheet-input-field"
          />
        </div>

        <div class="modal-footer-btns">
          <van-button block round @click="closeAddModal">取消</van-button>
          <van-button type="primary" block round :loading="submitting" @click="submitAddMistake">保存入册</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 编辑错题底部半屏抽屉 (Bottom Sheet) -->
    <van-popup
      v-model:show="showEditModal"
      position="bottom"
      round
      class="bottom-sheet-modal"
      :style="{ maxHeight: '85%' }"
    >
      <div class="add-modal-body" v-if="editingMistake">
        <div class="sheet-grabber"></div>
        <div class="st-section-header">
          <span class="st-icon-badge st-icon-badge--info">
            <van-icon name="edit" />
          </span>
          <span class="section-title">编辑错题</span>
        </div>

        <div class="form-group">
          <label class="form-label">学科</label>
          <div class="sheet-subject-chips">
            <span
              v-for="sub in subjects"
              :key="sub.id"
              class="st-chip"
              :class="{ active: editingMistake.subject_id === sub.id }"
              @click="editingMistake.subject_id = sub.id"
            >
              {{ sub.name }}
            </span>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">来源说明</label>
          <van-field
            v-model="editingMistake.source_reference"
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
              :class="{ active: editingMistake.error_type === err }"
              @click="editingMistake.error_type = err"
            >
              {{ err }}
            </span>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">掌握状态</label>
          <div class="sheet-subject-chips">
            <span
              v-for="st in ['未掌握', '待复习', '已掌握']"
              :key="st"
              class="st-chip"
              :class="{ active: editingMistake.mastery_status === st }"
              @click="editingMistake.mastery_status = st"
            >
              {{ st }}
            </span>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">题目图片</label>
          <div class="edit-image-section">
            <!-- 题干图：孩子试卷的裁剪照，常带批改与订正笔迹，可删可换 -->
            <div class="edit-image-row">
              <div class="edit-image-body">
                <span class="edit-image-label">题干图</span>
                <div class="diagram-thumb" v-if="editingMistake.thumbnail_path || editingMistake.original_image_path">
                  <img
                    :src="editingMistake.thumbnail_path || editingMistake.original_image_path"
                    alt="题干图"
                    @click="previewImage(editingMistake.original_image_path || editingMistake.thumbnail_path)"
                  />
                </div>
                <span class="edit-image-empty" v-else>无</span>
              </div>
              <div class="edit-image-actions">
                <button class="mini-btn" :disabled="editBusy" @click="openEditCropper('question')">重框</button>
                <button
                  class="mini-btn mini-btn--danger"
                  :disabled="editBusy || !editingMistake.original_image_path"
                  @click="deleteEditImage('question')"
                >
                  删除
                </button>
              </div>
            </div>

            <!-- 配图：只保留图形，复习与打印专用 -->
            <div class="edit-image-row">
              <div class="edit-image-body">
                <span class="edit-image-label">题目配图</span>
                <div class="diagram-thumb" v-if="editingMistake.cropped_diagram_path">
                  <img
                    :src="editingMistake.cropped_diagram_path"
                    alt="题目配图"
                    @click="previewImage(editingMistake.cropped_diagram_path)"
                  />
                </div>
                <span class="edit-image-empty" v-else>无</span>
              </div>
              <div class="edit-image-actions">
                <button
                  class="mini-btn"
                  :disabled="editBusy || !(editingMistake.original_image_path || editingMistake.thumbnail_path || editingMistake.cropped_diagram_path)"
                  @click="openEditCropper('diagram')"
                >
                  框选
                </button>
                <button
                  class="mini-btn mini-btn--danger"
                  :disabled="editBusy || !editingMistake.cropped_diagram_path"
                  @click="deleteEditImage('diagram')"
                >
                  删除
                </button>
              </div>
            </div>
            <p class="upload-hint">
              复习卷只打印「题目配图」。题干图常带订正笔迹，若不想保留可直接删除。
            </p>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">题干文字（可编辑）</label>
          <van-field
            v-model="editingMistake.extracted_text"
            type="textarea"
            rows="3"
            autosize
            placeholder="题干文字内容"
            class="sheet-input-field"
          />
        </div>

        <div class="form-group">
          <label class="form-label">参考答案与解析（选填）</label>
          <van-field
            v-model="editingMistake.answer"
            type="textarea"
            rows="2"
            autosize
            placeholder="填写参考答案或解题步骤"
            class="sheet-input-field"
          />
        </div>

        <div class="modal-footer-btns">
          <van-button block round @click="showEditModal = false">取消</van-button>
          <van-button type="primary" block round :loading="savingEdit" @click="submitEditMistake">保存修改</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 原图预览弹窗 -->
    <van-popup v-model:show="showPreview" round :style="{ padding: '10px', maxWidth: '90%' }">
      <img :src="previewUrl" style="max-width: 100%; max-height: 80vh; object-fit: contain; border-radius: 8px;" alt="原图" />
    </van-popup>

    <!-- 错题拍照框选裁剪弹窗（题干 / 配图 两种模式复用同一组件） -->
    <ImageCropper
      v-if="showCropper"
      v-model:show="showCropper"
      :image-url="cropperImageUrl"
      :title="cropperText.title"
      :tip="cropperText.tip"
      :confirm-text="cropperText.confirmText"
      :skip-text="cropperText.skipText"
      @crop="onCropConfirm"
      @skip="onCropSkip"
      @cancel="onCropCancel"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { showToast, showConfirmDialog, closeToast } from 'vant';
import { mistakeApi, settingsApi, ocrApi } from '../api';
import { compressImage } from '../utils/imageCompress';
import ImageCropper from '../components/ImageCropper.vue';

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
    if (activeTab.value === 'review') {
      showToast('今日复习暂无错题，可切换到「错题总库」管理全部错题');
    } else {
      showToast('当前列表暂无错题可管理');
    }
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
const editBusy = ref(false);
let pollTimerM = null;
let ocrPollCount = 0;
const OCR_MAX_POLLS = 60; // 500ms × 60 ≈ 30s 识别上限，超时给出明确提示而不是无限等待

// 图片框选裁剪状态
// cropperMode: question = 题干图（original/thumbnail）；diagram = 题目配图（数轴/几何图）
const showCropper = ref(false);
const cropperImageUrl = ref('');
const cropperMode = ref('question');
const pendingUploadFile = ref(null);
// 编辑态裁剪：非 null 时表示本次裁剪是给某条已存记录换图
const editCropKind = ref(null);

const CROPPER_TEXT = {
  question: {
    title: '框选裁剪题目',
    tip: '拖拽四周手柄框选题目区域，尽量把批改和订正笔迹排除在外',
    confirmText: '确认框选区域并识别',
    skipText: '跳过裁剪'
  },
  diagram: {
    title: '框选题目中的图形',
    tip: '把数轴、几何图等图形单独框出来，只用于复习打印，不影响题干文字',
    confirmText: '确认添加配图',
    skipText: '不添加配图'
  }
};
const cropperText = computed(() => CROPPER_TEXT[cropperMode.value] || CROPPER_TEXT.question);

// 答案查看展开状态
const openedAnswerIds = ref([]);
const toggleAnswer = (id) => {
  const idx = openedAnswerIds.value.indexOf(id);
  if (idx >= 0) {
    openedAnswerIds.value.splice(idx, 1);
  } else {
    openedAnswerIds.value.push(id);
  }
};

// 编辑错题状态
const showEditModal = ref(false);
const savingEdit = ref(false);
const editingMistake = ref(null);

const openEditMistake = (item) => {
  editingMistake.value = {
    id: item.id,
    subject_id: item.subject_id,
    source_reference: item.source_reference || '',
    error_type: item.error_type || '概念模糊',
    extracted_text: item.extracted_text || '',
    answer: item.answer || '',
    mastery_status: item.mastery_status || '未掌握',
    original_image_path: item.original_image_path || null,
    thumbnail_path: item.thumbnail_path || null,
    cropped_diagram_path: item.cropped_diagram_path || null
  };
  showEditModal.value = true;
};

/** 编辑态：打开裁剪器给已存记录换图 */
const openEditCropper = (kind) => {
  const target = editingMistake.value;
  if (!target) return;
  // 题干图缺失时退而用缩略图；配图可从题干图或原配图上再框
  const url = kind === 'question'
    ? (target.original_image_path || target.thumbnail_path)
    : (target.original_image_path || target.thumbnail_path || target.cropped_diagram_path);
  if (!url) {
    showToast('这张记录没有可用的底图，请重新拍照上传');
    return;
  }
  editCropKind.value = kind;
  cropperMode.value = kind;
  cropperImageUrl.value = url;
  showCropper.value = true;
};

/** 编辑态：裁剪结果写回记录（先清旧图回收文件，再写入新图） */
const replaceEditImage = async (kind, cropData) => {
  const target = editingMistake.value;
  if (!target || !cropData?.file) return;
  editBusy.value = true;
  try {
    showToast({ type: 'loading', message: '图片处理中...', forbidClick: true, duration: 0 });
    const data = await uploadImageFile(cropData.file);
    await mistakeApi.deleteImage(target.id, kind);
    if (kind === 'question') {
      await mistakeApi.update(target.id, {
        original_image_path: data.original_url,
        thumbnail_path: data.thumbnail_url
      });
      target.original_image_path = data.original_url;
      target.thumbnail_path = data.thumbnail_url;
    } else {
      await mistakeApi.update(target.id, { cropped_diagram_path: data.original_url });
      target.cropped_diagram_path = data.original_url;
    }
    closeToast();
    showToast({ message: kind === 'question' ? '题目图片已更换' : '配图已更新', icon: 'success' });
    fetchMistakes();
  } catch (e) {
    closeToast();
    showToast('图片保存失败，请重试');
  } finally {
    editBusy.value = false;
  }
};

/** 编辑态：删除题干图或配图 */
const deleteEditImage = async (kind) => {
  const target = editingMistake.value;
  if (!target) return;
  try {
    await showConfirmDialog({
      title: kind === 'question' ? '删除题目图片' : '删除配图',
      message: '删除后不可恢复，确定删除吗？'
    });
  } catch (e) {
    return;
  }
  editBusy.value = true;
  try {
    await mistakeApi.deleteImage(target.id, kind);
    if (kind === 'question') {
      target.original_image_path = null;
      target.thumbnail_path = null;
    } else {
      target.cropped_diagram_path = null;
    }
    showToast({ message: '图片已删除', icon: 'success' });
    fetchMistakes();
  } catch (e) {
    showToast('删除失败，请重试');
  } finally {
    editBusy.value = false;
  }
};

/** 录入态：撤掉已上传的配图 */
const removeNewDiagram = () => {
  newMistake.value.cropped_diagram_path = null;
};

const submitEditMistake = async () => {
  if (!editingMistake.value) return;
  savingEdit.value = true;
  try {
    await mistakeApi.update(editingMistake.value.id, {
      subject_id: editingMistake.value.subject_id,
      source_reference: editingMistake.value.source_reference,
      error_type: editingMistake.value.error_type,
      extracted_text: editingMistake.value.extracted_text,
      answer: editingMistake.value.answer,
      mastery_status: editingMistake.value.mastery_status
    });
    showToast({ message: '错题已修改', icon: 'success' });
    showEditModal.value = false;
    fetchMistakes();
  } catch (e) {
    const msg = e.response?.data?.detail || '修改失败，请重试';
    showToast(msg);
  } finally {
    savingEdit.value = false;
  }
};

const newMistake = ref({
  subject_id: 1,
  source_reference: '',
  error_type: '概念模糊',
  extracted_text: '',
  answer: '',
  original_image_path: null,
  thumbnail_path: null,
  cropped_diagram_path: null,
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
    if (e.message && (e.message.includes('Network Error') || e.code === 'ERR_NETWORK')) {
      showToast('网络连接失败，请检查网络或系统代理');
    } else {
      showToast('获取错题列表失败');
    }
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

const handleUpload = (file) => {
  pendingUploadFile.value = file;
  cropperImageUrl.value = file.content || (file.file ? URL.createObjectURL(file.file) : '');
  cropperMode.value = 'question';
  editCropKind.value = null;
  showCropper.value = true;
};

/** 压缩 + 上传，返回后端图片三元组；失败抛错 */
const uploadImageFile = async (rawFile) => {
  const compressed = await compressImage(rawFile);
  const fd = new FormData();
  fd.append('file', compressed.file || rawFile);
  const res = await mistakeApi.uploadImage(fd);
  return res.data;
};

/** 上传题干图，落到 newMistake */
const uploadQuestionImage = async (rawFile, previewBlobUrl = null) => {
  try {
    showToast({ type: 'loading', message: '图片处理中...', forbidClick: true, duration: 0 });
    const data = await uploadImageFile(rawFile);
    newMistake.value.original_image_path = data.original_url;
    newMistake.value.thumbnail_path = data.thumbnail_url;
    newMistake.value.storage_key = data.storage_key;
    if (previewBlobUrl) {
      fileList.value = [{ url: previewBlobUrl }];
    }
    closeToast();
    return true;
  } catch (e) {
    closeToast();
    showToast('图片上传失败，请重试');
    return false;
  }
};

/** 上传题目配图（数轴/几何图），落到 newMistake.cropped_diagram_path */
const uploadDiagramImage = async (rawFile) => {
  try {
    showToast({ type: 'loading', message: '配图处理中...', forbidClick: true, duration: 0 });
    const data = await uploadImageFile(rawFile);
    newMistake.value.cropped_diagram_path = data.original_url;
    closeToast();
    showToast({ message: '配图已添加', icon: 'success' });
    return true;
  } catch (e) {
    closeToast();
    showToast('配图上传失败，请重试');
    return false;
  }
};

/** 用同一张原图二次框选，只保留图形区域 */
const openDiagramCropper = () => {
  const pending = pendingUploadFile.value;
  const url = pending?.content
    || (pending?.file ? URL.createObjectURL(pending.file) : '')
    || cropperImageUrl.value;
  if (!url) {
    showToast('请先拍照或上传题目图片');
    return;
  }
  cropperImageUrl.value = url;
  cropperMode.value = 'diagram';
  editCropKind.value = null;
  showCropper.value = true;
};

/** 题干图上传并识别完成后，问一句是否还要框图形 */
const askForDiagramAfterQuestion = async () => {
  if (newMistake.value.cropped_diagram_path) return;
  try {
    await showConfirmDialog({
      title: '题目里有图形吗？',
      message: '数轴、几何图这类图形没法被文字识别保留，可以再框一次单独存成配图，复习打印时会带上。',
      confirmButtonText: '框选图形',
      cancelButtonText: '没有图形'
    });
  } catch (e) {
    return;
  }
  openDiagramCropper();
};

const onCropConfirm = async (cropData) => {
  showCropper.value = false;
  if (!cropData?.file) return;

  // 编辑态换图：直接写回记录
  if (editCropKind.value) {
    const kind = editCropKind.value;
    editCropKind.value = null;
    cropperMode.value = 'question';
    await replaceEditImage(kind, cropData);
    return;
  }

  if (cropperMode.value === 'diagram') {
    await uploadDiagramImage(cropData.file);
    cropperMode.value = 'question';
    return;
  }

  const ok = await uploadQuestionImage(cropData.file, cropData.blobUrl);
  if (!ok) return;
  await extractText();
  await askForDiagramAfterQuestion();
};

const onCropSkip = async () => {
  showCropper.value = false;

  // 配图流程里「跳过」= 不添加配图，不影响已上传的题干图
  if (cropperMode.value === 'diagram') {
    cropperMode.value = 'question';
    return;
  }

  const pending = pendingUploadFile.value;
  if (!pending?.file) return;

  // 整张照片通常带批改痕迹与订正答案，先明确告知风险再决定
  try {
    await showConfirmDialog({
      title: '确认不裁剪？',
      message: '将直接使用整张照片，照片里的批改痕迹和订正答案会一并保存，并可能随复习卷打印出来。',
      confirmButtonText: '仍用整张',
      cancelButtonText: '返回裁剪'
    });
  } catch (e) {
    showCropper.value = true;
    return;
  }

  const ok = await uploadQuestionImage(
    pending.file,
    pending.content || URL.createObjectURL(pending.file)
  );
  if (ok) {
    await extractText();
    await askForDiagramAfterQuestion();
  }
};

const onCropCancel = () => {
  const wasDiagram = cropperMode.value === 'diagram' || Boolean(editCropKind.value);
  showCropper.value = false;
  cropperMode.value = 'question';
  editCropKind.value = null;
  // 放弃配图 / 放弃换图，不动已有图片
  if (wasDiagram) return;
  fileList.value = [];
  pendingUploadFile.value = null;
};

const finishOcr = (ok, message) => {
  if (pollTimerM) {
    clearInterval(pollTimerM);
    pollTimerM = null;
  }
  ocrLoading.value = false;
  closeToast();
  showToast({ message, icon: ok ? 'success' : 'warning-o', duration: ok ? 2000 : 2600 });
};

const extractText = async () => {
  if (ocrLoading.value) return false;
  if (!newMistake.value.storage_key) {
    showToast('请先上传错题图片');
    return false;
  }

  ocrLoading.value = true;
  showToast({ type: 'loading', message: '正在识别题干…', duration: 0 });
  try {
    const fd = new FormData();
    fd.append('image_path', newMistake.value.storage_key);
    fd.append('mode', 'auto');
    const res = await ocrApi.createTask(fd);
    const taskId = res.data.task_id;
    if (pollTimerM) clearInterval(pollTimerM);
    ocrPollCount = 0;

    return await new Promise((resolve) => {
      pollTimerM = setInterval(async () => {
        ocrPollCount += 1;
        if (ocrPollCount > OCR_MAX_POLLS) {
          finishOcr(false, '题干识别超时，请重试或手动输入');
          resolve(false);
          return;
        }
        try {
          const statusRes = await ocrApi.getTask(taskId);
          const status = statusRes.data.status;
          if (status === 'succeeded') {
            const text = statusRes.data.result?.text || '';
            const engine = statusRes.data.result?.engine || 'OCR';
            const cost = statusRes.data.result?.cost_ms;
            if (text.trim()) {
              newMistake.value.extracted_text = text;
              const costText = cost ? ` · ${(cost / 1000).toFixed(1)}s` : '';
              finishOcr(true, `题干识别成功（${engine}${costText}）`);
              resolve(true);
            } else {
              finishOcr(false, '未识别到文字，可重新框选或手动输入');
              resolve(false);
            }
          } else if (status === 'failed') {
            const detail = statusRes.data.error || '';
            finishOcr(false, detail ? `题干提取失败：${String(detail).slice(0, 40)}` : '题干提取失败，请手动输入');
            resolve(false);
          }
        } catch (err) {
          finishOcr(false, '识别轮询异常，请重试');
          resolve(false);
        }
      }, 500);
    });
  } catch (e) {
    finishOcr(false, '发起识别任务失败');
    return false;
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
      answer: newMistake.value.answer,
      original_image_path: newMistake.value.original_image_path,
      thumbnail_path: newMistake.value.thumbnail_path,
      cropped_diagram_path: newMistake.value.cropped_diagram_path
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
  pendingUploadFile.value = null;
  cropperMode.value = 'question';
  editCropKind.value = null;
  if (pollTimerM) {
    clearInterval(pollTimerM);
    pollTimerM = null;
  }
  ocrLoading.value = false;
  closeToast();
  newMistake.value = {
    subject_id: subjects.value.length > 0 ? subjects.value[0].id : 1,
    source_reference: '',
    error_type: '概念模糊',
    extracted_text: '',
    answer: '',
    original_image_path: null,
    thumbnail_path: null,
    cropped_diagram_path: null,
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

onBeforeUnmount(() => {
  if (pollTimerM) {
    clearInterval(pollTimerM);
    pollTimerM = null;
  }
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
  font-size: var(--st-font-lg);
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
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
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
  font-size: var(--st-font-xs);
  padding: 2px 8px;
  border-radius: var(--st-radius-full, 9999px);
  backdrop-filter: blur(4px);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* 题目配图（数轴/几何图），打印与复习专用 */
.card-diagram-box {
  position: relative;
  width: 100%;
  max-height: 140px;
  border-radius: var(--st-radius-md, 10px);
  overflow: hidden;
  cursor: pointer;
  background: var(--st-bg-subtle, #f1f5f9);
  border: 1px dashed var(--st-border, #e2e8f0);
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 8px;
}

.card-diagram-box img {
  width: 100%;
  max-height: 140px;
  object-fit: contain;
}

/* 录入/编辑抽屉里的配图选择区 */
.diagram-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.diagram-thumb {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  gap: 6px;
}

.diagram-thumb img {
  max-width: 160px;
  max-height: 120px;
  border-radius: var(--st-radius-md, 10px);
  border: 1px solid var(--st-border, #e2e8f0);
  object-fit: contain;
  background: var(--st-bg-subtle, #f1f5f9);
  cursor: pointer;
}

.diagram-thumb-actions {
  display: flex;
  gap: 6px;
}

.mini-btn {
  border: 1px solid var(--st-border, #e2e8f0);
  background: var(--st-bg-subtle, #f8fafc);
  color: var(--st-text-primary);
  font-size: var(--st-font-xs);
  padding: 3px 12px;
  border-radius: var(--st-radius-full, 9999px);
  cursor: pointer;
}

.mini-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.mini-btn--danger {
  color: var(--st-danger, #dc2626);
  border-color: var(--st-danger, #dc2626);
  background: transparent;
}

.diagram-add-btn {
  align-self: flex-start;
}

/* 编辑抽屉的图片管理区块 */
.edit-image-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--st-radius-md, 10px);
  background: var(--st-bg-subtle, #f8fafc);
  border: 1px solid var(--st-border, #f1f5f9);
}

.edit-image-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.edit-image-body {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.edit-image-label {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  white-space: nowrap;
}

.edit-image-empty {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
}

.edit-image-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.question-text {
  font-size: var(--st-font-md);
  color: var(--st-text-primary);
  line-height: var(--st-leading-normal);
  margin: 0 0 6px 0;
}

.tags-row {
  display: flex;
  gap: 6px;
}

.error-tag {
  background: var(--st-warning-light, #fffbeb);
  color: var(--st-warning-dark, #d97706);
  font-size: var(--st-font-xs);
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
  font-size: var(--st-font-xs);
}

.review-round-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--st-text-secondary);
}

.next-date-tag {
  font-size: var(--st-font-xs);
  color: var(--st-purple, #7c3aed);
  background: var(--st-purple-light, #f5f3ff);
  padding: 2px 6px;
  border-radius: var(--st-radius-sm, 4px);
  font-weight: 500;
}

.review-buttons-row {
  display: flex;
  gap: 6px;
}

.rev-action-btn {
  flex: 1;
  font-weight: 600;
  font-size: var(--st-font-xs);
  padding: 0 4px;
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

.mistake-bottom-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.action-btn-primary {
  flex: 1.5;
  height: 42px;
  font-size: var(--st-font-md);
  font-weight: 600;
  border-radius: var(--st-radius-full, 9999px);
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
  white-space: nowrap;
}

.action-btn-secondary {
  flex: 0.95;
  height: 42px;
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: #334155;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: var(--st-radius-full, 9999px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
  white-space: nowrap;
  padding: 0 6px;
}

.action-btn-secondary:active {
  background-color: #f1f5f9;
}

.action-btn-paper {
  flex: 0.72;
  padding: 0 8px;
  color: #2563eb;
  background-color: #eff6ff;
  border-color: rgba(37, 99, 235, 0.3);
}

.action-btn-paper:active {
  background-color: #dbeafe;
}

.action-btn-danger {
  flex: 1.35;
  background-color: var(--st-danger, #ef4444) !important;
  border-color: var(--st-danger, #ef4444) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.25) !important;
}

.action-btn-danger:active {
  background-color: var(--st-danger-dark, #dc2626) !important;
}

.action-btn-danger:disabled,
.action-btn-danger.van-button--disabled {
  background-color: #fca5a5 !important;
  border-color: #fca5a5 !important;
  color: #ffffff !important;
  box-shadow: none !important;
  opacity: 0.65 !important;
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
  font-size: var(--st-font-xl);
  color: var(--st-text-muted);
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
  font-size: var(--st-font-xs);
  font-weight: 500;
  cursor: pointer;
}

.swipe-action-btn.btn-edit {
  background-color: var(--st-primary, #2563eb);
}

.swipe-action-btn.btn-delete {
  background-color: var(--st-danger, #ef4444);
}

/* 答案展示面板与轻量胶囊样式 */
.card-answer-panel {
  margin-top: 10px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: var(--st-radius-md, 8px);
  border: 1px dashed #cbd5e1;
  border-left: 3px solid var(--st-primary, #2563eb);
}

.answer-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.answer-title {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: var(--st-text-primary);
}

.answer-body {
  font-size: var(--st-font-sm);
  color: #334155;
  line-height: var(--st-leading-normal);
}

.answer-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.btn-answer {
  background-color: #f8fafc !important;
  color: var(--st-primary, #2563eb) !important;
  border-color: #bfdbfe !important;
}

.mastered-answer-bar {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.toggle-answer-pill {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: var(--st-primary, #2563eb);
  font-size: var(--st-font-xs);
  font-weight: 500;
  padding: 3px 10px;
  border-radius: var(--st-radius-full, 9999px);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.toggle-answer-pill:active {
  background: #e2e8f0;
}

.batch-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.batch-left-info {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
}

.batch-left-info b {
  color: var(--st-primary, #2563eb);
  font-size: var(--st-font-lg);
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
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-regular);
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

.upload-hint {
  margin: 6px 0 0;
  font-size: var(--st-font-xs);
  line-height: var(--st-leading-normal);
  color: var(--st-text-muted);
}

.modal-footer-btns {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}
</style>

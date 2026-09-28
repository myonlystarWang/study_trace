<template>
  <van-popup
    :show="modelValue"
    position="bottom"
    round
    class="bottom-sheet-modal hw-print-select-popup"
    :style="{ maxHeight: '85%' }"
    @update:show="$emit('update:modelValue', $event)"
  >
    <div class="print-select-container">
      <div class="sheet-grabber"></div>

      <!-- 弹窗顶栏 -->
      <div class="print-select-header">
        <div class="header-title-box">
          <span class="st-icon-badge st-icon-badge--primary">
            <van-icon name="printer" />
          </span>
          <span class="section-title">打印作业清单</span>
        </div>
        <button class="sheet-close-btn" @click="close" aria-label="关闭">
          <van-icon name="cross" size="18" />
        </button>
      </div>

      <!-- 模式选择分段控件：打印单日 vs 多日合并 -->
      <div class="print-mode-tabs">
        <button
          type="button"
          class="mode-tab-btn"
          :class="{ active: mode === 'single' }"
          @click="mode = 'single'"
        >
          <van-icon name="notes-o" size="14" />
          <span>打印单日清单</span>
        </button>
        <button
          type="button"
          class="mode-tab-btn"
          :class="{ active: mode === 'range' }"
          @click="mode = 'range'"
        >
          <van-icon name="calendar-o" size="14" />
          <span>合并多日 / 假期打印</span>
        </button>
      </div>

      <div class="print-select-body">
        <!-- 模式 1：单日模式 -->
        <div v-if="mode === 'single'" class="single-mode-box">
          <div class="field-label-row">
            <span class="field-label">打印日期</span>
            <button type="button" class="field-action-link" @click="singleDate = todayStr">设为今天</button>
          </div>
          <div class="date-input-wrap">
            <van-icon name="calendar-o" class="date-input-icon" />
            <input
              type="date"
              v-model="singleDate"
              class="st-date-picker-input"
            />
          </div>
          <p class="mode-tip-text">
            将打印所选日期的全部作业条目，若该日为周末或法定假期，将自动包含放假前顺延大作业。
          </p>
        </div>

        <!-- 模式 2：多日/假期合并模式 -->
        <div v-else class="range-mode-box">
          <!-- 假期智能推荐胶囊卡 -->
          <div v-if="breakSuggestion" class="holiday-suggest-card" @click="applyBreakSuggestion">
            <div class="suggest-badge">
              <van-icon name="flag-o" />
              <span>{{ breakSuggestion.isCurrent ? '当前正值' : '即将放假' }}</span>
            </div>
            <div class="suggest-info">
              <span class="suggest-name">{{ breakSuggestion.name }}</span>
              <span class="suggest-date">{{ breakSuggestion.start }} 至 {{ breakSuggestion.end }} (共 {{ breakSuggestion.days }} 天)</span>
            </div>
            <button type="button" class="suggest-apply-btn">一键填入</button>
          </div>

          <!-- 快捷时间跨度选择 -->
          <div class="quick-presets-row">
            <span class="presets-label">快捷选择：</span>
            <div class="presets-list">
              <button
                v-if="breakSuggestion"
                type="button"
                class="st-chip"
                @click="applyBreakSuggestion"
              >
                {{ breakSuggestion.name }}
              </button>
              <button type="button" class="st-chip" @click="applyPreset(3)">最近3天</button>
              <button type="button" class="st-chip" @click="applyPreset(7)">最近7天</button>
              <button type="button" class="st-chip" @click="applyThisWeek">本周</button>
            </div>
          </div>

          <!-- 起止日期选择 -->
          <div class="range-inputs-grid">
            <div class="range-field">
              <span class="field-label">开始日期</span>
              <div class="date-input-wrap">
                <van-icon name="calendar-o" class="date-input-icon" />
                <input
                  type="date"
                  v-model="startDate"
                  class="st-date-picker-input"
                />
              </div>
            </div>
            <div class="range-sep">至</div>
            <div class="range-field">
              <span class="field-label">截止日期</span>
              <div class="date-input-wrap">
                <van-icon name="calendar-o" class="date-input-icon" />
                <input
                  type="date"
                  v-model="endDate"
                  class="st-date-picker-input"
                />
              </div>
            </div>
          </div>
          <p class="mode-tip-text">
            将汇总选定日期范围内的所有作业，长假期作业将自动纳入合并。
          </p>
        </div>

        <!-- 选项：仅打印待办 -->
        <div class="print-option-row">
          <label class="option-checkbox-label">
            <input
              type="checkbox"
              v-model="onlyUncompleted"
              class="st-native-checkbox"
            />
            <span class="option-text">仅打印待办作业（已完成的作业不纳入打印清单）</span>
          </label>
        </div>
      </div>

      <!-- 底部确认操作按钮 -->
      <div class="print-select-footer">
        <button type="button" class="btn-cancel" @click="close">取消</button>
        <button type="button" class="btn-confirm" @click="confirmPrint">
          <van-icon name="printer" />
          <span>进入打印预览</span>
        </button>
      </div>
    </div>
  </van-popup>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { homeworkApi } from '../api';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  currentDate: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue']);
const router = useRouter();

const pad = (n) => String(n).padStart(2, '0');
const toDateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

const todayStr = toDateStr(new Date());
const mode = ref('single'); // 'single' | 'range'
const singleDate = ref(props.currentDate || todayStr);
const startDate = ref(todayStr);
const endDate = ref(todayStr);
const onlyUncompleted = ref(false);
const breakSuggestion = ref(null);

watch(
  () => props.currentDate,
  (val) => {
    if (val) {
      singleDate.value = val;
    }
  }
);

watch(
  () => props.modelValue,
  (show) => {
    if (show) {
      checkHolidayInfo();
    }
  }
);

// 探测当前或近期节假日连休信息
const checkHolidayInfo = async () => {
  try {
    const targetDate = singleDate.value || todayStr;
    const res = await homeworkApi.getHolidayInfo(targetDate);
    const data = res.data;
    if (data.current_break) {
      breakSuggestion.value = {
        name: data.current_break.display_name,
        start: data.current_break.span_start,
        end: data.current_break.span_end,
        days: data.current_break.days,
        isCurrent: true
      };
      // 如果当前正处于假期，默认自动为范围模式预选该假期
      startDate.value = data.current_break.span_start;
      endDate.value = data.current_break.span_end;
    } else if (data.upcoming_break) {
      breakSuggestion.value = {
        name: data.upcoming_break.display_name,
        start: data.upcoming_break.span_start,
        end: data.upcoming_break.span_end,
        days: data.upcoming_break.days,
        isCurrent: false
      };
    } else {
      breakSuggestion.value = null;
    }
  } catch (err) {
    // 容错不阻断
    breakSuggestion.value = null;
  }
};

const applyBreakSuggestion = () => {
  if (!breakSuggestion.value) return;
  mode.value = 'range';
  startDate.value = breakSuggestion.value.start;
  endDate.value = breakSuggestion.value.end;
  showToast({ message: `已选定${breakSuggestion.value.name}`, icon: 'passed', duration: 1000 });
};

const applyPreset = (days) => {
  const d = new Date();
  const start = new Date(d);
  start.setDate(d.getDate() - (days - 1));
  startDate.value = toDateStr(start);
  endDate.value = toDateStr(d);
};

const applyThisWeek = () => {
  const curr = new Date();
  const dayOfWeek = curr.getDay(); // 0 是周日
  const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(curr);
  monday.setDate(curr.getDate() + diffToMonday);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  startDate.value = toDateStr(monday);
  endDate.value = toDateStr(sunday);
};

const close = () => {
  emit('update:modelValue', false);
};

const confirmPrint = () => {
  close();
  if (mode.value === 'single') {
    const q = { date: singleDate.value };
    if (onlyUncompleted.value) q.only_uncompleted = '1';
    router.push({ path: '/homework/print', query: q });
  } else {
    let s = startDate.value;
    let e = endDate.value;
    if (s > e) {
      const temp = s;
      s = e;
      e = temp;
    }
    const q = {
      start_date: s,
      end_date: e
    };
    if (onlyUncompleted.value) q.only_uncompleted = '1';
    router.push({ path: '/homework/print', query: q });
  }
};

onMounted(() => {
  checkHolidayInfo();
});
</script>

<style scoped>
.hw-print-select-popup {
  background: var(--st-bg-card, #ffffff);
  border-top-left-radius: var(--st-radius-xl, 16px);
  border-top-right-radius: var(--st-radius-xl, 16px);
}

.print-select-container {
  display: flex;
  flex-direction: column;
  padding: 12px 18px 24px;
}

.sheet-grabber {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--st-border, #e2e8f0);
  margin: 0 auto 12px;
}

.print-select-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.header-title-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title {
  font-size: var(--st-font-lg, 17px);
  font-weight: 700;
  color: var(--st-text-primary, #0f172a);
}

.sheet-close-btn {
  background: transparent;
  border: none;
  color: var(--st-text-secondary, #64748b);
  cursor: pointer;
  padding: 4px;
}

/* 分段切换按钮 */
.print-mode-tabs {
  display: flex;
  background: var(--st-bg-subtle, #f1f5f9);
  border-radius: var(--st-radius-md, 8px);
  padding: 3px;
  gap: 4px;
  margin-bottom: 16px;
}

.mode-tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: var(--st-font-sm, 14px);
  font-weight: 500;
  color: var(--st-text-secondary, #64748b);
  cursor: pointer;
  transition: all 0.15s ease;
}

.mode-tab-btn.active {
  background: #ffffff;
  color: var(--st-primary, #2563eb);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.print-select-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.field-label {
  font-size: var(--st-font-xs, 12px);
  font-weight: 600;
  color: var(--st-text-secondary, #64748b);
}

.field-action-link {
  background: transparent;
  border: none;
  font-size: var(--st-font-xs, 12px);
  font-weight: 500;
  color: var(--st-primary, #2563eb);
  cursor: pointer;
}

.date-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--st-bg-card, #ffffff);
  border: 1px solid var(--st-border, #e2e8f0);
  border-radius: var(--st-radius-md, 8px);
}

.date-input-icon {
  color: var(--st-text-muted, #94a3b8);
  font-size: 16px;
}

.st-date-picker-input {
  border: none;
  background: transparent;
  font-size: var(--st-font-sm, 14px);
  font-weight: 500;
  color: var(--st-text-primary, #0f172a);
  width: 100%;
  outline: none;
}

.mode-tip-text {
  font-size: var(--st-font-xs, 12px);
  color: var(--st-text-muted, #94a3b8);
  margin-top: 6px;
  line-height: 1.4;
}

/* 假期智能推荐胶囊卡 */
.holiday-suggest-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(59, 130, 246, 0.04));
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: var(--st-radius-lg, 12px);
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.holiday-suggest-card:active {
  background: rgba(37, 99, 235, 0.12);
}

.suggest-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--st-primary, #2563eb);
  background: #ffffff;
  padding: 2px 6px;
  border-radius: 4px;
}

.suggest-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 10px;
}

.suggest-name {
  font-size: var(--st-font-sm, 13px);
  font-weight: 700;
  color: var(--st-text-primary, #0f172a);
}

.suggest-date {
  font-size: 11px;
  color: var(--st-text-secondary, #64748b);
  margin-top: 1px;
}

.suggest-apply-btn {
  border: none;
  background: var(--st-primary, #2563eb);
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
}

/* 快捷选择 */
.quick-presets-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.presets-label {
  font-size: var(--st-font-xs, 12px);
  color: var(--st-text-secondary, #64748b);
  flex-shrink: 0;
}

.presets-list {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}

.presets-list::-webkit-scrollbar {
  display: none;
}

.presets-list .st-chip {
  padding: 3px 9px;
  font-size: 12px;
}

/* 起止日期栅格 */
.range-inputs-grid {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.range-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.range-sep {
  font-size: var(--st-font-xs, 12px);
  font-weight: 600;
  color: var(--st-text-secondary, #64748b);
  margin-top: 16px;
}

/* 选项勾选 */
.print-option-row {
  padding: 8px 0;
  border-top: 1px solid var(--st-border, #e2e8f0);
}

.option-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.st-native-checkbox {
  width: 16px;
  height: 16px;
  accent-color: var(--st-primary, #2563eb);
  cursor: pointer;
}

.option-text {
  font-size: var(--st-font-xs, 12px);
  color: var(--st-text-regular, #334155);
}

/* 底部按钮 */
.print-select-footer {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-cancel {
  flex: 1;
  border: 1px solid var(--st-border, #e2e8f0);
  background: var(--st-bg-card, #ffffff);
  color: var(--st-text-regular, #334155);
  font-size: var(--st-font-md, 15px);
  font-weight: 600;
  padding: 10px 0;
  border-radius: var(--st-radius-md, 8px);
  cursor: pointer;
}

.btn-confirm {
  flex: 2;
  border: none;
  background: var(--st-primary, #2563eb);
  color: #ffffff;
  font-size: var(--st-font-md, 15px);
  font-weight: 600;
  padding: 10px 0;
  border-radius: var(--st-radius-md, 8px);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
}
</style>

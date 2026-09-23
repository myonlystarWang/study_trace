<template>
  <div class="st-subject-badge-wrapper" :class="{ 'with-label': showName }">
    <div
      class="st-subject-badge"
      :class="[badgeClass, size ? `st-subject-badge--${size}` : '']"
    >
      <!-- 数学: 尺规几何 / ∑ -->
      <svg v-if="normalizedSubject === 'math'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 19 L12 4 L20 19 Z" />
        <path d="M8 14 L16 14" />
      </svg>

      <!-- 语文: 展开书卷 -->
      <svg v-else-if="normalizedSubject === 'chinese'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        <line x1="8" y1="7" x2="16" y2="7" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </svg>

      <!-- 英语: 对话气泡 + 字母，避免与语文的书本轮廓混淆。 -->
      <svg v-else-if="normalizedSubject === 'english'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">
        <path d="M5 4h14v11H10l-5 4V4z" />
        <path d="M9 11l2-4 2 4M10 9.5h2" />
      </svg>

      <!-- 物理: 灯泡与能量 -->
      <svg v-else-if="normalizedSubject === 'physics'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 18h6" />
        <path d="M10 22h4" />
        <path d="M12 2a7 7 0 0 0-7 7c0 2.6 1.4 4.8 3.5 6h7c2.1-1.2 3.5-3.4 3.5-6a7 7 0 0 0-7-7z" />
      </svg>

      <!-- 化学: 实验锥形瓶 -->
      <svg v-else-if="normalizedSubject === 'chemistry'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10 2v5L4 18a2 2 0 0 0 1.7 3h12.6a2 2 0 0 0 1.7-3L14 7V2" />
        <line x1="8.5" y1="2" x2="15.5" y2="2" />
        <line x1="7" y1="15" x2="17" y2="15" />
      </svg>

      <!-- 生物: 萌芽幼叶 -->
      <svg v-else-if="normalizedSubject === 'biology'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22v-9" />
        <path d="M12 13a6 6 0 0 1 6-6c0 4-2 7-6 7" />
        <path d="M12 13a6 6 0 0 0-6-6c0 4 2 7 6 7" />
      </svg>

      <!-- 地理: 经纬地球仪 -->
      <svg v-else-if="normalizedSubject === 'geography'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>

      <!-- 历史: 沙漏时光 -->
      <svg v-else-if="normalizedSubject === 'history'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M5 22h14" />
        <path d="M5 2h14" />
        <path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22" />
        <path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2" />
      </svg>

      <!-- 道德与法治: 盾牌天平 -->
      <svg v-else-if="normalizedSubject === 'daofa' || normalizedSubject === 'politics'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>

      <!-- 兜底: 提取单字 -->
      <span v-else class="badge-text-fallback">{{ displayFallbackChar }}</span>
    </div>

    <!-- 可选带标签 -->
    <span v-if="showName" class="badge-subject-label">{{ name }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  name: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'md' // 'sm' | 'md' | 'lg'
  },
  showName: {
    type: Boolean,
    default: false
  }
});

const normalizedSubject = computed(() => {
  const n = (props.name || '').trim();
  if (n.includes('数')) return 'math';
  // “英语”包含“语”，必须先判断英语，否则会误落到语文图标。
  if (n.includes('英')) return 'english';
  if (n.includes('语')) return 'chinese';
  if (n.includes('物')) return 'physics';
  if (n.includes('化')) return 'chemistry';
  if (n.includes('生')) return 'biology';
  if (n.includes('地')) return 'geography';
  if (n.includes('历')) return 'history';
  if (n.includes('道') || n.includes('法') || n.includes('政')) return 'daofa';
  return 'neutral';
});

const badgeClass = computed(() => {
  return `st-subject-badge--${normalizedSubject.value}`;
});

const displayFallbackChar = computed(() => {
  return props.name ? props.name.charAt(0) : '课';
});
</script>

<style scoped>
.st-subject-badge-wrapper {
  display: inline-flex;
  align-items: center;
}

.st-subject-badge-wrapper.with-label {
  gap: 8px;
}

.badge-icon {
  width: 58%;
  height: 58%;
}

.badge-text-fallback {
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
}

.badge-subject-label {
  font-size: var(--st-font-md, 14px);
  font-weight: 600;
  color: var(--st-text-primary, #0f172a);
}
</style>

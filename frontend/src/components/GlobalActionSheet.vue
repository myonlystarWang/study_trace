<template>
  <div v-if="visible" class="action-sheet-layer" @click.self="close">
    <section class="action-sheet" role="dialog" aria-modal="true" aria-label="快速操作">
      <div class="action-sheet-handle" />
      <header class="action-sheet-header">
        <div>
          <p class="action-sheet-eyebrow">快速操作</p>
          <h2>{{ heading }}</h2>
        </div>
        <button class="action-sheet-close" type="button" aria-label="关闭" @click="close">
          <van-icon name="cross" />
        </button>
      </header>
      <div class="action-grid">
        <button v-for="action in actions" :key="action.key" type="button" class="action-item" @click="choose(action.key)">
          <span class="action-icon" :class="`action-icon--${action.tone}`"><van-icon :name="action.icon" /></span>
          <span>{{ action.label }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  visible: Boolean,
  routeName: { type: String, default: '' }
});
const emit = defineEmits(['update:visible', 'select']);

const heading = computed(() => ({
  today: '把时间留给重要的事',
  homework: '管理今天的作业',
  mistakes: '整理与复习错题',
  scores: '记录一次新的成长',
}[props.routeName] || '选择要做的事'));

const actions = [
  { key: 'homework', label: '录入作业', icon: 'todo-list-o', tone: 'blue' },
  { key: 'mistake', label: '录入错题', icon: 'records-o', tone: 'purple' },
  { key: 'score', label: '录入成绩', icon: 'chart-trending-o', tone: 'orange' },
  { key: 'focus', label: '开始专注', icon: 'underway-o', tone: 'green' },
  { key: 'paper', label: '智能组卷', icon: 'description', tone: 'gray' }
];

const close = () => emit('update:visible', false);
const choose = (key) => {
  emit('select', key);
  close();
};
</script>

<style scoped>
.action-sheet-layer { position: fixed; inset: 0; z-index: 100; display: flex; align-items: flex-end; background: rgba(15, 23, 42, .24); backdrop-filter: blur(4px); }
.action-sheet { width: min(100%, 500px); margin: 0 auto; padding: var(--st-space-3) var(--st-space-5) calc(var(--st-space-6) + env(safe-area-inset-bottom, 0px)); border-radius: var(--st-radius-xl) var(--st-radius-xl) 0 0; background: var(--st-bg-card); box-shadow: var(--st-shadow-float); }
.action-sheet-handle { width: 36px; height: 4px; margin: var(--st-space-1) auto var(--st-space-5); border-radius: var(--st-radius-full); background: var(--st-border-bold); }
.action-sheet-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--st-space-5); }
.action-sheet-eyebrow { margin: 0 0 var(--st-space-1); color: var(--st-text-secondary); font-size: var(--st-font-sm); }
.action-sheet-header h2 { margin: 0; color: var(--st-text-primary); font-size: var(--st-font-xl); line-height: var(--st-leading-tight); font-weight: 700; }
.action-sheet-close { width: 44px; height: 44px; border: 0; border-radius: var(--st-radius-full); background: var(--st-bg-subtle); color: var(--st-text-secondary); font-size: var(--st-font-xl); }
.action-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--st-space-3); }
.action-item { min-height: 88px; padding: var(--st-space-4) var(--st-space-2); border: 1px solid var(--st-border); border-radius: var(--st-radius-lg); background: var(--st-bg-subtle); color: var(--st-text-regular); font-size: var(--st-font-sm); font-weight: 600; }
.action-icon { display: grid; width: 38px; height: 38px; margin: 0 auto var(--st-space-2); place-items: center; border-radius: var(--st-radius-md); font-size: var(--st-font-xl); }
.action-icon--blue { color: var(--st-primary); background: var(--st-primary-light); }.action-icon--purple { color: var(--st-purple); background: var(--st-purple-light); }.action-icon--orange { color: var(--st-warning-dark); background: var(--st-warning-light); }.action-icon--green { color: var(--st-success-dark); background: var(--st-success-light); }.action-icon--gray { color: var(--st-neutral); background: var(--st-neutral-light); }
.action-item:active, .action-sheet-close:active { transform: scale(.97); }
@media (max-width: 340px) { .action-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>

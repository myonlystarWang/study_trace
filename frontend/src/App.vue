<template>
  <div class="app-container" :class="{ 'app-container--wide': $route.meta?.paperMode }">
    <router-view />

    <div v-if="showGlobalAdd" class="global-add-anchor">
      <button class="global-add-button" type="button" aria-label="快速操作" @click="showActions = true">
        <van-icon name="plus" size="22" />
      </button>
    </div>
    <GlobalActionSheet v-model:visible="showActions" :route-name="$route.name" @select="handleAction" />

    <!-- 底部导航栏：首页、作业、错题、数据、我的 -->
    <van-tabbar
      v-show="!$route.meta?.hideTabbar"
      :placeholder="!$route.meta?.hideTabbar"
      route
      active-color="var(--st-primary)"
      inactive-color="var(--st-text-muted)"
    >
      <van-tabbar-item to="/" icon="wap-home-o">今天</van-tabbar-item>
      <van-tabbar-item to="/homework" icon="todo-list-o">作业</van-tabbar-item>
      <van-tabbar-item to="/mistakes" icon="records-o">复习</van-tabbar-item>
      <van-tabbar-item to="/scores" icon="chart-trending-o">成长</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="contact-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>


<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import GlobalActionSheet from './components/GlobalActionSheet.vue';

const router = useRouter();
const route = useRoute();
const showActions = ref(false);
let visualViewport = null;

const syncKeyboardInset = () => {
  if (!visualViewport) return;
  const inset = Math.max(0, window.innerHeight - visualViewport.height - visualViewport.offsetTop);
  document.documentElement.style.setProperty('--st-keyboard-inset', `${inset}px`);
};

onMounted(() => {
  visualViewport = window.visualViewport;
  if (!visualViewport) return;
  syncKeyboardInset();
  visualViewport.addEventListener('resize', syncKeyboardInset);
  visualViewport.addEventListener('scroll', syncKeyboardInset);
});

onUnmounted(() => {
  if (visualViewport) {
    visualViewport.removeEventListener('resize', syncKeyboardInset);
    visualViewport.removeEventListener('scroll', syncKeyboardInset);
  }
  document.documentElement.style.setProperty('--st-keyboard-inset', '0px');
});
// 单题复习是一个明确的专注场景，悬浮录入入口会抢占底部的主操作。
// 错题总库与其他页面仍保留全局快速操作。
const showGlobalAdd = computed(() =>
  !route.meta?.hideTabbar && !(route.name === 'mistakes' && route.query.tab !== 'all')
);

const handleAction = async (action) => {
  const targets = {
    homework: '/homework?action=add',
    mistake: '/mistakes?action=add',
    score: '/scores?action=add',
    focus: '/?action=focus',
    paper: '/paper'
  };
  await router.push(targets[action]);
  window.dispatchEvent(new CustomEvent('zhixueji:action', { detail: action }));
};
</script>

<style>
/* 令牌由 main.js 统一引入（design-tokens.css），此处不再重复 @import，
   避免同一份变量定义出现在两处造成漂移。 */

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  -webkit-tap-highlight-color: transparent;
}

body {
  font-family: var(--st-font-family);
  /* 全站基准字号：14px（与 Vant --van-font-size-md 同源）。
     这是"裸放的 Vant 控件继承 16px"问题的根治点 —— 见 design-tokens.css 第 7 节注释。 */
  font-size: var(--st-font-md, 14px);
  line-height: var(--st-leading-normal, 1.5);
  background-color: var(--st-bg-page);
  color: var(--st-text-primary);
  min-height: 100vh;
  min-height: 100dvh;
}

.app-container {
  max-width: 390px;
  margin: 0 auto;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: var(--st-bg-page);
  box-shadow: 0 0 30px rgba(15, 23, 42, 0.08);
}

/* 底部 TabBar：磨砂毛玻璃背景 + 顶部细分割线 + 品牌蓝激活 */
.app-container .van-tabbar {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: saturate(180%) blur(14px);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
  border-top: 1px solid rgba(15, 23, 42, 0.06);
  box-shadow: 0 -1px 0 rgba(15, 23, 42, 0.03);
}

.global-add-anchor { position: fixed; left: 0; right: 0; bottom: calc(54px + env(safe-area-inset-bottom, 0px)); z-index: 48; display: flex; justify-content: flex-end; width: min(100%, 390px); margin: 0 auto; padding: 0 var(--st-space-5); pointer-events: none; }
.global-add-button { display: grid; width: 48px; height: 48px; place-items: center; border: 0; border-radius: var(--st-radius-full); background: var(--st-primary); color: #fff; box-shadow: var(--st-shadow-float); pointer-events: auto; }
.global-add-button:active { transform: scale(.94); background: var(--st-primary-dark); }
@media (min-width: 600px) { .app-container { border-left: 1px solid var(--st-border); border-right: 1px solid var(--st-border); } }
</style>

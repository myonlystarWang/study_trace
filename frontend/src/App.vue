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
import { consumeActionQuery } from './utils/routeAction';

const router = useRouter();
const route = useRoute();
const showActions = ref(false);
let visualViewport = null;
let lastInset = -1;
let insetRaf = 0;

const applyKeyboardInset = () => {
  if (!visualViewport) return;
  const raw = window.innerHeight - visualViewport.height - visualViewport.offsetTop;
  const inset = Math.max(0, Math.round(raw));
  // 键盘动画期间 scroll/resize 会高频触发，变化小于 2px 时不动 DOM，避免弹层来回抖。
  if (Math.abs(inset - lastInset) < 2) return;
  lastInset = inset;
  document.documentElement.style.setProperty('--st-keyboard-inset', `${inset}px`);
  // 键盘高度落定后弹层才真正缩高（还带 0.15s 过渡），前后各校正一次，别等 focusin 的定时器轮空。
  [80, 260].forEach((ms) => window.setTimeout(ensureActiveElementVisible, ms));
};

const syncKeyboardInset = () => {
  if (insetRaf) return;
  insetRaf = requestAnimationFrame(() => {
    insetRaf = 0;
    applyKeyboardInset();
  });
};

/**
 * 焦点元素是否被软键盘/滚动容器挡住，挡住就滚回来。
 * 安卓 Chrome 键盘弹起时布局视口不变（fixed 弹层仍按整屏算），
 * 弹层内的输入框很容易落在键盘下方，浏览器自己不会帮忙滚。
 */
const FOCUSABLE_TAGS = /^(INPUT|TEXTAREA|SELECT)$/;

const findScrollableAncestor = (el) => {
  let node = el.parentElement;
  while (node && node !== document.body && node !== document.documentElement) {
    const style = getComputedStyle(node);
    if (/(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 1) {
      return node;
    }
    node = node.parentElement;
  }
  return null;
};

const ensureActiveElementVisible = () => {
  const el = document.activeElement;
  if (!el || !FOCUSABLE_TAGS.test(el.tagName)) return;
  if (el.getBoundingClientRect().height === 0) return; // 已随弹层关闭而隐藏

  const vv = window.visualViewport;
  const viewTop = vv ? vv.offsetTop : 0;
  const viewBottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
  const scroller = findScrollableAncestor(el);
  const scrollerRect = scroller ? scroller.getBoundingClientRect() : null;

  const topLimit = Math.max(viewTop, scrollerRect ? scrollerRect.top : 0);
  const bottomLimit = Math.min(viewBottom, scrollerRect ? scrollerRect.bottom : viewBottom);
  const margin = 20;
  const rect = el.getBoundingClientRect();

  let delta = 0;
  if (rect.bottom > bottomLimit - margin) delta = rect.bottom - (bottomLimit - margin);
  else if (rect.top < topLimit + margin) delta = rect.top - (topLimit + margin);
  if (!delta) return;

  const target = scroller || window;
  if (target.scrollBy) target.scrollBy({ top: delta, behavior: 'smooth' });
};

const onFocusIn = (event) => {
  const el = event.target;
  if (!el || !FOCUSABLE_TAGS.test(el.tagName)) return;
  // 键盘弹起动画 + 弹层 max-height 收缩需要时间，分三次校正，谁生效算谁的。
  [120, 320, 560].forEach((ms) => window.setTimeout(ensureActiveElementVisible, ms));
};

onMounted(() => {
  visualViewport = window.visualViewport;
  document.addEventListener('focusin', onFocusIn);
  if (!visualViewport) return;
  syncKeyboardInset();
  visualViewport.addEventListener('resize', syncKeyboardInset);
  visualViewport.addEventListener('scroll', syncKeyboardInset);
});

onUnmounted(() => {
  document.removeEventListener('focusin', onFocusIn);
  if (insetRaf) cancelAnimationFrame(insetRaf);
  if (visualViewport) {
    visualViewport.removeEventListener('resize', syncKeyboardInset);
    visualViewport.removeEventListener('scroll', syncKeyboardInset);
  }
  document.documentElement.style.setProperty('--st-keyboard-inset', '0px');
});
// 错题页自带「+ 录入」入口（导航栏右上角），不再叠加全局悬浮 + ，
// 避免同一屏出现两个录入按钮、也避免压住复习的主操作。
const showGlobalAdd = computed(() =>
  !route.meta?.hideTabbar && route.name !== 'mistakes'
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
  // 动作已经下发给页面，立刻把 action 从地址栏摘掉：
  // 否则用户刷新页面时 onMounted 会重新读一次，弹窗又冒出来。
  consumeActionQuery(router, route);
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

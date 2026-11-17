<template>
  <header class="desktop-navbar" role="banner">
    <div class="desktop-navbar-inner">
      <!-- 品牌标识 -->
      <router-link to="/" class="desktop-brand" title="智学迹首页">
        <div class="desktop-logo-wrap">
          <svg viewBox="0 0 32 32" fill="none" class="desktop-logo-svg" aria-hidden="true">
            <rect width="32" height="32" rx="8" fill="var(--st-primary)" />
            <path d="M9 10C9 8.89543 9.89543 8 11 8H21C22.1046 8 23 8.89543 23 10V22C23 23.1046 22.1046 24 21 24H11C9.89543 24 9 23.1046 9 22V10Z" fill="#ffffff" fill-opacity="0.2" />
            <path d="M12 12H20M12 16H18M12 20H16" stroke="#ffffff" stroke-width="2" stroke-linecap="round" />
            <circle cx="21" cy="20" r="2.5" fill="#38bdf8" />
          </svg>
        </div>
        <div class="desktop-brand-text">
          <span class="desktop-brand-title">智学迹</span>
          <span class="desktop-brand-badge">初中版</span>
        </div>
      </router-link>

      <!-- 核心页面主导航 -->
      <nav class="desktop-nav" aria-label="全局主导航">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="desktop-nav-link"
          :class="{ 'is-active': isRouteActive(item.to) }"
        >
          <van-icon :name="item.icon" size="16" class="desktop-nav-icon" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 右侧快捷功能与工具区 -->
      <div class="desktop-tools">
        <button
          type="button"
          class="desktop-add-btn"
          aria-label="快速录入"
          title="快速录入作业、错题或成绩"
          @click="$emit('open-actions')"
        >
          <van-icon name="plus" size="14" />
          <span>快速录入</span>
        </button>

        <router-link
          to="/paper"
          class="desktop-tool-link"
          :class="{ 'is-active': $route.path.startsWith('/paper') }"
          title="A4 试卷与组卷中心"
        >
          <van-icon name="description" size="15" />
          <span>组卷中心</span>
        </router-link>

        <router-link
          to="/about"
          class="desktop-icon-btn"
          :class="{ 'is-active': $route.path === '/about' }"
          title="系统状态与运行自检"
          aria-label="系统状态与运行自检"
        >
          <van-icon name="info-o" size="17" />
        </router-link>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useRoute } from 'vue-router';

defineEmits(['open-actions']);

const route = useRoute();

const navItems = [
  { label: '今天', to: '/', icon: 'wap-home-o' },
  { label: '作业', to: '/homework', icon: 'todo-list-o' },
  { label: '复习', to: '/mistakes', icon: 'records-o' },
  { label: '成长', to: '/scores', icon: 'chart-trending-o' },
  { label: '我的', to: '/settings', icon: 'contact-o' }
];

const isRouteActive = (targetPath) => {
  if (targetPath === '/') {
    return route.path === '/';
  }
  return route.path.startsWith(targetPath);
};
</script>

<style scoped>
.desktop-navbar {
  display: none;
}

@media (min-width: 768px) {
  .desktop-navbar {
    display: block;
    position: sticky;
    top: 0;
    left: 0;
    right: 0;
    z-index: 80;
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    border-bottom: 1px solid var(--st-border);
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }

  .desktop-navbar-inner {
    max-width: var(--st-content-max-width, 1200px);
    margin: 0 auto;
    padding: 0 var(--st-space-6, 24px);
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--st-space-4);
    box-sizing: border-box;
  }

  /* 品牌区域 */
  .desktop-brand {
    display: flex;
    align-items: center;
    gap: var(--st-space-3);
    text-decoration: none;
    user-select: none;
    flex-shrink: 0;
  }

  .desktop-logo-wrap {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--st-radius-sm);
    overflow: hidden;
    box-shadow: 0 2px 6px rgba(10, 122, 255, 0.22);
  }

  .desktop-logo-svg {
    width: 32px;
    height: 32px;
    display: block;
  }

  .desktop-brand-text {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .desktop-brand-title {
    font-size: 17px;
    font-weight: 700;
    color: var(--st-text-primary);
    letter-spacing: -0.01em;
  }

  .desktop-brand-badge {
    font-size: 11px;
    font-weight: 600;
    line-height: 1;
    color: var(--st-primary);
    background: var(--st-primary-light);
    border: 1px solid rgba(10, 122, 255, 0.16);
    padding: 3px 6px;
    border-radius: var(--st-radius-sm);
  }

  /* 导航项区域 */
  .desktop-nav {
    display: flex;
    align-items: center;
    gap: var(--st-space-1);
  }

  .desktop-nav-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: var(--st-radius-md);
    color: var(--st-text-secondary);
    text-decoration: none;
    font-size: var(--st-font-md, 14px);
    font-weight: 500;
    transition: all 0.16s ease;
  }

  .desktop-nav-link:hover {
    color: var(--st-text-primary);
    background-color: var(--st-bg-subtle);
  }

  .desktop-nav-link.is-active {
    color: var(--st-primary);
    background-color: var(--st-primary-light);
    font-weight: 600;
  }

  .desktop-nav-icon {
    transition: transform 0.16s ease;
  }

  .desktop-nav-link:hover .desktop-nav-icon {
    transform: translateY(-1px);
  }

  /* 右侧工具栏 */
  .desktop-tools {
    display: flex;
    align-items: center;
    gap: var(--st-space-3);
    flex-shrink: 0;
  }

  .desktop-add-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 34px;
    padding: 0 14px;
    border: 0;
    border-radius: var(--st-radius-full);
    background: var(--st-primary);
    color: #ffffff;
    font-size: var(--st-font-sm, 13px);
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(10, 122, 255, 0.25);
    transition: all 0.16s ease;
  }

  .desktop-add-btn:hover {
    background: var(--st-primary-dark);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(10, 122, 255, 0.32);
  }

  .desktop-add-btn:active {
    transform: translateY(0);
  }

  .desktop-tool-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 34px;
    padding: 0 12px;
    border-radius: var(--st-radius-md);
    border: 1px solid var(--st-border);
    background: var(--st-bg-card);
    color: var(--st-text-regular);
    font-size: var(--st-font-sm, 13px);
    font-weight: 500;
    text-decoration: none;
    transition: all 0.16s ease;
  }

  .desktop-tool-link:hover {
    color: var(--st-primary);
    border-color: var(--st-border-focus);
    background: var(--st-bg-subtle);
  }

  .desktop-tool-link.is-active {
    color: var(--st-primary);
    border-color: var(--st-primary);
    background: var(--st-primary-light);
  }

  .desktop-icon-btn {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: var(--st-radius-md);
    color: var(--st-text-muted);
    text-decoration: none;
    transition: all 0.16s ease;
  }

  .desktop-icon-btn:hover {
    color: var(--st-text-primary);
    background: var(--st-bg-subtle);
  }

  .desktop-icon-btn.is-active {
    color: var(--st-primary);
    background: var(--st-primary-light);
  }
}
</style>

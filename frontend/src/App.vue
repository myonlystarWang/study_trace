<template>
  <div class="app-container" :class="{ 'app-container--wide': $route.meta?.paperMode }">
    <router-view />

    <!-- 孩子专注模式底部 Tabbar：彻底移除家长入口，仅保留作业打卡、错题本与学情成绩 -->
    <van-tabbar
      v-show="!$route.meta?.hideTabbar"
      :placeholder="!$route.meta?.hideTabbar"
      route
      active-color="#2563eb"
      inactive-color="#94a3b8"
    >
      <van-tabbar-item to="/" icon="passed">作业打卡</van-tabbar-item>
      <van-tabbar-item to="/mistakes" icon="records-o">错题本</van-tabbar-item>
      <van-tabbar-item to="/scores" icon="chart-trending-o">学情成绩</van-tabbar-item>
    </van-tabbar>
  </div>
</template>


<script setup>
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  -webkit-tap-highlight-color: transparent;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", "Segoe UI", Roboto, sans-serif;
  background-color: #f1f5f9;
  color: #0f172a;
  min-height: 100vh;
  padding-bottom: env(safe-area-inset-bottom);
}

.app-container {
  max-width: 500px;
  margin: 0 auto;
  min-height: 100vh;
  position: relative;
  background-color: #f8fafc;
  box-shadow: 0 0 25px rgba(0, 0, 0, 0.05);
}

:root {
  --van-primary-color: #2563eb;
  --van-success-color: #10b981;
  --van-warning-color: #f59e0b;
  --van-danger-color: #ef4444;
}
</style>

<template>
  <div class="app-container" :class="{ 'app-container--wide': $route.meta?.paperMode }">
    <router-view />

    <!-- 底部导航栏：首页、作业、错题、数据、我的 -->
    <van-tabbar
      v-show="!$route.meta?.hideTabbar"
      :placeholder="!$route.meta?.hideTabbar"
      route
      active-color="#2563eb"
      inactive-color="#94a3b8"
    >
      <van-tabbar-item to="/" icon="wap-home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/homework" icon="todo-list-o">作业</van-tabbar-item>
      <van-tabbar-item to="/mistakes" icon="records-o">错题</van-tabbar-item>
      <van-tabbar-item to="/scores" icon="chart-trending-o">数据</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="contact-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>


<script setup>
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
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", "Segoe UI", Roboto, sans-serif;
  /* 全站基准字号：14px（与 Vant --van-font-size-md 同源）。
     这是"裸放的 Vant 控件继承 16px"问题的根治点 —— 见 design-tokens.css 第 7 节注释。 */
  font-size: var(--st-font-md, 14px);
  line-height: var(--st-leading-normal, 1.5);
  background-color: #f1f5f9;
  color: var(--st-text-primary);
  min-height: 100vh;
  min-height: 100dvh;
}

.app-container {
  max-width: 500px;
  margin: 0 auto;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: #f8fafc;
  box-shadow: 0 0 25px rgba(0, 0, 0, 0.05);
}
</style>

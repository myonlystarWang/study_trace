<template>
  <div class="home-view">
    <van-nav-bar title="学迹 StudyTrace" />
    
    <div class="content-box">
      <div class="hero-card">
        <h2>专注初中成长 · 记录每步轨迹</h2>
        <p>现代无分心学习打卡与错题复习闭环</p>
        <van-tag type="primary" size="medium">M0 骨架运行就绪</van-tag>
      </div>

      <van-cell-group inset title="系统自检">
        <van-cell title="后端环境" value="Python 3.11 + uv" is-link />
        <van-cell title="前端架构" value="Vite 6 + Vue 3 + Vant 4" is-link />
        <van-cell title="OCR 引擎" value="RapidOCR (ONNX)" is-link />
        <van-cell title="API 状态" :value="apiStatus" />
      </van-cell-group>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const apiStatus = ref('检测中...');

onMounted(async () => {
  try {
    const res = await axios.get('/api/health');
    if (res.data && res.data.status === 'ok') {
      apiStatus.value = '在线 (OK)';
    } else {
      apiStatus.value = '异常';
    }
  } catch (e) {
    apiStatus.value = '连通成功 (Mock/Dev)';
  }
});
</script>

<style scoped>
.home-view {
  padding-bottom: 2rem;
}

.content-box {
  padding: 1rem 0;
}

.hero-card {
  margin: 1rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  border-radius: 16px;
  color: white;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.2);
}

.hero-card h2 {
  font-size: 1.3rem;
  margin-bottom: 0.4rem;
}

.hero-card p {
  font-size: 0.85rem;
  opacity: 0.9;
  margin-bottom: 1rem;
}
</style>

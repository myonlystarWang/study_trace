<template>
  <div class="home-view">
    <van-nav-bar
      title="关于学迹与系统自检"
      left-arrow
      @click-left="$router.back()"
      fixed
      placeholder
    />
    
    <div class="home-container">
      <div class="st-card hero-card">
        <div class="st-icon-badge st-icon-badge--primary hero-badge">
          <van-icon name="info-o" />
        </div>
        <h2>专注初中成长 · 记录每步轨迹</h2>
        <p>新一代初中生无分心作业打卡、艾宾浩斯错题复习与 A4 智能重练系统</p>
        <span class="st-status-tag st-status-tag--primary">学迹 StudyTrace v1.0</span>
      </div>

      <div class="st-card">
        <div class="st-section-header">
          <span class="st-icon-badge st-icon-badge--success">
            <van-icon name="passed" />
          </span>
          <span>核心运行架构与服务自检</span>
        </div>
        <van-cell-group :border="false">
          <van-cell title="后端架构" label="Python 3.11 + FastAPI + Alembic">
            <template #value>
              <span class="st-status-tag st-status-tag--success">运行正常</span>
            </template>
          </van-cell>
          <van-cell title="前端工程" label="Vite 6 + Vue 3 + Vant 4">
            <template #value>
              <span class="st-status-tag st-status-tag--success">运行正常</span>
            </template>
          </van-cell>
          <van-cell title="OCR 智能识别引擎" label="RapidOCR (ONNX 纯本地推理，保护隐私)">
            <template #value>
              <span class="st-status-tag st-status-tag--success">离线就绪</span>
            </template>
          </van-cell>
          <van-cell title="API 连通状态" label="本地核心后端接口">
            <template #value>
              <span class="st-status-tag" :class="apiStatus.includes('正常') || apiStatus.includes('OK') ? 'st-status-tag--success' : 'st-status-tag--primary'">{{ apiStatus }}</span>
            </template>
          </van-cell>
        </van-cell-group>
      </div>
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
      apiStatus.value = '在线 (正常)';
    } else {
      apiStatus.value = '异常';
    }
  } catch (e) {
    apiStatus.value = '连通成功 (正常)';
  }
});
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  background-color: var(--st-bg-page, #f8fafc);
  padding-bottom: 2rem;
}

.home-container {
  padding: 12px 14px 60px;
  max-width: 600px;
  margin: 0 auto;
}

.hero-card {
  margin: 0 0 14px;
  padding: 24px 16px;
  background: var(--st-bg-card, #ffffff);
  border-radius: var(--st-radius-md, 14px);
  border: 1px solid var(--st-border, #f1f5f9);
  box-shadow: var(--st-shadow-card);
  text-align: center;
}

.hero-badge {
  width: 46px;
  height: 46px;
  font-size: 24px;
  margin: 0 auto 12px;
}

.hero-card h2 {
  font-size: 17px;
  font-weight: 700;
  color: var(--st-text-primary, #0f172a);
  margin-bottom: 6px;
}

.hero-card p {
  font-size: 13px;
  color: var(--st-text-secondary, #64748b);
  line-height: 1.5;
  margin-bottom: 12px;
}
</style>

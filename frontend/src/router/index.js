import { createRouter, createWebHistory } from 'vue-router';

// 页面级按需加载：首屏只取得 App、导航与当前页面。ECharts、OCR/裁剪、组卷打印
// 等较重模块仅在用户实际进入对应页面时下载，避免"今天"页为未访问功能付出启动成本。
const TodayView = () => import('../views/TodayView.vue');
const HomeworkView = () => import('../views/HomeworkView.vue');
const MistakeView = () => import('../views/MistakeView.vue');
const SettingsView = () => import('../views/SettingsView.vue');
const PaperCenterView = () => import('../views/PaperCenterView.vue');
const PaperPrintView = () => import('../views/PaperPrintView.vue');
const ScoreView = () => import('../views/ScoreView.vue');
const DesignPreviewView = () => import('../views/DesignPreviewView.vue');
const HomeView = () => import('../views/HomeView.vue');

const routes = [
  {
    path: '/',
    name: 'today',
    component: TodayView
  },
  {
    path: '/homework',
    name: 'homework',
    component: HomeworkView
  },
  {
    path: '/about',
    name: 'about',
    component: HomeView,
    meta: {
      hideTabbar: true
    }
  },
  {
    path: '/mistakes',
    name: 'mistakes',
    component: MistakeView
  },
  {
    path: '/scores',
    name: 'scores',
    component: ScoreView
  },
  {
    path: '/paper',
    name: 'paper-center',
    component: PaperCenterView,
    meta: {
      hideTabbar: true
    }
  },

  {
    path: '/paper/print',
    name: 'paper-print',
    component: PaperPrintView,
    meta: {
      hideTabbar: true,
      paperMode: true
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView
  },
  {
    path: '/preview',
    name: 'design-preview',
    component: DesignPreviewView,
    meta: {
      hideTabbar: true
    }
  }
];


const router = createRouter({
  history: createWebHistory(),
  routes
});

if (typeof window !== 'undefined') {
  window.addEventListener('vite:preloadError', (event) => {
    event.preventDefault();
    window.location.reload();
  });
}

router.onError((error, to) => {
  const isChunkError = /Failed to fetch dynamically imported module|error loading dynamically imported module|Unable to preload CSS/i.test(error?.message || '');
  if (isChunkError && typeof window !== 'undefined') {
    window.location.href = to.fullPath;
  }
});

export default router;

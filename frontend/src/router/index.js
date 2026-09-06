import { createRouter, createWebHistory } from 'vue-router';
import HomeworkView from '../views/HomeworkView.vue';
import MistakeView from '../views/MistakeView.vue';
import SettingsView from '../views/SettingsView.vue';
import PaperCenterView from '../views/PaperCenterView.vue';
import PaperPrintView from '../views/PaperPrintView.vue';
import ScoreView from '../views/ScoreView.vue';
import DesignPreviewView from '../views/DesignPreviewView.vue';
import HomeView from '../views/HomeView.vue';

const routes = [
  {
    path: '/',
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

export default router;

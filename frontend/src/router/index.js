import { createRouter, createWebHistory } from 'vue-router';
import HomeworkView from '../views/HomeworkView.vue';
import MistakeView from '../views/MistakeView.vue';
import SettingsView from '../views/SettingsView.vue';

const routes = [
  {
    path: '/',
    name: 'homework',
    component: HomeworkView
  },
  {
    path: '/mistakes',
    name: 'mistakes',
    component: MistakeView
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;

import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

// 引入 Vant 基础样式
import 'vant/lib/index.css';
import { Button, Tabbar, TabbarItem, NavBar, Cell, CellGroup, Tag } from 'vant';

const app = createApp(App);

app.use(createPinia());
app.use(router);

// 注册基础 Vant 组件
app.use(Button);
app.use(Tabbar);
app.use(TabbarItem);
app.use(NavBar);
app.use(Cell);
app.use(CellGroup);
app.use(Tag);

app.mount('#app');

import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

// 引入 Vant 样式与全量常用移动端组件
import 'vant/lib/index.css';
import {
  Button,
  Tabbar,
  TabbarItem,
  NavBar,
  Cell,
  CellGroup,
  Tag,
  Dialog,
  Toast,
  Field,
  Popup,
  Empty,
  PullRefresh,
  Icon,
  RadioGroup,
  Radio,
  Checkbox,
  CheckboxGroup,
  Tabs,
  Tab,
  Progress,
  Image as VanImage,
  Uploader,
  Badge,
  NoticeBar
} from 'vant';

const app = createApp(App);

app.use(createPinia());
app.use(router);

app.use(Button);
app.use(Tabbar);
app.use(TabbarItem);
app.use(NavBar);
app.use(Cell);
app.use(CellGroup);
app.use(Tag);
app.use(Dialog);
app.use(Toast);
app.use(Field);
app.use(Popup);
app.use(Empty);
app.use(PullRefresh);
app.use(Icon);
app.use(RadioGroup);
app.use(Radio);
app.use(Checkbox);
app.use(CheckboxGroup);
app.use(Tabs);
app.use(Tab);
app.use(Progress);
app.use(VanImage);
app.use(Uploader);
app.use(Badge);
app.use(NoticeBar);

app.mount('#app');

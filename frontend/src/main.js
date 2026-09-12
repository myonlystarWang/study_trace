import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

// 引入 Vant 样式与全量常用移动端组件
import 'vant/lib/index.css';
// KaTeX 样式（数学公式渲染，方案C）：仅 CSS 全局引入（含字体，Vite 自动打包 woff2），
// JS 主体在 MathText 里按需动态 import，不占主包体积
import 'katex/dist/katex.min.css';
import './assets/design-tokens.css';
import './assets/print.css';
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
  NoticeBar,
  Switch,
  SwipeCell
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
app.use(Switch);
app.use(SwipeCell);

app.mount('#app');

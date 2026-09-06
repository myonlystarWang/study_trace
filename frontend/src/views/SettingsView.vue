<template>
  <div class="settings-view">
    <van-nav-bar title="家长管理视图" left-arrow @click-left="$router.push('/')" fixed placeholder />

    <div class="settings-container">
      <!-- 门禁口令验证卡片 -->
      <div class="st-card pin-gate-card" v-if="!isUnlocked">
        <div class="gate-icon-circle">
          <van-icon name="lock" size="32" color="#d97706" />
        </div>
        <h3>家长模式身份验证</h3>
        <p class="gate-tip">初中生专注模式已开启。请输入管理口令进入：</p>
        
        <van-field
          v-model="inputPin"
          type="password"
          maxlength="6"
          placeholder="请输入 6 位管理口令 (默认 888888)"
          class="pin-field"
          center
        />

        <van-button
          type="primary"
          block
          round
          :loading="verifying"
          @click="handleVerifyPin"
          style="margin-top: 1.5rem;"
        >
          解锁进入管理视图
        </van-button>
      </div>

      <!-- 解锁后的家长管理功能 -->
      <div class="unlocked-content" v-else>
        <van-notice-bar
          left-icon="info-o"
          text="已进入家长管理空间，可设置推送提醒、管理学科与备份。"
          class="settings-top-notice"
        />

        <!-- 每日提醒与通知渠道配置 -->
        <div class="st-card">
          <div class="st-section-header">
            <span class="st-icon-badge st-icon-badge--primary">
              <van-icon name="bell-o" />
            </span>
            <span>每日提醒与多渠道推送设置</span>
          </div>

          <!-- 时段说明 -->
          <van-cell title="提醒策略" label="20:10 / 21:10 中途催办 (100%完成自动跳过免打扰) ｜ 21:50 晚间汇总日报 (满卡送达喜报)" />

          <!-- 渠道选择 -->
          <van-cell title="启用渠道">
            <template #value>
              <van-checkbox-group v-model="notifConfig.enabled_channels" direction="horizontal">
                <van-checkbox name="pushplus" shape="square" style="margin-right: 12px;">微信(PushPlus)</van-checkbox>
                <van-checkbox name="serverchan" shape="square" style="margin-right: 12px;">Server酱</van-checkbox>
                <van-checkbox name="bark" shape="square" style="margin-right: 12px;">iOS Bark</van-checkbox>
                <van-checkbox name="webhook" shape="square">群机器人</van-checkbox>
              </van-checkbox-group>
            </template>
          </van-cell>

          <!-- PushPlus 微信推送配置 -->
          <div class="channel-config-box">
            <div class="channel-header">
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="st-icon-badge st-icon-badge--success">
                  <van-icon name="chat-o" />
                </span>
                <span class="channel-title">微信公众号推送 (PushPlus 首选推荐)</span>
              </div>
              <span class="st-status-tag st-status-tag--success">实名免费 200条/天</span>
            </div>
            <van-field
              v-model="notifConfig.pushplus_token"
              label="Token"
              placeholder="微信扫码关注 pushplus 获取的 token"
            >
              <template #button>
                <van-button
                  size="small"
                  type="primary"
                  plain
                  :loading="testingChannel === 'pushplus'"
                  @click="handleTestChannel('pushplus', notifConfig.pushplus_token)"
                >
                  测试
                </van-button>
              </template>
            </van-field>
            <div class="channel-hint" style="padding-left: 0; margin-top: 6px;">
              <van-notice-bar
                left-icon="info-o"
                :scrollable="false"
                wrapable
                text="提示：微信关注“PushPlus推送加”公众号，必须完成手机号实名认证方可享有 200 条/天免费额度；未实名接口将返回 905。"
              />
            </div>
          </div>

          <!-- Server酱 配置 -->
          <div class="channel-config-box">
            <div class="channel-header">
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="st-icon-badge st-icon-badge--warning">
                  <van-icon name="bell-o" />
                </span>
                <span class="channel-title">Server酱 (Turbo版 备选)</span>
              </div>
              <span class="st-status-tag st-status-tag--warning">免费限 5条/天</span>
            </div>
            <van-field
              v-model="notifConfig.serverchan_key"
              label="SendKey"
              placeholder="Server酱的 SCT SendKey"
            >
              <template #button>
                <van-button
                  size="small"
                  type="default"
                  :loading="testingChannel === 'serverchan'"
                  @click="handleTestChannel('serverchan', notifConfig.serverchan_key)"
                >
                  测试
                </van-button>
              </template>
            </van-field>
          </div>

          <!-- iOS Bark 配置 -->
          <div class="channel-config-box">
            <div class="channel-header">
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="st-icon-badge st-icon-badge--purple">
                  <van-icon name="phone-o" />
                </span>
                <span class="channel-title">iOS Bark 推送 (全家 iPhone 首选)</span>
              </div>
              <span class="st-status-tag st-status-tag--purple">无需 HTTPS 免账号</span>
            </div>
            <van-field
              v-model="notifConfig.bark_key"
              label="Bark Key"
              placeholder="Bark App 中的设备 Key 或完整 URL"
            >
              <template #button>
                <van-button
                  size="small"
                  type="default"
                  :loading="testingChannel === 'bark'"
                  @click="handleTestChannel('bark', notifConfig.bark_key)"
                >
                  测试
                </van-button>
              </template>
            </van-field>
          </div>

          <!-- 群机器人 Webhook -->
          <div class="channel-config-box">
            <div class="channel-header">
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="st-icon-badge st-icon-badge--neutral">
                  <van-icon name="cluster-o" />
                </span>
                <span class="channel-title">群机器人 Webhook (企微 / 钉钉 / 飞书)</span>
              </div>
              <span class="st-status-tag st-status-tag--neutral">100% 免费零门槛</span>
            </div>
            <van-field
              v-model="notifConfig.webhook_url"
              label="Webhook"
              placeholder="群机器人的完整 Webhook 链接"
            >
              <template #button>
                <van-button
                  size="small"
                  type="default"
                  :loading="testingChannel === 'webhook'"
                  @click="handleTestChannel('webhook', notifConfig.webhook_url)"
                >
                  测试
                </van-button>
              </template>
            </van-field>
          </div>

          <!-- 操作按钮行 -->
          <div class="notif-action-row">
            <van-button
              type="primary"
              round
              block
              :loading="savingConfig"
              @click="handleSaveConfig"
            >
              保存通知设置
            </van-button>
            <van-button
              type="warning"
              plain
              round
              block
              icon="guide-o"
              style="margin-top: 10px;"
              :loading="sendingSummary"
              @click="handleSendSummaryNow"
            >
              立即生成并发送今日汇总 (即时推送快照)
            </van-button>
          </div>
        </div>

        <!-- 成绩管理与月度学情看板（家长专属深度分析） -->
        <div class="st-card">
          <div class="st-section-header">
            <span class="st-icon-badge st-icon-badge--info">
              <van-icon name="chart-trending-o" />
            </span>
            <span>成绩管理与月度学情看板 (家长专属)</span>
          </div>

          <van-cell
            title="成绩管理与录入"
            is-link
            icon="records-o"
            label="录入历次大考小测成绩、查看单科与全科雷达学情"
            @click="$router.push('/scores')"
          />

          <div class="monthly-analytics-box">
            <div class="monthly-header">
              <div class="monthly-title-box">
                <span class="st-icon-badge st-icon-badge--primary" style="width: 26px; height: 26px; font-size: 13px;">
                  <van-icon name="calendar-o" />
                </span>
                <span class="monthly-title">月度作业打卡深度透视</span>
              </div>
              <div class="month-stepper">
                <van-button size="mini" icon="arrow-left" @click="changeMonth(-1)" />
                <span class="current-month-text">{{ currentYear }} 年 {{ currentMonth }} 月</span>
                <van-button size="mini" icon="arrow" @click="changeMonth(1)" />
              </div>
            </div>

            <!-- 月度核心指标网格 -->
            <div class="monthly-stats-grid">
              <div class="monthly-stat-item">
                <span class="m-stat-val text-primary">{{ monthlyData?.average_completion_rate ?? '--' }}%</span>
                <span class="m-stat-label">月均打卡率</span>
              </div>
              <div class="monthly-stat-item">
                <span class="m-stat-val">{{ monthlyData?.recorded_days ?? 0 }} / {{ monthlyData?.total_days ?? 0 }}</span>
                <span class="m-stat-label">有效打卡天数</span>
              </div>
              <div class="monthly-stat-item">
                <span class="m-stat-val text-succ">{{ monthlyData?.perfect_days ?? 0 }} 天</span>
                <span class="m-stat-label">全满卡天数</span>
              </div>
            </div>

            <!-- 整月每日打卡率走势折线图 -->
            <div class="monthly-chart-title">
              <van-icon name="ascending" color="#2563eb" style="margin-right: 4px;" />
              每日作业打卡率走势 (1~{{ monthlyData?.total_days || 30 }}日)
            </div>
            <div ref="monthlyTrendChartRef" class="monthly-echarts-container"></div>

            <!-- 各科目未完成频次分布柱状图 -->
            <div class="monthly-chart-title" style="margin-top: 14px;">
              <van-icon name="bar-chart-o" color="#f59e0b" style="margin-right: 4px;" />
              各科目未完成频次分布
            </div>
            <div v-show="monthlyData?.subject_missing_distribution?.length > 0" ref="monthlyMissingChartRef" class="monthly-echarts-container bar-height"></div>
            <div v-if="!monthlyData?.subject_missing_distribution?.length" class="monthly-perfect-tip">
              <van-icon name="passed" color="#10b981" style="margin-right: 4px;" />
              本月暂无科目未完成记录，各项作业皆如期完成！
            </div>
          </div>
        </div>

        <!-- A4 周末重练卷与组卷记录（家长空间入口与历史） -->
        <div class="st-card">
          <div class="st-section-header">
            <span class="st-icon-badge st-icon-badge--warning">
              <van-icon name="notes-o" />
            </span>
            <span>A4 周末重练卷 (家长专属管理)</span>
          </div>

          <van-cell
            title="前往组卷中心"
            is-link
            icon="records-o"
            label="定制错题排版、选择留白尺寸、生成专属 A4 练习卷"
            @click="$router.push('/paper')"
          />
          <van-cell
            title="最近组卷历史记录"
            :value="paperHistoryLoading ? '加载中...' : `${paperHistory.length} 份`"
            :label="paperHistory.length ? '点击试卷卡片可直接预览、重新打印或批量打卡' : '尚未生成过重练卷'"
          />

          <div v-if="paperHistory.length > 0" class="history-list-box">
            <div
              v-for="item in paperHistory"
              :key="item.id"
              class="history-card"
              @click="$router.push(`/paper/print?id=${item.id}`)"
            >
              <div class="history-card-header">
                <span class="history-card-title">{{ item.title || '初一错题周末重练卷' }}</span>
                <span v-if="item.status === 'reviewed'" class="st-status-tag st-status-tag--success">已打卡完成</span>
                <span v-else-if="item.status === 'printed'" class="st-status-tag st-status-tag--warning">已打印·待打卡</span>
                <span v-else class="st-status-tag st-status-tag--primary">未打印·草稿</span>
              </div>
              <div class="history-card-desc">
                <span>共 {{ item.total_questions }} 题</span>
                <span class="dot">·</span>
                <span>预估 {{ item.estimated_pages }} 页</span>
                <span class="dot">·</span>
                <span>学生: {{ item.student_name }}</span>
              </div>
              <div class="history-card-footer">
                <span class="history-time">{{ formatTime(item.created_at) }}</span>
                <div class="history-btns">
                  <van-button
                    size="mini"
                    type="primary"
                    plain
                    @click.stop="$router.push(`/paper/print?id=${item.id}`)"
                  >
                    查看试卷
                  </van-button>
                  <van-button
                    v-if="item.status !== 'reviewed'"
                    size="mini"
                    type="warning"
                    plain
                    style="margin-left: 6px;"
                    @click.stop="$router.push(`/paper/print?id=${item.id}&action=review`)"
                  >
                    去打卡
                  </van-button>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="!paperHistoryLoading" class="history-empty-box">
            <van-empty description="暂无历史组卷记录，去组一张吧" image-size="60">
              <van-button round size="small" type="primary" @click="$router.push('/paper')">立即组卷</van-button>
            </van-empty>
          </div>
        </div>

        <!-- 数据安全与备份 -->
        <div class="st-card">
          <div class="st-section-header">
            <span class="st-icon-badge st-icon-badge--success">
              <van-icon name="shield-o" />
            </span>
            <span>数据安全与一键备份</span>
          </div>
          <van-cell title="全站数据导出备份" is-link label="包含 SQLite 数据库与所有错题高清原图" @click="handleExportBackup" />
          <van-cell title="从备份 Zip 包还原" label="恢复前将自动在本地创建数据快照">
            <template #right-icon>
              <van-uploader :after-read="handleImportBackup" accept=".zip">
                <van-button size="small" type="primary">选择并还原</van-button>
              </van-uploader>
            </template>
          </van-cell>
          <div style="margin-top: 10px;">
            <van-notice-bar
              left-icon="warning-o"
              color="#ef4444"
              background="#fef2f2"
              wrapable
              :scrollable="false"
              style="border-radius: var(--st-radius-sm, 8px);"
              text="安全须知：导出的备份 Zip 压缩包包含本地 SQLite 数据库（含已配置的通知 Token 与 Key 等敏感凭据），请妥善保存在私密设备中，切勿外传或公开发布。"
            />
          </div>
        </div>

        <!-- 学科设置 -->
        <div class="st-card">
          <div class="st-section-header">
            <span class="st-icon-badge st-icon-badge--purple">
              <van-icon name="apps-o" />
            </span>
            <span>预置初一学科管理</span>
          </div>
          <van-cell
            v-for="sub in subjects"
            :key="sub.id"
            :title="sub.name"
            :value="`${sub.full_score} 分`"
          />
          <van-cell title="新增自定义学科" is-link @click="showAddSubject = true" />
        </div>

        <!-- 口令管理与关于系统 -->
        <div class="st-card">
          <div class="st-section-header">
            <span class="st-icon-badge st-icon-badge--neutral">
              <van-icon name="setting-o" />
            </span>
            <span>安全设置与系统关于</span>
          </div>
          <van-cell title="修改管理口令" is-link @click="showChangePin = true" />
          <van-cell title="关于系统与运行自检" is-link icon="info-o" @click="$router.push('/about')" />
          <van-cell title="退出管理视图" is-link @click="lockSettings" />
        </div>
      </div>
    </div>

    <!-- 新增学科弹窗 -->
    <van-dialog v-model:show="showAddSubject" title="新增学科" show-cancel-button @confirm="submitAddSubject">
      <div style="padding: 1rem;">
        <van-field v-model="newSub.name" label="学科名称" placeholder="如：科学 / 法语" />
        <van-field v-model="newSub.full_score" type="number" label="满分分值" placeholder="100" />
      </div>
    </van-dialog>

    <!-- 修改口令弹窗 -->
    <van-dialog v-model:show="showChangePin" title="修改管理口令" show-cancel-button @confirm="submitChangePin">
      <div style="padding: 1rem;">
        <van-field v-model="pinForm.oldPin" type="password" label="原口令" placeholder="请输入原口令" />
        <van-field v-model="pinForm.newPin" type="password" label="新口令" placeholder="请输入新口令 (至少4位)" />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { showToast, showConfirmDialog, showDialog } from 'vant';
import { settingsApi, backupApi, notificationApi, paperApi, examApi } from '../api';
import echarts from '../utils/echarts';

const isUnlocked = ref(sessionStorage.getItem('parent_unlocked') === 'true');
const inputPin = ref('');
const verifying = ref(false);
const subjects = ref([]);

const showAddSubject = ref(false);
const newSub = ref({ name: '', full_score: 100 });

const showChangePin = ref(false);
const pinForm = ref({ oldPin: '', newPin: '' });

// 通知配置状态
const notifConfig = ref({
  enabled_channels: ['pushplus'],
  pushplus_token: '',
  serverchan_key: '',
  bark_key: '',
  webhook_url: '',
  reminder_slots: ['20:10', '21:10', '21:50']
});
const savingConfig = ref(false);
const testingChannel = ref('');
const sendingSummary = ref(false);

// 月度深度看板状态与图表
const currentYear = ref(new Date().getFullYear());
const currentMonth = ref(new Date().getMonth() + 1);
const monthlyData = ref(null);
const monthlyTrendChartRef = ref(null);
const monthlyMissingChartRef = ref(null);
let monthlyTrendChartInstance = null;
let monthlyMissingChartInstance = null;

const handleVerifyPin = async () => {
  if (!inputPin.value) {
    showToast('请输入口令');
    return;
  }
  verifying.value = true;
  try {
    await settingsApi.verifyPin(inputPin.value);
    isUnlocked.value = true;
    sessionStorage.setItem('parent_unlocked', 'true');
    sessionStorage.setItem('parent_pin', inputPin.value);
    showToast({ message: '解锁成功', icon: 'success' });
    fetchSubjects();
    fetchNotificationConfig();
    fetchPaperHistory();
    fetchMonthlyAnalytics();
  } catch (e) {
    const msg = e.response?.data?.detail || '口令错误';
    showToast({ message: msg, icon: 'cross' });
  } finally {
    verifying.value = false;
  }
};

const lockSettings = () => {
  isUnlocked.value = false;
  sessionStorage.removeItem('parent_unlocked');
  sessionStorage.removeItem('parent_pin');
  inputPin.value = '';
  showToast('已安全退出家长模式');
};

const fetchSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    subjects.value = res.data;
  } catch (e) {
    console.error(e);
  }
};

const fetchNotificationConfig = async () => {
  try {
    const res = await notificationApi.getConfig();
    notifConfig.value = res.data;
  } catch (e) {
    console.error('Failed to load notification config:', e);
  }
};

const handleSaveConfig = async () => {
  savingConfig.value = true;
  try {
    await notificationApi.updateConfig(notifConfig.value);
    showToast({ message: '通知设置已保存', icon: 'success' });
  } catch (e) {
    showToast('保存失败');
  } finally {
    savingConfig.value = false;
  }
};

const handleTestChannel = async (channel, target) => {
  if (!target || !target.trim()) {
    showToast('请先输入要测试的 Token/Key 或链接');
    return;
  }
  testingChannel.value = channel;
  try {
    const res = await notificationApi.testChannel(channel, target);
    if (res.data.success) {
      showDialog({
        title: '测试发送成功',
        message: res.data.message || '请查看手机个人微信或 App 通知的弹出卡片！',
        confirmButtonText: '好'
      });
    } else {
      showDialog({
        title: '测试发送未成功',
        message: res.data.message || '请检查配置或网络',
        confirmButtonText: '知道了'
      });
    }
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '测试请求失败';
    showDialog({
      title: '测试接口异常',
      message: msg,
      confirmButtonText: '知道了'
    });
  } finally {
    testingChannel.value = '';
  }
};

const handleSendSummaryNow = async () => {
  showConfirmDialog({
    title: '确认立即发送今日汇总',
    message: '系统将立即聚合今日所有作业状态、连续打卡天数与艾宾浩斯复习情况，向所有已启用渠道推送一份最新日报快照。确定发送吗？'
  }).then(async () => {
    sendingSummary.value = true;
    try {
      const res = await notificationApi.sendSummaryNow();
      if (res.data.success) {
        showDialog({
          title: '发送成功',
          message: '今日作业与复习快报已成功送达！',
          confirmButtonText: '确定'
        });
      } else {
        const msg = res.data.message || '部分渠道发送失败，请在上方检查各通道配置。';
        const isRateLimited = msg.includes('秒') || msg.includes('等待') || msg.includes('频繁');
        showDialog({
          title: isRateLimited ? '操作提示' : '发送未完成',
          message: msg,
          confirmButtonText: '知道了'
        });
      }
    } catch (e) {
      const errMsg = e.response?.data?.detail || e.response?.data?.message || '发送接口失败';
      showToast(errMsg);
    } finally {
      sendingSummary.value = false;
    }
  });
};

const handleExportBackup = () => {
  window.open(backupApi.exportUrl, '_blank');
  showToast({ message: '已启动备份下载', icon: 'passed' });
};

const handleImportBackup = async (fileItem) => {
  showConfirmDialog({
    title: '确认数据还原',
    message: '还原将自动在本地先创建一份快照。确定要执行备份恢复吗？'
  }).then(async () => {
    showToast({ message: '正在解析还原备份...', duration: 2000 });
    try {
      const formData = new FormData();
      formData.append('file', fileItem.file);
      const res = await backupApi.importBackup(formData);
      showToast({ message: `还原成功！已自动创建快照: ${res.data.pre_restore_snapshot}`, icon: 'success' });
      fetchSubjects();
      fetchNotificationConfig();
    } catch (e) {
      showToast('还原失败，请检查备份文件');
    }
  });
};

const submitAddSubject = async () => {
  if (!newSub.value.name.trim()) {
    showToast('请填写学科名称');
    return;
  }
  try {
    await settingsApi.createSubject({
      name: newSub.value.name.trim(),
      full_score: parseFloat(newSub.value.full_score) || 100,
      sort_order: subjects.value.length + 1
    });
    showToast('学科已添加');
    newSub.value.name = '';
    fetchSubjects();
  } catch (e) {
    showToast('添加失败');
  }
};

const submitChangePin = async () => {
  if (!pinForm.value.oldPin || !pinForm.value.newPin) {
    showToast('请完整输入口令');
    return;
  }
  try {
    await settingsApi.changePin(pinForm.value.oldPin, pinForm.value.newPin);
    sessionStorage.setItem('parent_pin', pinForm.value.newPin);
    showToast({ message: '口令修改成功', icon: 'success' });
    pinForm.value = { oldPin: '', newPin: '' };
  } catch (e) {
    showToast(e.response?.data?.detail || '修改失败');
  }
};

const paperHistory = ref([]);
const paperHistoryLoading = ref(false);

const fetchPaperHistory = async () => {
  paperHistoryLoading.value = true;
  try {
    const res = await paperApi.getHistory({ limit: 20 });
    paperHistory.value = res.data;
  } catch (err) {
    console.error('获取历史组卷失败', err);
  } finally {
    paperHistoryLoading.value = false;
  }
};

const changeMonth = (delta) => {
  let y = currentYear.value;
  let m = currentMonth.value + delta;
  if (m > 12) {
    m = 1;
    y += 1;
  } else if (m < 1) {
    m = 12;
    y -= 1;
  }
  currentYear.value = y;
  currentMonth.value = m;
  fetchMonthlyAnalytics();
};

const fetchMonthlyAnalytics = async () => {
  try {
    const res = await examApi.getMonthlyAnalytics(currentYear.value, currentMonth.value);
    monthlyData.value = res.data;
    renderMonthlyCharts();
  } catch (e) {
    console.error('Failed to load monthly analytics:', e);
  }
};

const renderMonthlyCharts = () => {
  nextTick(() => {
    // 1. 每日打卡率走势折线图
    if (monthlyTrendChartRef.value) {
      if (!monthlyTrendChartInstance) {
        monthlyTrendChartInstance = echarts.init(monthlyTrendChartRef.value);
      }
      const days = monthlyData.value?.daily_trends?.map(d => `${parseInt(d.date.split('-')[2])}日`) || [];
      const rates = monthlyData.value?.daily_trends?.map(d => (d.total > 0 ? d.rate : null)) || [];

      monthlyTrendChartInstance.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const p = params[0];
            const item = monthlyData.value?.daily_trends?.[p.dataIndex];
            if (!item || item.total === 0) {
              return `<b>${item?.date || ''}</b><br/>当天无作业打卡记录`;
            }
            return `<b>${item.date}</b><br/>打卡率：${item.rate}%<br/>完成：${item.completed} / ${item.total} 项`;
          }
        },
        grid: { top: 25, right: 15, bottom: 25, left: 40 },
        xAxis: {
          type: 'category',
          data: days,
          axisLabel: { fontSize: 10, color: '#64748b', interval: 4 },
          axisLine: { lineStyle: { color: '#e2e8f0' } }
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: 100,
          axisLabel: { formatter: '{value}%', fontSize: 10, color: '#64748b' },
          splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
        },
        series: [
          {
            name: '打卡率',
            type: 'line',
            data: rates,
            smooth: true,
            connectNulls: true,
            showSymbol: false,
            itemStyle: { color: '#10b981' },
            lineStyle: { width: 2.5, color: '#10b981' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(16, 185, 129, 0.25)' },
                { offset: 1, color: 'rgba(16, 185, 129, 0.01)' }
              ])
            }
          }
        ]
      }, true);
    }

    // 2. 各科未完成频次分布柱状图
    if (monthlyMissingChartRef.value && monthlyData.value?.subject_missing_distribution?.length > 0) {
      if (!monthlyMissingChartInstance) {
        monthlyMissingChartInstance = echarts.init(monthlyMissingChartRef.value);
      }
      const subs = monthlyData.value.subject_missing_distribution.map(s => s.subject_name);
      const counts = monthlyData.value.subject_missing_distribution.map(s => s.missing_count);

      monthlyMissingChartInstance.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: '{b}: 遗漏未完成 {c} 次'
        },
        grid: { top: 25, right: 15, bottom: 25, left: 35 },
        xAxis: {
          type: 'category',
          data: subs,
          axisLabel: { fontSize: 11, color: '#475569' },
          axisLine: { lineStyle: { color: '#e2e8f0' } }
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { fontSize: 10, color: '#64748b' },
          splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
        },
        series: [
          {
            name: '未完成次数',
            type: 'bar',
            data: counts,
            barWidth: '40%',
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#f59e0b' },
                { offset: 1, color: '#fbbf24' }
              ]),
              borderRadius: [4, 4, 0, 0]
            },
            label: {
              show: true,
              position: 'top',
              fontSize: 11,
              color: '#d97706'
            }
          }
        ]
      }, true);
    }
  });
};

const handleSettingsResize = () => {
  if (monthlyTrendChartInstance) monthlyTrendChartInstance.resize();
  if (monthlyMissingChartInstance) monthlyMissingChartInstance.resize();
};

const formatTime = (isoString) => {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${m}-${day} ${h}:${min}`;
  } catch (e) {
    return isoString;
  }
};

onMounted(() => {
  window.addEventListener('resize', handleSettingsResize);
  if (isUnlocked.value) {
    fetchSubjects();
    fetchNotificationConfig();
    fetchPaperHistory();
    fetchMonthlyAnalytics();
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', handleSettingsResize);
  if (monthlyTrendChartInstance) monthlyTrendChartInstance.dispose();
  if (monthlyMissingChartInstance) monthlyMissingChartInstance.dispose();
});
</script>


<style scoped>
.settings-view {
  min-height: 100vh;
  background-color: var(--st-bg-page, #f8fafc);
  padding-bottom: 2rem;
}

.settings-container {
  padding: 12px 14px 60px;
  max-width: 600px;
  margin: 0 auto;
}

.settings-top-notice {
  margin-bottom: 14px;
  border-radius: var(--st-radius-sm, 8px);
}

.pin-gate-card {
  margin: 2.5rem auto;
  max-width: 440px;
  background: var(--st-bg-card, #ffffff);
  border-radius: var(--st-radius-md, 14px);
  padding: 2.5rem 1.5rem;
  text-align: center;
  border: 1px solid var(--st-border, #f1f5f9);
  box-shadow: var(--st-shadow-card);
}

.gate-icon-circle {
  width: 60px;
  height: 60px;
  background: var(--st-warning-light, #fffbeb);
  border-radius: var(--st-radius-full, 9999px);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.25rem;
}

.pin-gate-card h3 {
  margin: 0 0 0.5rem;
  font-size: 17px;
  font-weight: 700;
  color: var(--st-text-primary, #0f172a);
}

.gate-tip {
  font-size: 13px;
  color: var(--st-text-secondary, #64748b);
  margin-bottom: 1.5rem;
}

.pin-field {
  background: var(--st-bg-page, #f8fafc);
  border-radius: var(--st-radius-sm, 8px);
  border: 1px solid var(--st-border, #e2e8f0);
  font-size: 1.2rem;
  letter-spacing: 4px;
}

.channel-config-box {
  background: #f8fafc;
  margin: 10px 0;
  padding: 12px;
  border-radius: var(--st-radius-sm, 8px);
  border: 1px solid var(--st-border, #e2e8f0);
}

.channel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.channel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--st-text-primary, #0f172a);
}

.channel-hint {
  font-size: 11px;
  color: var(--st-text-secondary, #64748b);
  line-height: 1.4;
  margin-top: 6px;
  padding-left: 4px;
}

.notif-action-row {
  padding: 14px 0 0;
}

.history-list-box {
  padding: 8px 0 6px;
}

.history-card {
  background: #f8fafc;
  border: 1px solid var(--st-border, #e2e8f0);
  border-radius: var(--st-radius-sm, 10px);
  padding: 12px 14px;
  margin-bottom: 10px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.history-card:last-child {
  margin-bottom: 0;
}

.history-card:active {
  background: #f1f5f9;
}

.history-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.history-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--st-text-primary, #0f172a);
}

.history-card-desc {
  font-size: 12px;
  color: var(--st-text-secondary, #64748b);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.history-card-desc .dot {
  color: #cbd5e1;
}

.history-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px dashed var(--st-border, #e2e8f0);
}

.history-time {
  font-size: 11px;
  color: var(--st-text-muted, #94a3b8);
}

.history-empty-box {
  padding: 8px 0 16px;
}

.monthly-analytics-box {
  padding: 10px 0 4px;
}

.monthly-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.monthly-title-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.monthly-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--st-text-primary, #0f172a);
}

.month-stepper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.current-month-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--st-primary, #2563eb);
}

.monthly-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}

.monthly-stat-item {
  background: #f8fafc;
  border: 1px solid var(--st-border, #e2e8f0);
  border-radius: var(--st-radius-sm, 8px);
  padding: 8px 6px;
  text-align: center;
  display: flex;
  flex-direction: column;
}

.m-stat-val {
  font-size: 15px;
  font-weight: 700;
  color: var(--st-text-primary, #0f172a);
}

.m-stat-label {
  font-size: 10px;
  color: var(--st-text-secondary, #64748b);
  margin-top: 2px;
}

.text-primary {
  color: var(--st-primary, #2563eb) !important;
}

.text-succ {
  color: var(--st-success, #10b981) !important;
}

.monthly-chart-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--st-text-secondary, #475569);
  margin-bottom: 4px;
}

.monthly-echarts-container {
  width: 100%;
  height: 180px;
}

.monthly-echarts-container.bar-height {
  height: 170px;
}

.monthly-perfect-tip {
  font-size: 11px;
  color: #166534;
  background: #f0fdf4;
  padding: 10px 12px;
  border-radius: var(--st-radius-sm, 8px);
  border: 1px solid #bbf7d0;
  text-align: center;
  margin-top: 6px;
}
</style>

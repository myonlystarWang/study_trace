<template>
  <div class="settings-view">
    <van-nav-bar title="家长管理视图" left-arrow @click-left="$router.push('/')" />

    <!-- 门禁口令验证卡片 -->
    <div class="pin-gate-card" v-if="!isUnlocked">
      <div class="gate-icon">🔒</div>
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
      <van-notice-bar left-icon="info-o" text="已进入家长管理空间，可设置推送提醒、管理学科与备份。" />

      <!-- 每日提醒与通知渠道配置 -->
      <van-cell-group inset title="每日提醒与多渠道推送设置" style="margin-top: 1rem;">
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
            <span class="channel-title">🟢 微信公众号推送 (PushPlus 首选推荐)</span>
            <span class="channel-badge free">实名免费 200条/天</span>
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
          <div class="channel-hint">
            💡 提示：微信关注“PushPlus推送加”公众号，<b>必须完成手机号实名认证</b>方可享有 200 条/天免费额度；未实名接口将返回 905。
          </div>
        </div>

        <!-- Server酱 配置 -->
        <div class="channel-config-box">
          <div class="channel-header">
            <span class="channel-title">🟡 Server酱 (Turbo版 备选)</span>
            <span class="channel-badge warning">免费限 5条/天</span>
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
            <span class="channel-title">🍎 iOS Bark 推送 (全家 iPhone 首选)</span>
            <span class="channel-badge free">无需 HTTPS 免账号</span>
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
            <span class="channel-title">🤖 群机器人 Webhook (企微 / 钉钉 / 飞书)</span>
            <span class="channel-badge free">100% 免费零门槛</span>
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
            style="margin-top: 10px;"
            :loading="sendingSummary"
            @click="handleSendSummaryNow"
          >
            🚀 立即生成并发送今日汇总 (即时推送快照)
          </van-button>
        </div>
      </van-cell-group>

      <!-- 数据安全与备份 -->
      <van-cell-group inset title="数据安全与一键备份" style="margin-top: 1.5rem;">
        <van-cell title="全站数据导出备份" is-link label="包含 SQLite 数据库与所有错题高清原图" @click="handleExportBackup" />
        <van-cell title="从备份 Zip 包还原" label="恢复前将自动在本地创建数据快照">
          <template #right-icon>
            <van-uploader :after-read="handleImportBackup" accept=".zip">
              <van-button size="small" type="primary">选择并还原</van-button>
            </van-uploader>
          </template>
        </van-cell>
      </van-cell-group>
      <div class="security-warning-card">
        ⚠️ <b>安全须知</b>：导出的备份 Zip 压缩包包含本地 SQLite 数据库（含已配置的通知 Token 与 Key 等敏感凭据），请妥善保存在私密设备中，<b>切勿外传或公开发布</b>。
      </div>

      <!-- 学科设置 -->
      <van-cell-group inset title="预置初一学科管理" style="margin-top: 1rem;">
        <van-cell
          v-for="sub in subjects"
          :key="sub.id"
          :title="sub.name"
          :value="`${sub.full_score} 分`"
        />
        <van-cell title="新增自定义学科" is-link @click="showAddSubject = true" />
      </van-cell-group>

      <!-- 口令管理 -->
      <van-cell-group inset title="安全设置" style="margin-top: 1rem;">
        <van-cell title="修改管理口令" is-link @click="showChangePin = true" />
        <van-cell title="退出管理视图" is-link @click="lockSettings" />
      </van-cell-group>
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
import { ref, onMounted } from 'vue';
import { showToast, showConfirmDialog, showDialog } from 'vant';
import { settingsApi, backupApi, notificationApi } from '../api';

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
        title: '✅ 测试发送成功',
        message: res.data.message || '请查看手机个人微信或 App 通知的弹出卡片！',
        confirmButtonText: '好'
      });
    } else {
      showDialog({
        title: '❌ 测试发送未成功',
        message: res.data.message || '请检查配置或网络',
        confirmButtonText: '知道了'
      });
    }
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '测试请求失败';
    showDialog({
      title: '❌ 测试接口异常',
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
          title: '🎉 发送成功',
          message: '今日作业与复习快报已成功送达！',
          confirmButtonText: '确定'
        });
      } else {
        showDialog({
          title: '⚠️ 发送完成但部分失败',
          message: '部分渠道发送失败，请在上方检查各通道配置。',
          confirmButtonText: '知道了'
        });
      }
    } catch (e) {
      showToast('发送接口失败');
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

onMounted(() => {
  if (isUnlocked.value) {
    fetchSubjects();
    fetchNotificationConfig();
  }
});
</script>

<style scoped>
.settings-view {
  min-height: 100vh;
  background-color: #f7f8fa;
  padding-bottom: 2rem;
}

.pin-gate-card {
  margin: 3rem 1.5rem;
  background: white;
  border-radius: 16px;
  padding: 2.5rem 1.5rem;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.gate-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.pin-gate-card h3 {
  margin: 0 0 0.5rem;
  color: #1a1a1a;
}

.gate-tip {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 1.5rem;
}

.pin-field {
  background: #f7f8fa;
  border-radius: 8px;
  font-size: 1.2rem;
  letter-spacing: 4px;
}

.channel-config-box {
  background: #f9fafb;
  margin: 10px 16px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid #f0f0f0;
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
  color: #1f2937;
}

.channel-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
}

.channel-badge.free {
  background: #dcfce7;
  color: #15803d;
}

.channel-badge.warning {
  background: #fef3c7;
  color: #b45309;
}

.channel-hint {
  font-size: 11px;
  color: #6b7280;
  line-height: 1.4;
  margin-top: 6px;
  padding-left: 4px;
}

.notif-action-row {
  padding: 16px;
}

.security-warning-card {
  margin: 10px 16px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 11px;
  color: #92400e;
  line-height: 1.5;
}
</style>

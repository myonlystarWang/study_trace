<template>
  <div class="settings-view">
    <van-nav-bar title="家长管理视图" />

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
      <van-notice-bar left-icon="info-o" text="已进入家长管理空间，可管理学科、导出备份或修改口令。" />

      <!-- 数据安全与备份 -->
      <van-cell-group inset title="数据安全与一键备份" style="margin-top: 1rem;">
        <van-cell title="全站数据导出备份" is-link label="包含 SQLite 数据库与所有错题高清原图" @click="handleExportBackup" />
        <van-cell title="从备份 Zip 包还原" label="恢复前将自动在本地创建数据快照">
          <template #right-icon>
            <van-uploader :after-read="handleImportBackup" accept=".zip">
              <van-button size="small" type="primary">选择并还原</van-button>
            </van-uploader>
          </template>
        </van-cell>
      </van-cell-group>

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
import { showToast, showConfirmDialog } from 'vant';
import { settingsApi, backupApi } from '../api';

const isUnlocked = ref(sessionStorage.getItem('parent_unlocked') === 'true');
const inputPin = ref('');
const verifying = ref(false);
const subjects = ref([]);

const showAddSubject = ref(false);
const newSub = ref({ name: '', full_score: 100 });

const showChangePin = ref(false);
const pinForm = ref({ oldPin: '', newPin: '' });

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
    showToast({ message: '解锁成功', icon: 'success' });
    fetchSubjects();
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
    showToast({ message: '口令修改成功', icon: 'success' });
    pinForm.value = { oldPin: '', newPin: '' };
  } catch (e) {
    showToast(e.response?.data?.detail || '修改失败');
  }
};

onMounted(() => {
  if (isUnlocked.value) {
    fetchSubjects();
  }
});
</script>

<style scoped>
.settings-view {
  padding-bottom: 6rem;
  background: #f8fafc;
  min-height: 100vh;
}

.pin-gate-card {
  margin: 3rem 1.5rem;
  background: white;
  padding: 2.5rem 1.5rem;
  border-radius: 20px;
  box-shadow: 0 4px 25px rgba(0, 0, 0, 0.05);
  text-align: center;
}

.gate-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.pin-gate-card h3 {
  color: #0f172a;
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
}

.gate-tip {
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

.pin-field {
  background: #f1f5f9;
  border-radius: 12px;
  font-size: 1.1rem;
  text-align: center;
}
</style>

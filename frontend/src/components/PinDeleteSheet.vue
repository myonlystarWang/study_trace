<template>
  <van-popup v-model:show="isVisible" position="bottom" round class="bottom-sheet-modal">
    <div class="pin-sheet">
      <div class="pin-sheet-handle" />
      <div class="pin-sheet-icon"><van-icon name="lock" /></div>
      <h2>确认管理身份</h2>
      <p>{{ message }}</p>
      <van-field v-model="pin" type="password" inputmode="numeric" maxlength="6" placeholder="请输入管理口令" class="pin-field" />
      <van-button block round type="primary" :loading="loading" @click="verify">继续</van-button>
    </div>
  </van-popup>
</template>

<script setup>
import { computed, ref } from 'vue';
import { showToast } from 'vant';
import { settingsApi } from '../api';

const props = defineProps({ modelValue: Boolean, message: { type: String, default: '删除后无法恢复。请输入管理口令后继续。' } });
const emit = defineEmits(['update:modelValue', 'verified']);
const pin = ref('');
const loading = ref(false);
const isVisible = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) });

const verify = async () => {
  if (!pin.value) return showToast('请输入管理口令');
  loading.value = true;
  try {
    await settingsApi.verifyPin(pin.value);
    sessionStorage.setItem('parent_pin', pin.value);
    sessionStorage.setItem('parent_unlocked', 'true');
    emit('verified');
    emit('update:modelValue', false);
    pin.value = '';
  } catch (error) {
    showToast(error.response?.data?.detail || '验证失败');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.pin-sheet { padding: var(--st-space-3) var(--st-space-5) calc(var(--st-space-6) + env(safe-area-inset-bottom, 0px)); text-align: center; background: var(--st-bg-card); }
.pin-sheet-handle { width: 36px; height: 4px; margin: 0 auto var(--st-space-5); border-radius: var(--st-radius-full); background: var(--st-border-bold); }
.pin-sheet-icon { display: grid; width: 44px; height: 44px; margin: 0 auto var(--st-space-3); place-items: center; border-radius: var(--st-radius-md); background: var(--st-warning-light); color: var(--st-warning-dark); font-size: var(--st-font-xl); }
.pin-sheet h2 { margin: 0; color: var(--st-text-primary); font-size: var(--st-font-xl); }.pin-sheet p { margin: var(--st-space-2) auto var(--st-space-5); color: var(--st-text-secondary); font-size: var(--st-font-sm); line-height: var(--st-leading-normal); max-width: 280px; }
.pin-field { margin-bottom: var(--st-space-4); border: 1px solid var(--st-border); border-radius: var(--st-radius-md); background: var(--st-bg-subtle); text-align: center; }
</style>

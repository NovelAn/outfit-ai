<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { ref } from "vue";
import { api, messageOf } from "@/api/client";
import type { Profile } from "@/api/types";

const profile = ref<Profile>();
const loading = ref(true);
const saving = ref(false);
const refreshing = ref(false);
const error = ref("");
const keywords = ref("");
const preferredColors = ref("");
const preferredStyles = ref("");
const avoids = ref("");
const occasions = ref("");

function join(values: string[]) {
  return values.join("、");
}

function split(value: string) {
  return value
    .split(/[、,，]/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function fillDraft(value: Profile) {
  profile.value = value;
  keywords.value = join(value.style_keywords);
  preferredColors.value = join(value.preferred_colors);
  preferredStyles.value = join(value.preferred_styles);
  avoids.value = join(value.avoids);
  occasions.value = join(value.occasions);
}

async function loadProfile() {
  loading.value = true;
  error.value = "";
  try {
    fillDraft(await api.profile());
  } catch (cause) {
    error.value = messageOf(cause);
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!profile.value) return;
  saving.value = true;
  try {
    const saved = await api.saveProfile({
      ...profile.value,
      style_keywords: split(keywords.value),
      preferred_colors: split(preferredColors.value),
      preferred_styles: split(preferredStyles.value),
      avoids: split(avoids.value),
      occasions: split(occasions.value),
    });
    fillDraft(saved);
    uni.showToast({ title: "风格档案已保存", icon: "success" });
  } catch (cause) {
    uni.showToast({ title: messageOf(cause), icon: "none" });
  } finally {
    saving.value = false;
  }
}

async function refreshMemo() {
  refreshing.value = true;
  try {
    await api.refreshTasteMemo();
    uni.showToast({ title: "造型师正在整理新反馈", icon: "none" });
  } catch (cause) {
    uni.showToast({ title: messageOf(cause), icon: "none" });
  } finally {
    refreshing.value = false;
  }
}

onShow(loadProfile);
</script>

<template>
  <view class="page profile-page">
    <view class="eyebrow">Style DNA</view>
    <text class="display-title">不是风格标签，<br />是你穿衣的脉络。</text>
    <view class="lede">这些信息会和每次反馈一起交给造型师。保留真实偏好，也留一点变化的空间。</view>

    <view v-if="error" class="error-banner">{{ error }}</view>
    <view v-if="loading" class="profile-skeleton card">
      <view v-for="index in 7" :key="index" class="skeleton-line"></view>
    </view>

    <template v-else-if="profile">
      <view class="archive-heading">
        <view class="archive-line"></view>
        <text>基础档案</text>
        <view class="archive-line"></view>
      </view>

      <view class="profile-form card">
        <label class="field first-field">
          <text class="field-label">常住城市</text>
          <input v-model="profile.city" class="input" placeholder="定位失败时用于天气，例如上海" />
        </label>
        <view class="two-columns">
          <label class="field">
            <text class="field-label">色彩季节</text>
            <input v-model="profile.color_season" class="input" placeholder="例如：深秋" />
          </label>
          <label class="field">
            <text class="field-label">冷暖倾向</text>
            <input v-model="profile.color_undertone" class="input" placeholder="冷 / 暖 / 中性" />
          </label>
        </view>
        <label class="field">
          <text class="field-label">风格关键词</text>
          <input v-model="keywords" class="input" placeholder="克制、利落、质感（用顿号分隔）" />
        </label>
        <label class="field">
          <text class="field-label">偏好颜色</text>
          <input v-model="preferredColors" class="input" placeholder="海军蓝、炭灰、米白" />
        </label>
        <label class="field">
          <text class="field-label">偏好风格</text>
          <input v-model="preferredStyles" class="input" placeholder="极简、经典、英伦" />
        </label>
        <label class="field">
          <text class="field-label">避免</text>
          <input v-model="avoids" class="input" placeholder="高饱和撞色、过度宽松…" />
        </label>
        <label class="field">
          <text class="field-label">常见场合</text>
          <input v-model="occasions" class="input" placeholder="通勤、差旅、周末" />
        </label>
        <label class="field">
          <text class="field-label">当地气候</text>
          <input v-model="profile.climate" class="input" placeholder="湿润、四季分明…" />
        </label>
      </view>

      <view class="archive-heading memo-heading">
        <view class="archive-line"></view>
        <text>品味备忘录</text>
        <view class="archive-line"></view>
      </view>
      <view class="memo-card card">
        <view class="memo-meta">
          <text>造型师对你的理解</text>
          <text v-if="profile.feedback_since_refresh">
            {{ profile.feedback_since_refresh }} 条新反馈待消化
          </text>
        </view>
        <textarea
          v-model="profile.taste_memo"
          class="memo-textarea"
          maxlength="-1"
          placeholder="还没有品味备忘录。先保存你的风格档案，穿几次并留下反馈。"
        />
        <button
          class="button-quiet refresh-button"
          :disabled="refreshing"
          @tap="refreshMemo"
        >
          {{ refreshing ? "正在刷新…" : "刷新我的品味" }}
        </button>
      </view>

      <view class="sticky-action">
        <button class="button" :disabled="saving" @tap="save">
          {{ saving ? "保存中…" : "保存风格档案" }}
        </button>
      </view>
    </template>
  </view>
</template>

<style scoped>
.archive-heading {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  margin: 30px 0 14px;
  color: #6e665c;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.archive-line {
  height: 1px;
  background: #e5ded2;
}

.profile-form {
  padding: 20px;
}

.first-field {
  margin-top: 0;
}

.two-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.memo-heading {
  margin-top: 34px;
}

.memo-card {
  position: relative;
  padding: 20px;
  overflow: hidden;
}

.memo-card::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 4px;
  background: #c76a43;
  content: "";
}

.memo-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #6e665c;
  font-size: 11px;
}

.memo-textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 220px;
  margin-top: 14px;
  padding: 0;
  color: #1f1b16;
  background: transparent;
  font-family: "Songti SC", "STSong", serif;
  font-size: 17px;
  line-height: 1.8;
}

.refresh-button {
  width: 100%;
  margin-top: 16px;
}

.profile-skeleton {
  margin-top: 28px;
  padding: 20px;
}

.skeleton-line {
  height: 48px;
  margin-top: 14px;
  background: #e8e0d5;
  border-radius: 12px;
}

.skeleton-line:first-child {
  margin-top: 0;
}
</style>

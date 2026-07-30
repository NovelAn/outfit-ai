<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { ref } from "vue";
import { api, messageOf } from "@/api/client";
import type { Profile } from "@/api/types";

const profile = ref<Profile>();
const wardrobeCount = ref(0);
const inspirationCount = ref(0);
const historyCount = ref(0);
const keywords = ref("");
const preferredColors = ref("");
const avoids = ref("");
const loading = ref(true);
const saving = ref(false);
const refreshing = ref(false);
const error = ref("");

function split(value: string) {
  return value
    .split(/[、,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function fill(value: Profile) {
  profile.value = value;
  keywords.value = value.style_keywords.join("、");
  preferredColors.value = value.preferred_colors.join("、");
  avoids.value = value.avoids.join("、");
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [currentProfile, items, references, history] = await Promise.all([
      api.profile(),
      api.items(),
      api.styleReferences(),
      api.history(),
    ]);
    fill(currentProfile);
    wardrobeCount.value = items.length;
    inspirationCount.value = references.filter((item) => item.status === "ready").length;
    historyCount.value = history.length;
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
      avoids: split(avoids.value),
    });
    fill(saved);
    uni.showToast({ title: "Style DNA 已保存", icon: "success" });
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
    uni.showToast({ title: "正在整理近期反馈", icon: "none" });
  } catch (cause) {
    uni.showToast({ title: messageOf(cause), icon: "none" });
  } finally {
    refreshing.value = false;
  }
}

function openHistory() {
  uni.navigateTo({ url: "/pages/history/index" });
}

onShow(load);
</script>

<template>
  <view class="me-page">
    <view class="app-header">
      <text class="brand">Outfit-AI</text>
      <text class="header-note">MY STYLE DNA</text>
    </view>

    <view class="me-main">
      <view v-if="error" class="error-banner">{{ error }}</view>
      <view v-if="loading" class="profile-loading">
        <view v-for="index in 4" :key="index" class="loading-card"></view>
      </view>

      <template v-else-if="profile">
        <view class="identity-card">
          <view class="monogram">AI</view>
          <view class="identity-copy">
            <text class="identity-title">我的个人穿搭基因</text>
            <text>长期参考与真实反馈持续更新</text>
          </view>
          <text class="learning-badge">LEARNING</text>
        </view>

        <view class="stats-row">
          <view>
            <text>{{ wardrobeCount }}</text>
            <text>真实衣物</text>
          </view>
          <view>
            <text>{{ inspirationCount }}</text>
            <text>长期参考</text>
          </view>
          <view>
            <text>{{ historyCount }}</text>
            <text>搭配记录</text>
          </view>
        </view>

        <view class="profile-card palette-card">
          <view class="card-heading">
            <text>核心穿搭色板</text>
            <text>STYLE DNA</text>
          </view>
          <view class="palette-row">
            <view
              v-for="(color, index) in profile.palette.slice(0, 5)"
              :key="`${color}-${index}`"
              class="palette-swatch"
              :style="{ backgroundColor: color }"
            >
              <text>{{ color }}</text>
            </view>
            <view v-if="!profile.palette.length" class="palette-empty">
              上传参考 Look 后自动沉淀
            </view>
          </view>
        </view>

        <view class="profile-card">
          <view class="card-heading">
            <text>风格关键词</text>
            <text>EDITABLE</text>
          </view>
          <input v-model="keywords" class="editor-line" placeholder="极简、质感、利落" />
          <label class="field-row">
            <text>偏好色</text>
            <input v-model="preferredColors" placeholder="海军蓝、燕麦色" />
          </label>
          <label class="field-row">
            <text>避免</text>
            <input v-model="avoids" placeholder="明显 logo、高饱和撞色" />
          </label>
          <label class="field-row">
            <text>常住城市</text>
            <input v-model="profile.city" placeholder="用于天气，例如上海" />
          </label>
        </view>

        <view class="profile-card memo-card">
          <view class="card-heading">
            <view>
              <text>AI 品味学习备忘录</text>
              <text v-if="profile.feedback_since_refresh" class="feedback-count">
                {{ profile.feedback_since_refresh }} 条新反馈
              </text>
            </view>
            <button class="small-action" :disabled="refreshing" @tap="refreshMemo">
              {{ refreshing ? "整理中" : "刷新" }}
            </button>
          </view>
          <textarea
            v-model="profile.taste_memo"
            class="memo-input"
            maxlength="-1"
            placeholder="随着参考 Look 和真实反馈积累，这里会形成长期品味理解。"
          />
        </view>

        <button class="menu-row" @tap="openHistory">
          <view>
            <text class="menu-title">每日穿搭推荐历史</text>
            <text class="menu-note">查看真正穿过、喜欢或跳过的搭配</text>
          </view>
          <text>{{ historyCount }} 方案　›</text>
        </button>

        <button class="save-button" :disabled="saving" @tap="save">
          {{ saving ? "保存中…" : "保存 Style DNA" }}
        </button>
      </template>
    </view>
  </view>
</template>

<style scoped>
.me-page {
  min-height: 100vh;
  padding-bottom: calc(94px + env(safe-area-inset-bottom));
  background: #fbf9f4;
  color: #162839;
}

.app-header {
  position: sticky;
  z-index: 5;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 64px;
  padding: env(safe-area-inset-top) 20px 0;
  background: rgba(251, 249, 244, 0.96);
  border-bottom: 1px solid #e4e2dd;
}

.brand {
  font-family: Georgia, "Songti SC", serif;
  font-size: 17px;
  font-weight: 700;
}

.header-note {
  color: #74777d;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.me-main {
  max-width: 520px;
  margin: 0 auto;
  padding: 18px 16px 40px;
}

.identity-card,
.stats-row,
.profile-card,
.menu-row {
  box-sizing: border-box;
  width: 100%;
  background: #fff;
  border: 1px solid #e4e2dd;
}

.identity-card {
  display: grid;
  grid-template-columns: 48px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 14px;
}

.monogram {
  width: 48px;
  height: 48px;
  color: #fff;
  background: #162839;
  font-family: Georgia, serif;
  font-size: 17px;
  font-style: italic;
  font-weight: 700;
  line-height: 48px;
  text-align: center;
}

.identity-title,
.identity-copy > text:last-child {
  display: block;
}

.identity-title {
  font-size: 13px;
  font-weight: 700;
}

.identity-copy > text:last-child {
  margin-top: 4px;
  color: #74777d;
  font-size: 10px;
}

.learning-badge {
  padding: 4px 7px;
  color: #fff;
  background: #9a442a;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 12px;
}

.stats-row view {
  padding: 16px 8px;
  text-align: center;
  border-right: 1px solid #e4e2dd;
}

.stats-row view:last-child {
  border-right: 0;
}

.stats-row text {
  display: block;
}

.stats-row text:first-child {
  font-family: Georgia, "Songti SC", serif;
  font-size: 22px;
  font-weight: 700;
}

.stats-row text:last-child {
  margin-top: 3px;
  color: #74777d;
  font-size: 9px;
}

.profile-card {
  margin-top: 12px;
  padding: 16px;
}

.card-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  font-size: 11px;
  font-weight: 700;
}

.card-heading > text:last-child {
  color: #9a442a;
  font-size: 8px;
  letter-spacing: 0.1em;
}

.palette-row {
  display: flex;
  gap: 8px;
  overflow: hidden;
}

.palette-swatch {
  position: relative;
  width: 54px;
  height: 72px;
  flex: 0 0 auto;
  border: 1px solid #e4e2dd;
}

.palette-swatch text {
  position: absolute;
  right: 2px;
  bottom: 2px;
  left: 2px;
  overflow: hidden;
  padding: 3px;
  color: #162839;
  background: rgba(255, 255, 255, 0.82);
  font-size: 7px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.palette-empty {
  width: 100%;
  padding: 22px 8px;
  color: #74777d;
  background: #f5f3ee;
  font-size: 11px;
  text-align: center;
}

.editor-line {
  box-sizing: border-box;
  width: 100%;
  height: 46px;
  padding: 0 12px;
  color: #162839;
  background: #f5f3ee;
  border: 1px solid #e4e2dd;
  font-size: 12px;
}

.field-row {
  display: grid;
  grid-template-columns: 72px 1fr;
  align-items: center;
  min-height: 48px;
  border-bottom: 1px solid #e4e2dd;
  font-size: 11px;
}

.field-row input {
  width: 100%;
  color: #162839;
  text-align: right;
}

.feedback-count {
  margin-left: 6px;
  color: #9a442a;
  font-size: 9px;
}

.small-action {
  min-height: 36px;
  margin: 0;
  padding: 0 12px;
  color: #9a442a;
  background: transparent;
  border: 1px solid #d8b7a6;
  border-radius: 999px;
  font-size: 10px;
  line-height: 34px;
}

.small-action::after,
.menu-row::after,
.save-button::after {
  border: 0;
}

.memo-input {
  box-sizing: border-box;
  width: 100%;
  min-height: 180px;
  padding: 14px;
  color: #162839;
  background: #f8f7f3;
  font-family: "Songti SC", "STSong", serif;
  font-size: 14px;
  line-height: 1.8;
}

.menu-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 72px;
  margin-top: 12px;
  padding: 14px 16px;
  color: #162839;
  border-radius: 0;
  text-align: left;
}

.menu-title,
.menu-note {
  display: block;
}

.menu-title {
  font-size: 12px;
  font-weight: 700;
}

.menu-note {
  margin-top: 4px;
  color: #74777d;
  font-size: 9px;
}

.menu-row > text {
  color: #74777d;
  font-size: 10px;
}

.save-button {
  width: 100%;
  min-height: 48px;
  margin-top: 16px;
  color: #fff;
  background: #162839;
  border-radius: 0;
  font-size: 12px;
  font-weight: 700;
  line-height: 48px;
}

.profile-loading {
  display: grid;
  gap: 12px;
}

.loading-card {
  height: 120px;
  background: #ece9e2;
}

.error-banner {
  margin: 0 0 14px;
}
</style>

<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { ref } from "vue";
import { api, messageOf } from "@/api/client";
import type { Profile } from "@/api/types";
import { chooseImages } from "@/utils/media";

const profile = ref<Profile>();
const loading = ref(true);
const saving = ref(false);
const refreshing = ref(false);
const drafting = ref(false);
const error = ref("");
const keywords = ref("");
const preferredColors = ref("");
const preferredStyles = ref("");
const avoids = ref("");
const occasions = ref("");
const styleBrief = ref("");
const sampleImages = ref<string[]>([]);
const draftReady = ref(false);
const memoNotice = ref("");

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

function currentProfile(): Profile | undefined {
  if (!profile.value) return undefined;
  return {
    ...profile.value,
    style_keywords: split(keywords.value),
    preferred_colors: split(preferredColors.value),
    preferred_styles: split(preferredStyles.value),
    avoids: split(avoids.value),
    occasions: split(occasions.value),
  };
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
  const payload = currentProfile();
  if (!payload) return;
  saving.value = true;
  try {
    const saved = await api.saveProfile(payload);
    fillDraft(saved);
    draftReady.value = false;
    uni.showToast({ title: "风格档案已保存", icon: "success" });
  } catch (cause) {
    uni.showToast({ title: messageOf(cause), icon: "none" });
  } finally {
    saving.value = false;
  }
}

async function chooseSamples() {
  try {
    sampleImages.value = await chooseImages(3);
  } catch (cause) {
    const message = messageOf(cause);
    if (!message.includes("cancel")) uni.showToast({ title: message, icon: "none" });
  }
}

async function generateDraft() {
  const payload = currentProfile();
  if (!payload || !styleBrief.value.trim()) {
    uni.showToast({ title: "先写下你喜欢怎么穿", icon: "none" });
    return;
  }
  drafting.value = true;
  try {
    const result = await api.draftStyleDna({
      ...payload,
      taste_memo: styleBrief.value.trim(),
    });
    fillDraft(result.draft);
    draftReady.value = true;
    uni.showToast({ title: "草稿已生成，请检查", icon: "none" });
  } catch (cause) {
    uni.showToast({ title: messageOf(cause), icon: "none" });
  } finally {
    drafting.value = false;
  }
}

async function refreshMemo() {
  refreshing.value = true;
  try {
    await api.refreshTasteMemo();
    memoNotice.value = "刷新任务已开始。处理需要一点时间，稍后点“重新读取结果”。";
    uni.showToast({ title: "造型师正在整理新反馈", icon: "none" });
  } catch (cause) {
    uni.showToast({ title: messageOf(cause), icon: "none" });
  } finally {
    refreshing.value = false;
  }
}

async function reloadMemo() {
  await loadProfile();
  memoNotice.value = "";
  uni.showToast({ title: "已重新读取当前结果", icon: "none" });
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
      <view class="onboarding-card card">
        <view class="onboarding-title">先写一版文字品味草稿</view>
        <view class="onboarding-copy">
          当前只会把你的文字和已填写的结构化偏好交给 AI，生成品味备忘录草稿。样例图仅在本机预览，不会发送给 AI。
        </view>
        <view v-if="sampleImages.length" class="sample-grid">
          <image
            v-for="path in sampleImages"
            :key="path"
            class="sample-image"
            :src="path"
            mode="aspectFill"
          />
        </view>
        <button class="button-quiet sample-button" @tap="chooseSamples">
          {{ sampleImages.length ? "重新选择样例图" : "选择样例图（最多 3 张）" }}
        </button>
        <label class="field">
          <text class="field-label">你喜欢怎么穿</text>
          <textarea
            v-model="styleBrief"
            class="textarea brief-textarea"
            maxlength="500"
            placeholder="例如：工作日想利落但不要太正式，偏爱深蓝、灰和米白，不喜欢明显 logo。"
          />
        </label>
        <button class="button draft-button" :disabled="drafting" @tap="generateDraft">
          {{ drafting ? "正在生成草稿…" : "生成文字品味草稿" }}
        </button>
        <view class="draft-caveat">
          当前服务会先暂存文字草稿；结构化偏好仍由你编辑，点击页面底部“保存风格档案”完成确认。
        </view>
      </view>

      <view v-if="draftReady" class="draft-ready" role="status">
        文字品味草稿已写入“品味备忘录”。下面的结构化偏好不会由样例图自动生成，请逐项编辑后保存。
      </view>

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
        <view v-if="memoNotice" class="memo-notice" role="status">{{ memoNotice }}</view>
        <button v-if="memoNotice" class="button-quiet reload-button" @tap="reloadMemo">
          重新读取结果
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
.onboarding-card {
  margin-top: 28px;
  padding: 20px;
}

.onboarding-title {
  font-family: "Songti SC", "STSong", serif;
  font-size: 21px;
  font-weight: 600;
}

.onboarding-copy,
.draft-caveat,
.memo-notice {
  margin-top: 8px;
  color: #5b544b;
  font-size: 12px;
  line-height: 1.6;
}

.sample-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-top: 16px;
}

.sample-image {
  width: 100%;
  height: 116px;
  background: #e8e0d5;
  border-radius: 10px;
}

.sample-button,
.draft-button,
.reload-button {
  width: 100%;
  margin-top: 14px;
}

.brief-textarea {
  min-height: 108px;
}

.draft-ready {
  margin-top: 16px;
  padding: 12px 14px;
  color: #71351f;
  background: #e8d5c8;
  border-radius: 12px;
  font-size: 13px;
}

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
  background: #a64b2a;
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

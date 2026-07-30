<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { computed, ref } from "vue";
import {
  api,
  mediaUrl,
  messageOf,
  uploadStyleReference,
} from "@/api/client";
import type {
  InspirationResult,
  Profile,
  StyleReference,
} from "@/api/types";
import { chooseImages } from "@/utils/media";

type Season = "spring" | "summer" | "autumn" | "winter";

const seasons: { value: Season; label: string }[] = [
  { value: "spring", label: "春" },
  { value: "summer", label: "夏" },
  { value: "autumn", label: "秋" },
  { value: "winter", label: "冬" },
];
const scenes = ["咖啡馆阅读", "周末漫步", "城市通勤", "假日旅行"];

const references = ref<StyleReference[]>([]);
const selectedIds = ref<string[]>([]);
const profile = ref<Profile>();
const season = ref<Season>("autumn");
const scene = ref(scenes[0]);
const styleNote = ref("");
const loading = ref(true);
const uploading = ref(false);
const generating = ref(false);
const error = ref("");
const result = ref<InspirationResult>();
const polling = new Set<string>();

const readyReferences = computed(() =>
  references.value.filter((item) => item.status === "ready"),
);

function toggleReference(id: string) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((value) => value !== id)
    : [...selectedIds.value, id];
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [styleReferences, currentProfile] = await Promise.all([
      api.styleReferences(),
      api.profile(),
    ]);
    references.value = styleReferences;
    profile.value = currentProfile;
    for (const item of styleReferences) {
      if (item.status === "pending" || item.status === "analyzing") void poll(item.id);
    }
  } catch (cause) {
    error.value = messageOf(cause);
  } finally {
    loading.value = false;
  }
}

async function poll(id: string) {
  if (polling.has(id)) return;
  polling.add(id);
  try {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const current = await api.styleReferenceStatus(id);
      const index = references.value.findIndex((item) => item.id === id);
      if (index >= 0) references.value[index] = current;
      else references.value.unshift(current);
      if (current.status === "ready") {
        if (!selectedIds.value.includes(id)) selectedIds.value.push(id);
        return;
      }
      if (current.status === "failed") return;
    }
  } catch (cause) {
    error.value = messageOf(cause);
  } finally {
    polling.delete(id);
  }
}

async function upload() {
  error.value = "";
  try {
    const paths = await chooseImages(6);
    uploading.value = true;
    for (const path of paths) {
      const created = await uploadStyleReference(path);
      references.value.unshift({
        id: created.id,
        image_url: path,
        status: created.status as StyleReference["status"],
        attempt_count: 0,
        analysis: null,
        added_at: new Date().toISOString(),
      });
      void poll(created.id);
    }
  } catch (cause) {
    const message = messageOf(cause);
    if (!message.includes("cancel")) error.value = message;
  } finally {
    uploading.value = false;
  }
}

async function retry(item: StyleReference) {
  try {
    const response = await api.retryStyleReference(item.id);
    item.status = response.status as StyleReference["status"];
    void poll(item.id);
  } catch (cause) {
    error.value = messageOf(cause);
  }
}

async function generate() {
  generating.value = true;
  error.value = "";
  try {
    result.value = await api.generateInspiration({
      reference_ids: selectedIds.value,
      style_note: styleNote.value.trim() || undefined,
      season: season.value,
      scene: scene.value,
    });
  } catch (cause) {
    error.value = messageOf(cause);
  } finally {
    generating.value = false;
  }
}

onShow(load);
</script>

<template>
  <view class="inspiration-page">
    <view class="app-header">
      <text class="brand">Outfit-AI</text>
      <text class="header-note">INSPIRATION ARCHIVE</text>
    </view>

    <view class="inspiration-main">
      <view class="archive-heading">
        <view>
          <text class="page-title">长期灵感库</text>
          <text class="page-copy">这些心仪的瞬间，正在让 AI 越来越懂你</text>
        </view>
        <text class="archive-count">{{ readyReferences.length }} LOOKS</text>
      </view>

      <scroll-view scroll-x class="filmstrip">
        <view class="filmstrip-row">
          <button class="upload-frame" :disabled="uploading" @tap="upload">
            <text class="upload-icon">＋</text>
            <text>{{ uploading ? "上传中" : "上传灵感" }}</text>
          </button>
          <view
            v-for="(item, index) in references"
            :key="item.id"
            class="film-frame"
            :class="{ selected: selectedIds.includes(item.id), failed: item.status === 'failed' }"
            :role="item.status === 'ready' ? 'button' : undefined"
            :tabindex="item.status === 'ready' ? 0 : -1"
            @tap="item.status === 'ready' ? toggleReference(item.id) : undefined"
            @keyup.enter="item.status === 'ready' ? toggleReference(item.id) : undefined"
            @keyup.space="item.status === 'ready' ? toggleReference(item.id) : undefined"
          >
            <image :src="mediaUrl(item.image_url)" mode="aspectFill" />
            <view class="frame-caption">
              <text>Archive {{ String(index + 1).padStart(2, "0") }}</text>
              <text v-if="item.status !== 'ready'" class="frame-status">
                {{ item.status === "failed" ? "分析失败" : "正在分析" }}
              </text>
              <text v-else>{{ selectedIds.includes(item.id) ? "本次已选" : "长期参考" }}</text>
            </view>
            <button
              v-if="item.status === 'failed'"
              class="retry-mini"
              @tap.stop="retry(item)"
            >
              重试
            </button>
          </view>
        </view>
      </scroll-view>

      <view class="dna-strip">
        <text class="section-kicker">当前 STYLE DNA</text>
        <view class="dna-tags">
          <text v-for="keyword in (profile?.style_keywords || []).slice(0, 5)" :key="keyword">
            {{ keyword }}
          </text>
          <text v-if="!profile?.style_keywords.length">等待参考 Look 沉淀</text>
        </view>
      </view>

      <view class="generator-sheet">
        <text class="generator-title">AI 穿搭灵感生成</text>
        <view class="field-label">季节</view>
        <view class="season-row">
          <button
            v-for="item in seasons"
            :key="item.value"
            class="season-button"
            :class="{ active: season === item.value }"
            @tap="season = item.value"
          >
            {{ item.label }}
          </button>
        </view>
        <label class="select-line">
          <text>场景</text>
          <picker :range="scenes" :value="scenes.indexOf(scene)" @change="scene = scenes[Number($event.detail.value)]">
            <view>{{ scene }}⌄</view>
          </picker>
        </label>
        <textarea
          v-model="styleNote"
          class="note-input"
          maxlength="500"
          placeholder="可选：例如想尝试更松弛的层次，避免明显 logo"
        />
        <button class="generate-button" :disabled="generating" @tap="generate">
          {{ generating ? "正在生成一张新灵感…" : "✦ 生成灵感" }}
        </button>
        <view class="authenticity-note">AI 灵感图 · 不代表衣橱已有单品</view>
      </view>

      <view v-if="error" class="error-banner">{{ error }}</view>

      <view v-if="generating" class="result-loading">
        <view class="loading-frame"></view>
        <text>正在把 Style DNA 和本次参考 Look 变成一张新画报</text>
      </view>

      <view v-else-if="result" class="result-section">
        <image class="result-image" :src="mediaUrl(result.image_url)" mode="widthFix" />
        <text class="result-title">Look / New Direction</text>
        <text class="result-context">{{ season }} · {{ scene }}</text>
        <view class="authenticity-note">AI 灵感图 · 不代表衣橱已有单品</view>
        <button class="outline-action" @tap="generate">↻ 再生成一个变体</button>
      </view>

      <view v-else-if="!loading" class="empty-result">
        <text class="empty-title">为未来的衣橱留一页。</text>
        <text>灵感图不依赖真实衣物，适合换季、新风格尝试和未来购物判断。</text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.inspiration-page {
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

.header-note,
.archive-count,
.section-kicker {
  color: #74777d;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.inspiration-main {
  max-width: 560px;
  margin: 0 auto;
}

.archive-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 26px 20px 18px;
}

.page-title,
.page-copy {
  display: block;
}

.page-title {
  font-family: "Songti SC", "STSong", serif;
  font-size: 25px;
  font-weight: 700;
}

.page-copy {
  margin-top: 8px;
  color: #74777d;
  font-size: 12px;
}

.archive-count {
  padding-top: 8px;
}

.filmstrip {
  width: 100%;
  padding: 12px 0 28px;
  border-top: 1px solid #e4e2dd;
  border-bottom: 1px solid #e4e2dd;
  white-space: nowrap;
}

.filmstrip-row {
  display: flex;
  gap: 12px;
  padding: 0 20px;
}

.upload-frame,
.film-frame {
  position: relative;
  width: 142px;
  height: 208px;
  flex: 0 0 auto;
  margin: 0;
  padding: 0;
  overflow: hidden;
  background: transparent;
  border: 1px dashed #c4c6cd;
  border-radius: 0;
}

.upload-frame::after,
.film-frame::after,
.retry-mini::after,
.season-button::after,
.generate-button::after,
.outline-action::after {
  border: 0;
}

.upload-frame {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  color: #162839;
  font-size: 11px;
}

.upload-icon {
  font-size: 24px;
  font-weight: 300;
}

.film-frame {
  border-style: solid;
  border-color: transparent;
}

.film-frame.selected {
  border-color: #9a442a;
}

.film-frame.failed {
  opacity: 0.72;
}

.film-frame image {
  width: 100%;
  height: 176px;
}

.frame-caption {
  display: flex;
  justify-content: space-between;
  height: 32px;
  padding: 0 2px;
  color: #74777d;
  font-family: Georgia, "Songti SC", serif;
  font-size: 9px;
  font-style: italic;
  line-height: 28px;
}

.frame-status {
  color: #9a442a;
}

.retry-mini {
  position: absolute;
  top: 8px;
  right: 8px;
  min-height: 32px;
  margin: 0;
  padding: 0 10px;
  color: #fff;
  background: #9a442a;
  border-radius: 0;
  font-size: 10px;
  line-height: 32px;
}

.dna-strip {
  padding: 22px 20px;
  border-bottom: 1px solid #e4e2dd;
}

.section-kicker {
  color: #9a442a;
}

.dna-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 10px;
}

.dna-tags text {
  padding: 6px 12px;
  color: #fff;
  background: #162839;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
}

.dna-tags text:nth-child(n + 2) {
  color: #162839;
  background: #e7e5e0;
}

.generator-sheet {
  margin: 28px 20px;
  padding: 18px;
  background: #f5f3ee;
  border: 1px solid #e4e2dd;
  border-radius: 3px;
}

.generator-title {
  display: block;
  margin-bottom: 18px;
  font-family: Georgia, "Songti SC", serif;
  font-size: 20px;
  font-style: italic;
}

.field-label,
.select-line {
  color: #162839;
  font-size: 11px;
  font-weight: 700;
}

.season-row {
  display: flex;
  margin: 8px 0 18px;
}

.season-button {
  min-width: 48px;
  min-height: 40px;
  margin: 0 4px 0 0;
  color: #162839;
  background: transparent;
  border: 1px solid #c4c6cd;
  border-radius: 0;
  font-size: 12px;
  line-height: 38px;
}

.season-button.active {
  color: #fff;
  background: #162839;
}

.select-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  border-bottom: 1px solid #c4c6cd;
}

.select-line picker {
  min-width: 160px;
  text-align: right;
}

.note-input {
  box-sizing: border-box;
  width: 100%;
  height: 92px;
  margin-top: 14px;
  padding: 12px;
  color: #162839;
  background: #fbf9f4;
  border: 1px solid #e4e2dd;
  font-size: 12px;
  line-height: 1.6;
}

.generate-button {
  width: 100%;
  min-height: 48px;
  margin-top: 14px;
  color: #fff;
  background: #162839;
  border-radius: 0;
  font-size: 12px;
  font-weight: 700;
  line-height: 48px;
}

.error-banner {
  margin: 16px 20px;
}

.result-loading,
.empty-result {
  padding: 24px 20px 62px;
  text-align: center;
}

.loading-frame {
  width: 100%;
  aspect-ratio: 3 / 4;
  background: linear-gradient(100deg, #e8e5de 20%, #f7f5f0 50%, #e8e5de 80%);
  background-size: 240% 100%;
  animation: shimmer 1.4s infinite linear;
}

.result-loading text {
  display: block;
  margin-top: 16px;
  color: #74777d;
  font-family: Georgia, "Songti SC", serif;
  font-size: 13px;
  font-style: italic;
}

.result-section {
  padding: 6px 20px 62px;
}

.result-image {
  display: block;
  width: 100%;
  background: #ece9e2;
  box-shadow: 0 5px 14px rgba(22, 40, 57, 0.11);
}

.result-title,
.result-context {
  display: block;
}

.result-title {
  margin-top: 14px;
  font-family: Georgia, "Songti SC", serif;
  font-size: 17px;
  font-style: italic;
  font-weight: 700;
}

.result-context {
  margin-top: 3px;
  color: #74777d;
  font-size: 10px;
}

.authenticity-note {
  margin-top: 22px;
  padding: 14px;
  color: #74777d;
  text-align: center;
  border-top: 1px solid #e4e2dd;
  border-bottom: 1px solid #e4e2dd;
  font-size: 11px;
  font-style: italic;
}

.outline-action {
  width: 100%;
  min-height: 46px;
  margin-top: 16px;
  color: #9a442a;
  background: transparent;
  border: 1px solid #d8b7a6;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 44px;
}

.empty-title {
  display: block;
  margin-bottom: 10px;
  font-family: "Songti SC", "STSong", serif;
  font-size: 24px;
}

.empty-result > text:last-child {
  color: #74777d;
  font-size: 12px;
  line-height: 1.8;
}

@keyframes shimmer {
  to {
    background-position: -240% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-frame {
    animation: none;
  }
}
</style>

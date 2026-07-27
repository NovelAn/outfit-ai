<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { computed, ref } from "vue";
import { api, mediaUrl, messageOf } from "@/api/client";
import type { Look, PickMode, Recommendation } from "@/api/types";

const occasions = ["日常", "通勤", "约会", "聚会", "旅行"];
const moods = ["利落", "松弛", "低调", "想尝试一点新意"];
const OCCASION_KEY = "outfit-ai.last-occasion";
const modeCopy: Record<PickMode, { name: string; english: string; note: string }> = {
  safe: { name: "稳妥", english: "Safe", note: "熟悉、舒服，今天不用多想" },
  fresh: { name: "新鲜", english: "Fresh", note: "仍然像你，但组合有一点变化" },
  stretch: { name: "突破", english: "Stretch", note: "向边界多走半步" },
};

const weekday = new Date().getDay();
const occasion = ref(uni.getStorageSync(OCCASION_KEY) || (weekday > 0 && weekday < 6 ? "通勤" : "日常"));
const mood = ref("");
const city = ref("");
const latitude = ref<number>();
const longitude = ref<number>();
const locating = ref(true);
const loading = ref(false);
const recommendation = ref<Recommendation>();
const error = ref("");
const lockedIds = ref<string[]>([]);

const looks = computed(() => {
  const result = recommendation.value;
  if (!result) return [];
  const available = [result.safe, result.fresh, result.stretch].filter(
    (look): look is Look => Boolean(look),
  );
  return available.sort((a, b) => Number(isLookLocked(b)) - Number(isLookLocked(a)));
});

const locationLabel = computed(() => {
  if (latitude.value !== undefined) return "已使用当前位置";
  if (city.value.trim()) return `城市 · ${city.value.trim()}`;
  return "需要城市或位置";
});

function isLocked(id: string) {
  return lockedIds.value.includes(id);
}

function isLookLocked(look: Look) {
  return look.items.length > 0 && look.items.every((item) => isLocked(item.id));
}

function toggleItem(id: string) {
  lockedIds.value = isLocked(id)
    ? lockedIds.value.filter((itemId) => itemId !== id)
    : [...lockedIds.value, id];
}

function setOccasion(value: string) {
  occasion.value = value;
  uni.setStorageSync(OCCASION_KEY, value);
}

function setMood(value: string) {
  mood.value = mood.value === value ? "" : value;
}

function toggleLook(look: Look) {
  if (isLookLocked(look)) {
    const ids = new Set(look.items.map((item) => item.id));
    lockedIds.value = lockedIds.value.filter((id) => !ids.has(id));
  } else {
    lockedIds.value = Array.from(new Set([...lockedIds.value, ...look.items.map((item) => item.id)]));
  }
}

function getPosition(): Promise<{ latitude: number; longitude: number }> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("定位超时")), 5000);
    uni.getLocation({
      type: "wgs84",
      success: ({ latitude: lat, longitude: lng }) => {
        clearTimeout(timer);
        resolve({ latitude: lat, longitude: lng });
      },
      fail: (cause) => {
        clearTimeout(timer);
        reject(cause);
      },
    });
  });
}

async function resolveLocation() {
  locating.value = true;
  try {
    const profile = await api.profile();
    city.value = profile.city || "";
  } catch {
    // City input remains available when the profile service is unavailable.
  }
  try {
    const location = await getPosition();
    latitude.value = location.latitude;
    longitude.value = location.longitude;
  } catch {
    latitude.value = undefined;
    longitude.value = undefined;
  } finally {
    locating.value = false;
  }
}

async function generate(lockOverride?: string[]): Promise<boolean> {
  if (latitude.value === undefined && !city.value.trim()) {
    error.value = "无法读取位置，请先填写城市";
    return false;
  }
  loading.value = true;
  error.value = "";
  try {
    recommendation.value = await api.recommend({
      occasion: occasion.value,
      mood: mood.value || undefined,
      city: city.value.trim() || undefined,
      latitude: latitude.value,
      longitude: longitude.value,
      locked_item_ids: lockOverride || lockedIds.value,
    });
    return true;
  } catch (cause) {
    error.value = messageOf(cause);
    return false;
  } finally {
    loading.value = false;
  }
}

async function replaceOne(look: Look) {
  try {
    const selection = await uni.showActionSheet({
      itemList: look.items.map((item) => item.name || "未命名单品"),
    });
    const replaceId = look.items[selection.tapIndex]?.id;
    if (!replaceId) return;
    const keepIds = look.items.filter((item) => item.id !== replaceId).map((item) => item.id);
    lockedIds.value = keepIds;
    if (await generate(keepIds)) {
      uni.showToast({ title: "已保留其余单品重新搭配", icon: "none" });
    }
  } catch (cause) {
    const message = messageOf(cause);
    if (!message.includes("cancel")) uni.showToast({ title: message, icon: "none" });
  }
}

async function sendFeedback(look: Look) {
  try {
    const result = await uni.showActionSheet({
      itemList: ["喜欢这套", "这套不适合我"],
    });
    const liked = result.tapIndex === 0;
    await api.feedback({
      history_id: look.history_id,
      items_worn: look.items.map((item) => item.id),
      action: liked ? "saved" : "skipped",
      occasion: occasion.value,
      sentiment: liked ? "positive" : "negative",
    });
    uni.showToast({ title: liked ? "已记住你的喜欢" : "已记住，下次避开", icon: "none" });
  } catch (cause) {
    const message = messageOf(cause);
    if (!message.includes("cancel")) uni.showToast({ title: message, icon: "none" });
  }
}

async function wearToday(look: Look) {
  try {
    await api.feedback({
      history_id: look.history_id,
      items_worn: look.items.map((item) => item.id),
      action: "worn",
      occasion: occasion.value,
      sentiment: "positive",
    });
    uni.showToast({ title: "已记为今天穿了", icon: "success" });
  } catch (cause) {
    uni.showToast({ title: messageOf(cause), icon: "none" });
  }
}

onShow(resolveLocation);
</script>

<template>
  <view class="page recommend-page">
    <view class="eyebrow">Today’s edit</view>
    <text class="display-title">今天，想穿成<br />什么样的人？</text>
    <view class="lede">造型师只会使用你确认过的真实单品。先说场合和心情，再给三种幅度。</view>

    <view class="context-panel card">
      <view class="context-line">
        <text class="context-label">位置</text>
        <text class="context-value">{{ locating ? "正在定位…" : locationLabel }}</text>
      </view>
      <label v-if="!locating && latitude === undefined" class="city-field">
        <input v-model="city" class="input" placeholder="手动填写城市，例如上海" />
      </label>
      <view class="context-label context-group-label">场合</view>
      <scroll-view class="choice-scroll" scroll-x>
        <view class="choice-row">
          <view
            v-for="value in occasions"
            :key="value"
            class="chip"
            :class="{ active: occasion === value }"
            role="button"
            tabindex="0"
            :aria-pressed="occasion === value"
            @tap="setOccasion(value)"
            @keyup.enter="setOccasion(value)"
            @keyup.space="setOccasion(value)"
          >
            {{ value }}
          </view>
        </view>
      </scroll-view>
      <view class="context-label context-group-label">心情</view>
      <scroll-view class="choice-scroll" scroll-x>
        <view class="choice-row">
          <view
            v-for="value in moods"
            :key="value"
            class="chip"
            :class="{ active: mood === value }"
            role="button"
            tabindex="0"
            :aria-pressed="mood === value"
            @tap="setMood(value)"
            @keyup.enter="setMood(value)"
            @keyup.space="setMood(value)"
          >
            {{ value }}
          </view>
        </view>
      </scroll-view>
    </view>

    <view v-if="error" class="error-banner">{{ error }}</view>

    <view v-if="recommendation" class="weather-strip">
      <view>
        <text class="weather-temp">{{ Math.round(recommendation.weather.temp) }}°</text>
        <text class="weather-condition">{{ recommendation.weather.condition }}</text>
      </view>
      <text class="weather-context">{{ occasion }} · {{ mood || "不限定心情" }}</text>
    </view>

    <view v-if="loading" class="looks-list" aria-label="造型师正在搭配">
      <view v-for="index in 3" :key="index" class="look-card card look-skeleton">
        <view class="skeleton-title"></view>
        <view class="skeleton-hero"></view>
        <view class="skeleton-line"></view>
        <view class="skeleton-line short"></view>
      </view>
    </view>

    <view v-else-if="looks.length" class="looks-list">
      <view
        v-for="look in looks"
        :key="look.pick_mode"
        class="look-card card"
        :class="{ locked: isLookLocked(look) }"
      >
        <view class="look-heading">
          <view>
            <text class="mode-english">{{ modeCopy[look.pick_mode].english }}</text>
            <text class="mode-name">{{ modeCopy[look.pick_mode].name }}</text>
          </view>
          <text class="mode-note">{{ modeCopy[look.pick_mode].note }}</text>
        </view>
        <view class="look-images" :class="`count-${look.items.length}`">
          <view
            v-for="item in look.items"
            :key="item.id"
            class="look-item"
            :class="{ selected: isLocked(item.id) }"
            role="button"
            tabindex="0"
            :aria-pressed="isLocked(item.id)"
            @tap="toggleItem(item.id)"
            @keyup.enter="toggleItem(item.id)"
            @keyup.space="toggleItem(item.id)"
          >
            <image class="look-image" :src="mediaUrl(item.image_url)" mode="aspectFill" />
            <view v-if="isLocked(item.id)" class="lock-mark">已锁定</view>
            <text class="look-item-name">{{ item.name }}</text>
          </view>
        </view>
        <view class="stylist-note">
          <view class="note-rule"></view>
          <view>
            <text class="note-label">造型师手记</text>
            <text class="note-copy">{{ look.reason }}</text>
          </view>
        </view>
        <view class="fit-grid">
          <view>
            <text class="fit-label">天气</text>
            <text class="fit-copy">{{ look.weather_fit }}</text>
          </view>
          <view>
            <text class="fit-label">场合</text>
            <text class="fit-copy">{{ look.occasion_fit }}</text>
          </view>
        </view>
        <view class="look-actions">
          <button class="button-quiet" @tap="toggleLook(look)">
            {{ isLookLocked(look) ? "取消锁定" : "锁定这套" }}
          </button>
          <button class="button-quiet" @tap="sendFeedback(look)">反馈</button>
          <button class="button-quiet" @tap="replaceOne(look)">换一件</button>
          <button class="button-secondary" @tap="wearToday(look)">今天穿了</button>
        </view>
      </view>
      <view v-if="looks.length < 3" class="soft-notice">
        今天的衣橱条件只够组成 {{ looks.length }} 套可靠搭配，没有勉强凑数。
      </view>
    </view>

    <view v-else class="empty-state">
      先选好场合和心情。<br />至少确认上装、下装和鞋各一件，造型师才会开始。
    </view>

    <view class="sticky-action">
      <button class="button generate-button" :disabled="loading || locating" @tap="generate()">
        {{ loading ? "造型师正在搭配…" : recommendation ? "按现在的选择换一批" : "看看今天怎么穿" }}
      </button>
      <view v-if="lockedIds.length" class="locked-summary">已锁定 {{ lockedIds.length }} 件，换一批时会保留</view>
    </view>
  </view>
</template>

<style scoped>
.context-panel {
  margin-top: 26px;
  padding: 18px;
}

.context-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.context-label {
  color: #6e665c;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.context-value {
  font-size: 14px;
  font-weight: 600;
}

.city-field {
  display: block;
  margin-top: 12px;
}

.context-group-label {
  margin-top: 20px;
}

.choice-scroll {
  width: 100%;
  margin-top: 9px;
  white-space: nowrap;
}

.choice-row {
  display: inline-flex;
  gap: 8px;
}

.looks-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 24px;
}

.weather-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 22px;
  padding: 0 4px;
}

.weather-temp {
  font-family: "Songti SC", "STSong", serif;
  font-size: 30px;
  font-weight: 600;
}

.weather-condition {
  margin-left: 9px;
  color: #6e665c;
  font-size: 13px;
}

.weather-context {
  color: #6e665c;
  font-size: 12px;
}

.look-card {
  padding: 18px;
  overflow: hidden;
}

.look-card.locked {
  border-color: #a64b2a;
  box-shadow: 0 7px 24px rgba(116, 61, 39, 0.1);
}

.look-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.mode-english,
.mode-name,
.mode-note {
  display: block;
}

.mode-english {
  color: #a64b2a;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.mode-name {
  margin-top: 2px;
  font-family: "Songti SC", "STSong", serif;
  font-size: 26px;
  font-weight: 600;
}

.mode-note {
  max-width: 176px;
  color: #6e665c;
  font-size: 12px;
  line-height: 1.45;
  text-align: right;
}

.look-images {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  overflow: hidden;
  background: #e5ded2;
  border-radius: 12px;
}

.look-item {
  position: relative;
  min-width: 0;
  background: #e8e0d5;
}

.look-item.selected::after {
  position: absolute;
  inset: 0;
  border: 3px solid #a64b2a;
  border-radius: 2px;
  content: "";
  pointer-events: none;
}

.look-image {
  display: block;
  width: 100%;
  height: 220px;
}

.look-item-name {
  position: absolute;
  right: 6px;
  bottom: 6px;
  left: 6px;
  overflow: hidden;
  padding: 5px 7px;
  color: #fff;
  background: rgba(31, 27, 22, 0.7);
  border-radius: 6px;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lock-mark {
  position: absolute;
  z-index: 2;
  top: 7px;
  right: 7px;
  padding: 4px 6px;
  color: #71351f;
  background: #f5e3d9;
  border-radius: 999px;
  font-size: 9px;
  font-weight: 700;
}

.stylist-note {
  display: grid;
  grid-template-columns: 3px 1fr;
  gap: 12px;
  margin-top: 18px;
}

.note-rule {
  background: #a64b2a;
  border-radius: 999px;
}

.note-label,
.note-copy {
  display: block;
}

.note-label {
  color: #a64b2a;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.note-copy {
  margin-top: 6px;
  font-family: "Songti SC", "STSong", serif;
  font-size: 16px;
  line-height: 1.65;
}

.fit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #d8cfc1;
}

.fit-label,
.fit-copy {
  display: block;
}

.fit-label {
  color: #6e665c;
  font-size: 11px;
  font-weight: 700;
}

.fit-copy {
  margin-top: 5px;
  font-size: 12px;
  line-height: 1.55;
}

.look-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 18px;
}

.look-actions button {
  padding: 0 6px;
  font-size: 12px;
}

.soft-notice {
  padding: 4px 12px;
  color: #6e665c;
  font-size: 13px;
  line-height: 1.55;
  text-align: center;
}

.locked-summary {
  padding: 7px 4px 0;
  color: #6e665c;
  font-size: 11px;
  text-align: center;
}

.look-skeleton {
  min-height: 440px;
}

.skeleton-title,
.skeleton-hero,
.skeleton-line {
  background: linear-gradient(100deg, #e6ded3 20%, #f7f2ea 50%, #e6ded3 80%);
  background-size: 240% 100%;
  border-radius: 8px;
  animation: shimmer 1.5s infinite linear;
}

.skeleton-title {
  width: 42%;
  height: 30px;
}

.skeleton-hero {
  height: 240px;
  margin-top: 18px;
}

.skeleton-line {
  height: 13px;
  margin-top: 18px;
}

.skeleton-line.short {
  width: 70%;
  margin-top: 10px;
}

@keyframes shimmer {
  to {
    background-position: -240% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-title,
  .skeleton-hero,
  .skeleton-line {
    animation: none;
  }
}
</style>

<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { computed, ref } from "vue";
import { api, mediaUrl, messageOf } from "@/api/client";
import type { Look, PickMode, Recommendation, StyleReference } from "@/api/types";

type Season = "spring" | "summer" | "autumn" | "winter" | "spring_autumn";

const scenes = ["日常", "通勤", "约会", "聚会", "旅行"];
const seasons: { value: Season; label: string }[] = [
  { value: "spring", label: "春" },
  { value: "summer", label: "夏" },
  { value: "autumn", label: "秋" },
  { value: "winter", label: "冬" },
];
const modeCopy: Record<PickMode, { name: string; english: string; subtitle: string }> = {
  safe: { name: "稳妥", english: "SAFE", subtitle: "熟悉而准确" },
  fresh: { name: "新鲜", english: "FRESH", subtitle: "多一点变化" },
  stretch: { name: "突破", english: "STRETCH", subtitle: "向边界走半步" },
};

const scene = ref(new Date().getDay() > 0 && new Date().getDay() < 6 ? "通勤" : "日常");
const season = ref<Season>();
const styleNote = ref("");
const city = ref("");
const latitude = ref<number>();
const longitude = ref<number>();
const locating = ref(true);
const loading = ref(false);
const error = ref("");
const recommendation = ref<Recommendation>();
const references = ref<StyleReference[]>([]);
const selectedReferenceIds = ref<string[]>([]);

const looks = computed(() => {
  if (!recommendation.value) return [];
  return [
    recommendation.value.safe,
    recommendation.value.fresh,
    recommendation.value.stretch,
  ].filter((look): look is Look => Boolean(look));
});

const todayLabel = new Intl.DateTimeFormat("zh-CN", {
  month: "short",
  day: "numeric",
  weekday: "short",
}).format(new Date());

function toggleReference(id: string) {
  selectedReferenceIds.value = selectedReferenceIds.value.includes(id)
    ? selectedReferenceIds.value.filter((value) => value !== id)
    : [...selectedReferenceIds.value, id];
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

async function loadContext() {
  locating.value = true;
  try {
    const [profile, styleReferences] = await Promise.all([
      api.profile(),
      api.styleReferences(),
    ]);
    city.value = profile.city || "";
    references.value = styleReferences.filter((item) => item.status === "ready");
  } catch (cause) {
    error.value = messageOf(cause);
  }
  try {
    const position = await getPosition();
    latitude.value = position.latitude;
    longitude.value = position.longitude;
  } catch {
    latitude.value = undefined;
    longitude.value = undefined;
  } finally {
    locating.value = false;
  }
}

async function generate() {
  if (latitude.value === undefined && !city.value.trim()) {
    error.value = "无法读取位置，请填写城市后重试";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    recommendation.value = await api.recommend({
      occasion: scene.value,
      scene: scene.value,
      season: season.value,
      style_note: styleNote.value.trim() || undefined,
      reference_ids: selectedReferenceIds.value,
      city: city.value.trim() || undefined,
      latitude: latitude.value,
      longitude: longitude.value,
      locked_item_ids: [],
    });
  } catch (cause) {
    error.value = messageOf(cause);
  } finally {
    loading.value = false;
  }
}

async function feedback(look: Look) {
  try {
    const result = await uni.showActionSheet({ itemList: ["喜欢这套", "今天穿了", "不适合我"] });
    const actions = ["saved", "worn", "skipped"] as const;
    await api.feedback({
      history_id: look.history_id,
      items_worn: look.items.map((item) => item.id),
      action: actions[result.tapIndex],
      occasion: scene.value,
      sentiment: result.tapIndex === 2 ? "negative" : "positive",
    });
    uni.showToast({ title: result.tapIndex === 1 ? "已记为今天穿了" : "已记录反馈", icon: "none" });
  } catch (cause) {
    const message = messageOf(cause);
    if (!message.includes("cancel")) uni.showToast({ title: message, icon: "none" });
  }
}

function openInspiration() {
  uni.switchTab({ url: "/pages/inspiration/index" });
}

onShow(loadContext);
</script>

<template>
  <view class="today-page">
    <view class="topbar">
      <view>
        <text class="topbar-meta">{{ city || (locating ? "正在定位" : "未设置城市") }}</text>
        <text class="topbar-date">{{ todayLabel }}</text>
      </view>
      <text class="topbar-mark">OUTFIT-AI</text>
    </view>

    <view class="today-main">
      <view class="title-row">
        <view>
          <text class="page-title">今日推荐</text>
          <text class="page-subtitle">Daily Picks</text>
        </view>
        <button class="outline-button" :disabled="loading" @tap="generate">
          {{ recommendation ? "换一批" : "开始搭配" }}
        </button>
      </view>

      <view class="context-sheet">
        <view class="sheet-label">今天去哪里</view>
        <scroll-view scroll-x class="choice-scroll">
          <view class="choice-row">
            <button
              v-for="value in scenes"
              :key="value"
              class="text-choice"
              :class="{ active: scene === value }"
              @tap="scene = value"
            >
              {{ value }}
            </button>
          </view>
        </scroll-view>
        <view class="sheet-label">季节</view>
        <view class="season-row">
          <button
            v-for="item in seasons"
            :key="item.value"
            class="season-button"
            :class="{ active: season === item.value }"
            @tap="season = season === item.value ? undefined : item.value"
          >
            {{ item.label }}
          </button>
        </view>
        <input
          v-if="!locating && latitude === undefined"
          v-model="city"
          class="line-input"
          placeholder="定位不可用，填写城市"
        />
        <input
          v-model="styleNote"
          class="line-input"
          maxlength="500"
          placeholder="可选：今天有特别想法吗？"
        />
      </view>

      <view v-if="references.length" class="reference-section">
        <view class="section-heading">
          <text>今天参考这些 Look</text>
          <button class="link-button" @tap="openInspiration">管理长期灵感 →</button>
        </view>
        <scroll-view scroll-x class="reference-scroll">
          <view class="reference-row">
            <button
              v-for="item in references"
              :key="item.id"
              class="reference-card"
              :class="{ selected: selectedReferenceIds.includes(item.id) }"
              @tap="toggleReference(item.id)"
            >
              <image :src="mediaUrl(item.image_url)" mode="aspectFill" />
              <text>{{ selectedReferenceIds.includes(item.id) ? "已选" : "参考" }}</text>
            </button>
          </view>
        </scroll-view>
      </view>
      <button v-else class="add-reference" @tap="openInspiration">＋ 添加参考 Look</button>

      <view v-if="error" class="error-banner">{{ error }}</view>

      <view v-if="loading" class="loading-editorial">
        <view class="loading-line"></view>
        <text>造型师正在从真实衣橱里组合三套 Look…</text>
        <view class="loading-line"></view>
      </view>

      <view v-else-if="looks.length" class="look-list">
        <view v-for="(look, index) in looks" :key="look.pick_mode" class="look-editorial">
          <view class="look-kicker">LOOK {{ String(index + 1).padStart(2, "0") }}</view>
          <text class="look-title">{{ modeCopy[look.pick_mode].name }}</text>
          <view class="look-labels">
            <text class="mode-label">{{ modeCopy[look.pick_mode].english }}</text>
            <text>{{ modeCopy[look.pick_mode].subtitle }}</text>
          </view>
          <view class="editorial-number">EDITORIAL NO. {{ String(index + 1).padStart(2, "0") }}</view>
          <view class="garment-stack">
            <button v-for="item in look.items" :key="item.id" class="garment">
              <image :src="mediaUrl(item.image_url)" mode="aspectFit" />
              <text>{{ item.name }}</text>
            </button>
          </view>
          <text class="look-reason">{{ look.reason }}</text>
          <view class="fit-line">{{ look.weather_fit }} · {{ look.occasion_fit }}</view>
          <view class="look-actions">
            <button class="rust-button" :disabled="loading" @tap="generate">↻ AI 换一换</button>
            <button class="outline-button" @tap="feedback(look)">✦ 打分与反馈</button>
          </view>
        </view>
      </view>

      <view v-else class="empty-editorial">
        <text class="empty-title">从真实衣橱开始。</text>
        <text>选择场景，也可以挑几张参考 Look。AI 只会使用你已经确认的真实衣物。</text>
        <button class="navy-button" :disabled="loading || locating" @tap="generate">用我的衣橱搭配</button>
      </view>
    </view>
  </view>
</template>

<style scoped>
.today-page {
  min-height: 100vh;
  padding-bottom: calc(92px + env(safe-area-inset-bottom));
  background: #fbf9f4;
  color: #162839;
}

.topbar,
.title-row,
.section-heading,
.choice-row,
.season-row,
.reference-row,
.look-actions {
  display: flex;
  align-items: center;
}

.topbar {
  position: sticky;
  z-index: 5;
  top: 0;
  justify-content: space-between;
  min-height: 64px;
  padding: env(safe-area-inset-top) 20px 0;
  background: rgba(251, 249, 244, 0.96);
  border-bottom: 1px solid #e4e2dd;
}

.topbar-meta,
.topbar-date {
  display: block;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.topbar-date {
  margin-top: 3px;
  color: #74777d;
}

.topbar-mark {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.today-main {
  max-width: 520px;
  margin: 0 auto;
}

.title-row {
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid #e4e2dd;
}

.page-title {
  font-family: "Songti SC", "STSong", serif;
  font-size: 22px;
  font-weight: 700;
}

.page-subtitle {
  margin-left: 3px;
  color: #74777d;
  font-family: Georgia, serif;
  font-size: 11px;
  font-style: italic;
}

.outline-button,
.rust-button,
.navy-button,
.link-button,
.text-choice,
.season-button,
.reference-card,
.garment,
.add-reference {
  margin: 0;
}

.outline-button,
.rust-button {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid #c4c6cd;
  border-radius: 999px;
  background: transparent;
  color: #162839;
  font-size: 12px;
  font-weight: 700;
  line-height: 38px;
}

.outline-button::after,
.rust-button::after,
.navy-button::after,
.link-button::after,
.text-choice::after,
.season-button::after,
.reference-card::after,
.garment::after,
.add-reference::after {
  border: 0;
}

.context-sheet {
  margin: 20px;
  padding: 16px;
  background: #f5f3ee;
  border: 1px solid #e4e2dd;
  border-radius: 3px;
}

.sheet-label {
  margin: 12px 0 8px;
  color: #9a442a;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.sheet-label:first-child {
  margin-top: 0;
}

.choice-row {
  gap: 4px;
}

.text-choice,
.season-button {
  min-width: 48px;
  min-height: 40px;
  padding: 0 12px;
  background: transparent;
  color: #74777d;
  border: 1px solid #d8d9dc;
  border-radius: 0;
  font-size: 12px;
  line-height: 38px;
}

.text-choice.active,
.season-button.active {
  color: #fff;
  background: #162839;
  border-color: #162839;
}

.season-row {
  gap: 4px;
}

.line-input {
  box-sizing: border-box;
  width: 100%;
  height: 44px;
  margin-top: 12px;
  color: #162839;
  background: transparent;
  border-bottom: 1px solid #c4c6cd;
  font-size: 13px;
}

.reference-section {
  padding: 8px 0 22px;
  border-bottom: 1px solid #e4e2dd;
}

.section-heading {
  justify-content: space-between;
  padding: 0 20px 12px;
  font-family: "Songti SC", "STSong", serif;
  font-size: 17px;
}

.link-button {
  min-height: 44px;
  padding: 0;
  background: transparent;
  color: #74777d;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 11px;
  line-height: 44px;
}

.reference-scroll {
  width: 100%;
  white-space: nowrap;
}

.reference-row {
  gap: 10px;
  padding: 0 20px;
}

.reference-card {
  position: relative;
  width: 86px;
  height: 122px;
  flex: 0 0 auto;
  padding: 0;
  overflow: hidden;
  background: #ece9e2;
  border: 2px solid transparent;
  border-radius: 2px;
}

.reference-card.selected {
  border-color: #9a442a;
}

.reference-card image {
  width: 100%;
  height: 100%;
}

.reference-card text {
  position: absolute;
  right: 4px;
  bottom: 4px;
  padding: 3px 6px;
  color: #fff;
  background: #162839;
  font-size: 9px;
}

.add-reference {
  width: calc(100% - 40px);
  min-height: 52px;
  margin: 18px 20px;
  color: #162839;
  background: transparent;
  border: 1px dashed #c4c6cd;
  border-radius: 2px;
  font-size: 12px;
  line-height: 50px;
}

.error-banner {
  margin: 16px 20px;
}

.loading-editorial,
.empty-editorial {
  padding: 80px 28px;
  text-align: center;
}

.loading-editorial text {
  display: block;
  margin: 18px 0;
  color: #74777d;
  font-family: Georgia, "Songti SC", serif;
  font-size: 14px;
  font-style: italic;
}

.loading-line {
  height: 1px;
  background: #e4e2dd;
}

.look-editorial {
  position: relative;
  padding: 42px 24px 52px;
  text-align: center;
  border-bottom: 1px solid #e4e2dd;
}

.look-kicker {
  position: absolute;
  top: 24px;
  left: 20px;
  color: #74777d;
  font-size: 9px;
  letter-spacing: 0.08em;
}

.look-title {
  display: block;
  font-family: "Songti SC", "STSong", serif;
  font-size: 34px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.look-labels {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 9px;
}

.look-labels text {
  padding: 4px 7px;
  background: #e7e5e0;
}

.look-labels .mode-label {
  color: #fff;
  background: #9a442a;
  font-weight: 700;
  letter-spacing: 0.18em;
}

.editorial-number {
  margin-top: 14px;
  color: #9c9da1;
  font-size: 8px;
  letter-spacing: 0.12em;
}

.garment-stack {
  width: 78%;
  margin: 36px auto 28px;
}

.garment {
  width: 100%;
  min-height: 156px;
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.garment image {
  width: 100%;
  height: 138px;
}

.garment text {
  display: block;
  color: #74777d;
  font-size: 9px;
  line-height: 18px;
}

.look-reason,
.fit-line {
  display: block;
  max-width: 340px;
  margin: 0 auto;
  font-family: "Songti SC", "STSong", serif;
  font-size: 13px;
  line-height: 1.8;
}

.fit-line {
  margin-top: 8px;
  color: #74777d;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 10px;
}

.look-actions {
  justify-content: center;
  gap: 10px;
  margin-top: 20px;
}

.rust-button {
  color: #9a442a;
  background: #fff3ec;
  border-color: #e2bfae;
}

.empty-title {
  display: block;
  margin-bottom: 12px;
  font-family: "Songti SC", "STSong", serif;
  font-size: 27px;
}

.empty-editorial > text:last-of-type {
  display: block;
  color: #74777d;
  font-size: 13px;
  line-height: 1.8;
}

.navy-button {
  width: 100%;
  min-height: 48px;
  margin-top: 24px;
  color: #fff;
  background: #162839;
  border-radius: 0;
  font-size: 13px;
  font-weight: 700;
  line-height: 48px;
}
</style>

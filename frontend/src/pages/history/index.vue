<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { ref } from "vue";
import { api, mediaUrl, messageOf } from "@/api/client";
import type { HistoryItem, PickMode } from "@/api/types";

const history = ref<HistoryItem[]>([]);
const loading = ref(true);
const error = ref("");

const modeName: Record<PickMode, string> = {
  safe: "Safe · 稳妥",
  fresh: "Fresh · 新鲜",
  stretch: "Stretch · 突破",
};

const actionName: Record<string, string> = {
  shown: "看过",
  saved: "喜欢",
  skipped: "不适合",
  worn: "今天穿了",
};

function dateLabel(value: string) {
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : `${date.getMonth() + 1}月${date.getDate()}日`;
}

async function loadHistory() {
  loading.value = true;
  error.value = "";
  try {
    history.value = await api.history();
  } catch (cause) {
    error.value = messageOf(cause, "读取历史失败");
  } finally {
    loading.value = false;
  }
}

onShow(loadHistory);
</script>

<template>
  <view class="page history-page">
    <view class="eyebrow">The look archive</view>
    <text class="display-title">穿过的日子，<br />会慢慢变成品味。</text>
    <view class="lede">每次选择都留下一点线索。喜欢、不适合和真正穿出门的，都会帮造型师更懂你。</view>

    <view v-if="error" class="error-banner">{{ error }}</view>

    <view v-if="loading" class="timeline">
      <view v-for="index in 3" :key="index" class="history-row">
        <view class="timeline-mark"></view>
        <view class="history-card card history-skeleton"></view>
      </view>
    </view>
    <view v-else-if="history.length" class="timeline">
      <view v-for="entry in history" :key="entry.id" class="history-row">
        <view class="timeline-date">
          <text>{{ dateLabel(entry.date) }}</text>
          <view class="timeline-mark"></view>
        </view>
        <view class="history-card card">
          <image
            class="history-image"
            :src="entry.collage_path ? mediaUrl(entry.collage_path) : api.collage(entry.item_ids)"
            mode="aspectFill"
          />
          <view class="history-copy">
            <view class="history-meta">
              <text class="mode-pill">{{ modeName[entry.pick_mode] }}</text>
              <text class="action-pill" :class="{ worn: entry.wore_it }">
                {{ actionName[entry.action] || entry.action }}
              </text>
            </view>
            <text class="history-title">{{ entry.occasion || "日常" }}穿搭</text>
            <text v-if="entry.mood" class="history-mood">那天想要：{{ entry.mood }}</text>
            <text v-if="entry.reason" class="history-reason">{{ entry.reason }}</text>
          </view>
        </view>
      </view>
    </view>
    <view v-else class="empty-state">
      第一套穿搭还在前面。<br />去「推荐」看看今天怎么穿。
    </view>
  </view>
</template>

<style scoped>
.timeline {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 22px;
  margin-top: 30px;
}

.timeline::before {
  position: absolute;
  top: 12px;
  bottom: 12px;
  left: 5px;
  width: 1px;
  background: #d8cfc1;
  content: "";
}

.history-row {
  position: relative;
  padding-left: 24px;
}

.timeline-date {
  display: flex;
  align-items: center;
  margin-bottom: 9px;
  color: #6e665c;
  font-size: 12px;
  font-weight: 600;
}

.timeline-mark {
  position: absolute;
  z-index: 2;
  top: 4px;
  left: 0;
  width: 11px;
  height: 11px;
  background: #faf8f4;
  border: 3px solid #a64b2a;
  border-radius: 50%;
}

.history-card {
  display: grid;
  grid-template-columns: 42% 1fr;
  min-height: 200px;
  overflow: hidden;
}

.history-image {
  width: 100%;
  height: 100%;
  min-height: 200px;
  background: #e8e0d5;
}

.history-copy {
  min-width: 0;
  padding: 16px;
}

.history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mode-pill,
.action-pill {
  padding: 5px 8px;
  color: #6e665c;
  background: #e5ded2;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
}

.action-pill.worn {
  color: #71351f;
  background: #e8d5c8;
}

.history-title,
.history-mood,
.history-reason {
  display: block;
}

.history-title {
  margin-top: 14px;
  font-family: "Songti SC", "STSong", serif;
  font-size: 19px;
  font-weight: 600;
}

.history-mood {
  margin-top: 6px;
  color: #6e665c;
  font-size: 11px;
}

.history-reason {
  display: -webkit-box;
  margin-top: 12px;
  overflow: hidden;
  font-size: 12px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.history-skeleton {
  min-height: 200px;
  background: linear-gradient(100deg, #eee8df 20%, #f8f4ed 50%, #eee8df 80%);
  background-size: 240% 100%;
  animation: shimmer 1.5s infinite linear;
}

@keyframes shimmer {
  to {
    background-position: -240% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .history-skeleton {
    animation: none;
  }
}
</style>

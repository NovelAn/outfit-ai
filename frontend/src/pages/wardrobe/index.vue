<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { ref } from "vue";
import { api, mediaUrl, messageOf, uploadItem } from "@/api/client";
import type { AnalysisStatus, WardrobeItem } from "@/api/types";
import { chooseImages } from "@/utils/media";

interface PendingItem {
  id: string;
  localPath: string;
  status: AnalysisStatus;
  attempt_count: number;
  message?: string;
}

const items = ref<WardrobeItem[]>([]);
const pending = ref<PendingItem[]>([]);
const loading = ref(true);
const uploading = ref(false);
const error = ref("");
const editorId = ref("");
const editName = ref("");
const editCategory = ref("");
const editColor = ref("");
const editMaterial = ref("");
const editFit = ref("");
const editStyles = ref("");
const categoryIndex = ref(0);
const pollingIds = new Set<string>();
const PENDING_KEY = "outfit-ai.pending-uploads";

const categories = [
  { value: "top", label: "上装" },
  { value: "bottom", label: "下装" },
  { value: "shoes", label: "鞋履" },
  { value: "outerwear", label: "外套" },
  { value: "accessory", label: "配饰" },
];
const categoryName = Object.fromEntries(categories.map((entry) => [entry.value, entry.label]));

const statusName: Record<AnalysisStatus, string> = {
  pending: "等待识别",
  analyzing: "造型师识别中",
  ready: "待你确认",
  failed: "识别失败",
};

async function loadItems() {
  loading.value = true;
  error.value = "";
  try {
    items.value = await api.items();
  } catch (cause) {
    error.value = messageOf(cause);
  } finally {
    loading.value = false;
  }
}

function openEditor(item: WardrobeItem) {
  editorId.value = item.id;
  editName.value = item.name || "";
  const index = categories.findIndex((entry) => entry.value === item.category);
  categoryIndex.value = index < 0 ? 0 : index;
  editCategory.value = index < 0 ? "" : categories[index].value;
  editColor.value = item.primary_color || "";
  editMaterial.value = item.material || "";
  editFit.value = item.fit || "";
  editStyles.value = (item.styles || []).join("、");
}

function selectCategory(event: { detail: { value: string | number } }) {
  categoryIndex.value = Number(event.detail.value);
  editCategory.value = categories[categoryIndex.value].value;
}

function savePending() {
  uni.setStorageSync(PENDING_KEY, pending.value);
}

function restorePending() {
  if (pending.value.length) return;
  const stored = uni.getStorageSync(PENDING_KEY);
  if (Array.isArray(stored)) pending.value = stored as PendingItem[];
}

function closeEditor() {
  editorId.value = "";
}

async function openPending(item: PendingItem) {
  if (item.status !== "ready") return;
  try {
    openEditor(await api.itemStatus(item.id));
  } catch (cause) {
    item.message = messageOf(cause);
  }
}

async function pollItem(id: string) {
  if (pollingIds.has(id)) return;
  pollingIds.add(id);
  let networkFailures = 0;
  try {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      try {
        const item = await api.itemStatus(id);
        networkFailures = 0;
        const local = pending.value.find((entry) => entry.id === id);
        if (local) {
          local.status = item.status;
          local.attempt_count = item.attempt_count;
          local.message = item.status === "ready" ? "轻触确认识别结果" : "";
          savePending();
        }
        if (item.status === "ready") return;
        if (item.status === "failed") {
          if (local) {
            local.message = "识别没有完成，可重新尝试";
            savePending();
          }
          return;
        }
      } catch (cause) {
        networkFailures += 1;
        const local = pending.value.find((entry) => entry.id === id);
        if (networkFailures >= 3) {
          if (local) {
            local.message = `${messageOf(cause)}；稍后进入衣橱会继续`;
            savePending();
          }
          return;
        }
        if (local) local.message = `连接波动，正在重试（${networkFailures}/3）`;
      }
    }
    const local = pending.value.find((entry) => entry.id === id);
    if (local) local.message = "识别仍在进行，稍后再回来看看";
  } finally {
    pollingIds.delete(id);
  }
}

async function chooseAndUpload() {
  error.value = "";
  try {
    const paths = await chooseImages(6);
    uploading.value = true;
    for (const filePath of paths) {
      try {
        const uploaded = await uploadItem(filePath);
        pending.value.unshift({
          id: uploaded.id,
          localPath: filePath,
          status: uploaded.status as AnalysisStatus,
          attempt_count: 0,
        });
        savePending();
        void pollItem(uploaded.id);
      } catch (cause) {
        error.value = messageOf(cause);
      }
    }
  } catch (cause) {
    const message = messageOf(cause);
    if (!message.includes("cancel")) error.value = message;
  } finally {
    uploading.value = false;
  }
}

async function retry(item: PendingItem) {
  item.message = "";
  try {
    const result = await api.retryItem(item.id);
    item.status = result.status as AnalysisStatus;
    savePending();
    void pollItem(item.id);
  } catch (cause) {
    item.message = messageOf(cause);
  }
}

async function confirmItem() {
  if (!editName.value.trim() || !editCategory.value.trim() || !editColor.value.trim()) {
    uni.showToast({ title: "请补全名称、类别和主色", icon: "none" });
    return;
  }
  try {
    await api.confirmItem(editorId.value, {
      name: editName.value.trim(),
      category: editCategory.value.trim(),
      primary_color: editColor.value.trim(),
      material: editMaterial.value.trim() || null,
      fit: editFit.value.trim() || null,
      styles: editStyles.value
        .split(/[、,，]/)
        .map((value) => value.trim())
        .filter(Boolean),
      confirmed_by_user: true,
    });
    pending.value = pending.value.filter((entry) => entry.id !== editorId.value);
    savePending();
    closeEditor();
    await loadItems();
    uni.showToast({ title: "已加入衣橱", icon: "success" });
  } catch (cause) {
    uni.showToast({ title: messageOf(cause), icon: "none" });
  }
}

onShow(async () => {
  restorePending();
  await loadItems();
  for (const item of pending.value) {
    if (item.status === "pending" || item.status === "analyzing") void pollItem(item.id);
  }
});
</script>

<template>
  <view class="page wardrobe-page">
    <view class="eyebrow">Personal wardrobe</view>
    <text class="display-title">穿真实的衣服，<br />养成自己的风格。</text>
    <view class="lede">照片会先由造型师识别，再由你确认。AI 不会把没确认的单品拿去搭配。</view>

    <view v-if="error" class="error-banner">{{ error }}</view>

    <view v-if="pending.length" class="pending-section">
      <view class="section-title">正在整理</view>
      <view class="pending-list">
        <view
          v-for="item in pending"
          :key="item.id"
          class="pending-card card"
          :role="item.status === 'ready' ? 'button' : undefined"
          :tabindex="item.status === 'ready' ? 0 : -1"
          @tap="openPending(item)"
          @keyup.enter="openPending(item)"
          @keyup.space="openPending(item)"
        >
          <image class="pending-image" :src="item.localPath" mode="aspectFill" />
          <view class="pending-copy">
            <view class="status-pill">{{ statusName[item.status] }}</view>
            <text class="pending-hint">
              {{ item.message || (item.status === "ready" ? "轻触确认识别结果" : "通常只需要一点时间") }}
            </text>
            <button
              v-if="item.status === 'failed'"
              class="button-quiet retry-button"
              @tap="retry(item)"
            >
              再试一次
            </button>
          </view>
        </view>
      </view>
    </view>

    <view class="section-title">衣橱 · {{ items.length }} 件</view>
    <view v-if="loading" class="wardrobe-grid" aria-label="正在加载衣橱">
      <view v-for="index in 4" :key="index" class="item-card card skeleton"></view>
    </view>
    <view v-else-if="items.length" class="wardrobe-grid">
      <view
        v-for="item in items"
        :key="item.id"
        class="item-card card"
        role="button"
        tabindex="0"
        hover-class="card-pressed"
        @tap="openEditor(item)"
        @keyup.enter="openEditor(item)"
        @keyup.space="openEditor(item)"
      >
        <image class="item-image" :src="mediaUrl(item.image_url)" mode="aspectFill" />
        <view class="item-meta">
          <text class="item-name">{{ item.name || "未命名单品" }}</text>
          <text class="item-detail">
            {{ categoryName[item.category || ""] || item.category || "未分类" }}
            <template v-if="item.primary_color"> · {{ item.primary_color }}</template>
          </text>
        </view>
      </view>
    </view>
    <view v-else class="empty-state">
      再加几件适合今天的单品。<br />先从常穿的上装、下装和鞋开始。
    </view>

    <button class="upload-fab" :disabled="uploading" aria-label="上传衣物照片" @tap="chooseAndUpload">
      {{ uploading ? "上传中" : "＋ 添加衣物" }}
    </button>

    <view v-if="editorId" class="sheet-mask" @tap.self="closeEditor">
      <view class="editor-sheet">
        <view class="sheet-handle"></view>
        <view class="sheet-heading">确认这件单品</view>
        <view class="sheet-note">AI 先填了一版，你来做最后决定。</view>
        <view class="form-grid">
          <label class="field">
            <text class="field-label">名称 *</text>
            <input v-model="editName" class="input" placeholder="例如：米白牛津纺衬衫" />
          </label>
          <view class="field">
            <text class="field-label">类别 *（top / bottom / shoes）</text>
            <picker
              :range="categories"
              range-key="label"
              :value="categoryIndex"
              @change="selectCategory"
            >
              <view class="input picker-input">
                {{ editCategory ? categoryName[editCategory] : "请选择类别" }}
              </view>
            </picker>
          </view>
          <label class="field">
            <text class="field-label">主色 *</text>
            <input v-model="editColor" class="input" placeholder="米白" />
          </label>
          <label class="field">
            <text class="field-label">材质</text>
            <input v-model="editMaterial" class="input" placeholder="棉、羊毛、皮革…" />
          </label>
          <label class="field">
            <text class="field-label">版型</text>
            <input v-model="editFit" class="input" placeholder="合身、宽松…" />
          </label>
          <label class="field">
            <text class="field-label">风格关键词</text>
            <input v-model="editStyles" class="input" placeholder="极简、通勤（用顿号分隔）" />
          </label>
        </view>
        <view class="sheet-actions">
          <button class="button-quiet" @tap="closeEditor">稍后再说</button>
          <button class="button" @tap="confirmItem">确认入库</button>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.pending-section {
  margin-top: 28px;
}

.pending-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pending-card {
  display: flex;
  min-height: 112px;
  overflow: hidden;
}

.pending-image {
  width: 112px;
  height: 112px;
  background: #e8e0d5;
}

.pending-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 14px;
}

.status-pill {
  padding: 5px 9px;
  color: #71351f;
  background: #e8d5c8;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.pending-hint {
  margin-top: 8px;
  color: #6e665c;
  font-size: 13px;
}

.retry-button {
  min-height: 36px;
  margin-top: 10px;
  padding: 0 12px;
  line-height: 36px;
}

.wardrobe-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.item-card {
  min-width: 0;
  overflow: hidden;
}

.item-image {
  display: block;
  width: 100%;
  height: 210px;
  background: #e8e0d5;
}

.item-meta {
  padding: 12px;
}

.item-name,
.item-detail {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-name {
  font-family: "Songti SC", "STSong", serif;
  font-size: 16px;
  font-weight: 600;
}

.item-detail {
  margin-top: 5px;
  color: #6e665c;
  font-size: 12px;
}

.skeleton {
  height: 268px;
  background: linear-gradient(100deg, #eee8df 20%, #f8f4ed 50%, #eee8df 80%);
  background-size: 240% 100%;
  animation: shimmer 1.5s infinite linear;
}

.upload-fab {
  position: fixed;
  z-index: 9;
  right: 20px;
  bottom: calc(72px + env(safe-area-inset-bottom));
  min-height: 52px;
  margin: 0;
  padding: 0 20px;
  color: #fff;
  background: #a64b2a;
  border-radius: 999px;
  box-shadow: 0 8px 24px rgba(116, 61, 39, 0.22);
  font-size: 15px;
  font-weight: 600;
  line-height: 52px;
}

.upload-fab::after {
  border: 0;
}

.sheet-mask {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: flex;
  align-items: flex-end;
  background: rgba(31, 27, 22, 0.32);
}

.editor-sheet {
  box-sizing: border-box;
  width: 100%;
  max-height: 88vh;
  padding: 10px 20px calc(24px + env(safe-area-inset-bottom));
  overflow-y: auto;
  background: #faf8f4;
  border-radius: 24px 24px 0 0;
}

.sheet-handle {
  width: 40px;
  height: 4px;
  margin: 0 auto 18px;
  background: #c9beb0;
  border-radius: 999px;
}

.sheet-heading {
  font-family: "Songti SC", "STSong", serif;
  font-size: 24px;
  font-weight: 600;
}

.sheet-note {
  margin-top: 6px;
  color: #6e665c;
  font-size: 14px;
}

.sheet-actions {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 10px;
  margin-top: 24px;
}

@keyframes shimmer {
  to {
    background-position: -240% 0;
  }
}

@media (min-width: 720px) {
  .upload-fab {
    right: calc((100vw - 640px) / 2);
  }

  .editor-sheet {
    max-width: 680px;
    margin: 0 auto;
    border-radius: 24px 24px 0 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }
}
</style>

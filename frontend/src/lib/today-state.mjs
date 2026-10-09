export const displayWeatherForRecommendation = (weather, recommendation) => weather || recommendation?.weather;

export const lookFeedbackKey = (look) => look?.historyId || "";

export const formatTargetDateLabel = (value) => {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "未选择";
  const [, month, day] = value.split("-");
  return `${Number(month)}/${Number(day)}`;
};

export const recommendationErrorMessage = (error, hasCachedRecommendation) => {
  const message = error instanceof Error ? error.message : "每日推荐加载失败";
  return hasCachedRecommendation ? `今日推荐加载失败，当前显示上一组缓存：${message}` : message;
};

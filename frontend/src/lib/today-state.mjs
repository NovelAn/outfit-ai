export const displayWeatherForRecommendation = (weather, recommendation) => weather || recommendation?.weather;

export const lookFeedbackKey = (look) => look?.historyId || "";

export const recommendationErrorMessage = (error, hasCachedRecommendation) => {
  const message = error instanceof Error ? error.message : "每日推荐加载失败";
  return hasCachedRecommendation ? `今日推荐加载失败，当前显示上一组缓存：${message}` : message;
};

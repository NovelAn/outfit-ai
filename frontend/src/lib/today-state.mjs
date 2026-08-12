export const displayWeatherForRecommendation = (weather, recommendation) => weather || recommendation?.weather;

export const lookFeedbackKey = (look) => look?.historyId || "";

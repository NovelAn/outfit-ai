export const SEASON_OPTIONS = ["春", "夏", "秋", "冬"];
export const THICKNESS_OPTIONS = ["轻薄", "适中", "厚实"];

const seasonAliases = {
  春季: "春",
  夏季: "夏",
  秋季: "秋",
  初秋: "秋",
  冬季: "冬",
  四季: "四季",
  全年: "四季",
  all: "四季",
};

export function normalizeSeasonValues(values = []) {
  const normalized = values.map((season) => seasonAliases[season] || season);
  return normalized.includes("四季") ? [...SEASON_OPTIONS] : [...new Set(normalized)];
}

export function wardrobeInfoTags(item = {}) {
  const seasons = normalizeSeasonValues(item.seasons || []);
  return [
    ...seasons,
    ...(seasons.length > 0 && item.thickness ? ["·"] : []),
    item.thickness || "",
  ].filter(Boolean);
}

export function wardrobeFeatureTags(item = {}) {
  return (item.tags || []).filter((tag) => !THICKNESS_OPTIONS.includes(tag));
}

export function filterWardrobeItems(
  items,
  { category = "全部", seasons = [], thicknesses = [] } = {},
) {
  return items.filter((item) => {
    const matchesCategory = category === "全部" || item.category === category;
    const itemSeasons = normalizeSeasonValues(item.seasons || []);
    const seasonFilterActive = seasons.length > 0 && seasons.length < SEASON_OPTIONS.length;
    const matchesSeason =
      !seasonFilterActive || itemSeasons.some((season) => seasons.includes(season));
    const matchesThickness =
      thicknesses.length === 0 || thicknesses.includes(item.thickness || "");
    return matchesCategory && matchesSeason && matchesThickness;
  });
}

export function toggleFilterValue(values, value, allValues) {
  if (value === "四季") {
    return allValues.every((option) => values.includes(option)) ? [] : [...allValues];
  }
  return values.includes(value)
    ? values.filter((option) => option !== value)
    : [...values, value];
}

const presentationRank = (item = {}) => {
  const text = `${item.category || ""} ${item.name || ""}`.toLowerCase();
  if (/帽|hat|cap/.test(text)) return 10;
  if (/围巾|丝巾|领巾|围脖|scarf|tie/.test(text)) return 20;
  if (/外套|夹克|风衣|大衣|西装|背心|马甲|outerwear|jacket|coat|blazer|cardigan|vest/.test(text)) return 30;
  if (/上装|衬衫|t恤|短袖|毛衣|针织|shirt|tee|sweater|top|knit/.test(text)) return 40;
  if (/下装|裤|裙|牛仔|bottom|pants|trouser|jean|short|skirt/.test(text)) return 50;
  if (/鞋|靴|sneaker|shoe|boot|loafer|derby/.test(text)) return 60;
  if (/配饰|包|腰带|首饰|手表|accessory|bag|belt|jewelry|watch/.test(text)) return 70;
  return 70;
};

export const orderLookItems = (items = []) =>
  items
    .map((item, index) => ({ item, index }))
    .sort((left, right) => presentationRank(left.item) - presentationRank(right.item) || left.index - right.index)
    .map(({ item }) => item);

const STACK_ROTATIONS = [-3, 2, -1, 3, -2, 1];

export const lookStackLayout = (count, expanded) => ({
  height: count === 0 ? 0 : expanded ? count * 152 - 20 : 164,
  offsets: Array.from({ length: count }, (_, index) => expanded ? index * 152 : index * 10),
  rotations: Array.from(
    { length: count },
    (_, index) => expanded ? (index % 2 ? 1 : -1) : STACK_ROTATIONS[index % STACK_ROTATIONS.length],
  ),
});

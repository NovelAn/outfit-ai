export const compactLookItems = (items = []) => {
  const visualItems = [...items];
  const accessoryAnchor = visualItems.findIndex((item) => item.category === "配饰" && /帽|hat|cap/i.test(item.name));
  if (accessoryAnchor > 0) visualItems.unshift(visualItems.splice(accessoryAnchor, 1)[0]);

  return { primaryItems: visualItems.slice(0, 3), railItems: visualItems.slice(3) };
};

export function chooseImages(count: number): Promise<string[]> {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count,
      sourceType: ["album", "camera"],
      sizeType: ["compressed"],
      success: (result) =>
        resolve(Array.isArray(result.tempFilePaths) ? result.tempFilePaths : [result.tempFilePaths]),
      fail: reject,
    });
  });
}

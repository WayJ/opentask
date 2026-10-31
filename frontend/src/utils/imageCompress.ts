/**
 * 图片压缩工具
 */

// 最大尺寸（1080p: 1920x1080）
const MAX_WIDTH = 1920;
const MAX_HEIGHT = 1080;
// 目标大小（1MB）
const TARGET_SIZE = 1 * 1024 * 1024;

interface CompressOptions {
  maxSize?: number;
  maxWidth?: number;
  maxHeight?: number;
}

/**
 * 压缩图片文件
 * @param file 原始图片文件
 * @param options 压缩选项
 * @returns 压缩后的 File 对象
 */
export async function compressImage(file: File, options: CompressOptions = {}): Promise<File> {
  const { maxSize = TARGET_SIZE, maxWidth = MAX_WIDTH, maxHeight = MAX_HEIGHT } = options;
  // 如果不是图片类型，直接返回原文件
  if (!file.type.startsWith('image/')) {
    return file;
  }

  // 如果文件已经小于目标大小且尺寸合适，直接返回
  if (file.size <= maxSize) {
    const dimensions = await getImageDimensions(file);
    if (dimensions.width <= maxWidth && dimensions.height <= maxHeight) {
      return file;
    }
  }

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      // 计算缩放比例
      let width = img.width;
      let height = img.height;

      if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height);
        width = Math.floor(width * ratio);
        height = Math.floor(height * ratio);
      }

      // 创建 Canvas 进行压缩
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('无法获取 Canvas 上下文'));
        return;
      }

      // 绘制图片
      ctx.drawImage(img, 0, 0, width, height);

      // 初始质量
      let quality = 0.9;

      // 递归压缩直到满足大小要求
      const compress = () => {
        canvas.toBlob(
          blob => {
            if (!blob) {
              reject(new Error('图片压缩失败'));
              return;
            }

            // 如果已经满足大小要求，或质量已经很低了，就返回
            if (blob.size <= maxSize || quality <= 0.5) {
              const compressedFile = new File([blob], file.name, { type: file.type, lastModified: Date.now() });
              resolve(compressedFile);
            } else {
              // 降低质量继续压缩
              quality -= 0.1;
              compress();
            }
          },
          file.type,
          quality
        );
      };

      compress();
    };

    img.onerror = () => {
      reject(new Error('图片加载失败'));
    };

    // 加载图片
    const reader = new FileReader();
    reader.onload = e => {
      img.src = e.target?.result as string;
    };
    reader.onerror = () => {
      reject(new Error('文件读取失败'));
    };
    reader.readAsDataURL(file);
  });
}

/**
 * 获取图片尺寸
 */
function getImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.width, height: img.height });
    };
    img.onerror = () => {
      reject(new Error('无法获取图片尺寸'));
    };
    img.src = URL.createObjectURL(file);
  });
}

/**
 * 批量压缩图片
 * @param files 文件列表
 * @param options 压缩选项
 * @returns 压缩后的文件列表
 */
export async function compressImages(files: File[], options: CompressOptions = {}): Promise<File[]> {
  const results: File[] = [];

  // eslint-disable-next-line @typescript-eslint/no-loop-func
  for (const file of files) {
    if (file.type.startsWith('image/')) {
      try {
        // eslint-disable-next-line no-await-in-loop
        const compressed = await compressImage(file, options);
        results.push(compressed);
      } catch (error) {
        console.error(`压缩图片 ${file.name} 失败:`, error);
        // 压缩失败，使用原文件
        results.push(file);
      }
    } else {
      // 非图片文件，直接添加
      results.push(file);
    }
  }

  return results;
}

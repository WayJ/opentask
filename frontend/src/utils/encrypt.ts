/**
 * 加密工具
 * SSO 密码加密实现
 */
import CryptoJS from 'crypto-js';

// 手动导入需要的模块
const Base64 = (CryptoJS as any).enc.Base64;
const Hex = (CryptoJS as any).enc.Hex;
const UTF8 = (CryptoJS as any).enc.Utf8;
const { parse } = UTF8;
const md5 = (CryptoJS as any).MD5;
const ECB = (CryptoJS as any).mode.ECB;
const pkcs7 = (CryptoJS as any).pad.Pkcs7;

export interface EncryptionParams {
  iv: string;
  key: string;
  useHex: boolean;
}

// 密钥：MD5(VITE_CIPHER_KEY)
// 添加默认值以防环境变量未加载
const CIPHER_KEY = import.meta.env.VITE_CIPHER_KEY || 'EY8WePvjM5GGwQzn';
const defaultKey = md5(CIPHER_KEY).toString();

/**
 * AesEncryption 加密类
 * 完全按照原项目实现
 */
export class AesEncryption {
  private iv: any;
  private key: any;
  private useHex = true;

  constructor(opt: Partial<EncryptionParams> = {}) {
    const { iv, key = defaultKey, useHex = true } = opt;
    if (key) this.key = parse(key);
    if (iv) this.iv = parse(iv);
    this.useHex = Boolean(useHex);
  }

  decryptByAES(cipherText: string) {
    const realCipherText = this.useHex ? Base64.stringify(Hex.parse(cipherText)) : cipherText;
    return CryptoJS.AES.decrypt(realCipherText, this.key as any, this.getOptions()).toString(UTF8);
  }

  encryptByAES(cipherText: string) {
    const result = CryptoJS.AES.encrypt(cipherText, this.key as any, this.getOptions()).toString();
    return this.useHex ? Hex.stringify(Base64.parse(result)) : result;
  }

  private getOptions() {
    return {
      iv: this.iv,
      mode: ECB,
      padding: pkcs7
    };
  }
}

/**
 * Base64 编码
 */
export function encryptByBase64(cipherText: string) {
  return UTF8.parse(cipherText).toString(Base64);
}

/**
 * Base64 解码
 */
export function decodeByBase64(cipherText: string) {
  return Base64.parse(cipherText).toString(UTF8);
}

/**
 * MD5 哈希
 */
export function encryptByMd5(password: string) {
  return md5(password).toString();
}

/**
 * 密码加密（SSO登录专用）
 * 按照SSO原项目实现：MD5(密码) → AES-ECB加密 → Hex编码
 * @param password 明文密码
 * @returns 加密后的密码（Hex格式）
 *
 * 加密流程：
 * 1. 对明文密码进行 MD5 加密
 * 2. 使用 AES-ECB 模式加密（密钥为 MD5(VITE_CIPHER_KEY)）
 * 3. 将加密结果（Base64）转换为 Hex 格式
 */
export function encryptPassword(password: string): string {
  // 1. 先对原始密码进行 MD5 加密
  const md5Password = encryptByMd5(password);

  // 2. 再对 MD5 结果进行 AES-ECB 加密
  const aes = new AesEncryption();
  const result = aes.encryptByAES(md5Password);

  return result;
}

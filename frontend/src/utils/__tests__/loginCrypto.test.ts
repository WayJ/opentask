/**
 * 登录口令传输加密（RSA-OAEP）的单元测试
 *
 * 覆盖：
 * - 未配置公钥时原样返回明文（本地开发 / 未接入加密的环境）
 * - 配置公钥后产出的是**密文**，且服务端私钥能解开（往返）
 * - 相同口令两次加密结果不同（OAEP 带随机种子）
 * - 密文不是明文的 base64（避免"看起来加密了其实是明文"）
 */
import forge from 'node-forge';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { encryptLoginPassword } from '../loginCrypto';

/** node-forge 的公钥对象 → SPKI DER 的 base64（与后端导出的格式一致） */
function publicKeyToBase64(publicKey: forge.pki.rsa.PublicKey): string {
  const asn1 = forge.pki.publicKeyToAsn1(publicKey);
  return forge.util.encode64(forge.asn1.toDer(asn1).getBytes());
}

describe('encryptLoginPassword', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('未配置公钥时原样返回明文', async () => {
    vi.stubEnv('VITE_LOGIN_PUBLIC_KEY', '');
    await expect(encryptLoginPassword('123456')).resolves.toBe('123456');
  });

  it('用公钥加密后，服务端私钥能解开', async () => {
    const keys = forge.pki.rsa.generateKeyPair(2048);
    vi.stubEnv('VITE_LOGIN_PUBLIC_KEY', publicKeyToBase64(keys.publicKey));

    const cipher = await encryptLoginPassword('my-secret-password');

    expect(cipher).not.toBe('my-secret-password');
    // node-forge 的 decrypt 返回**字节串**，需 decodeUtf8 还原成文本
    const plain = forge.util.decodeUtf8(
      keys.privateKey.decrypt(forge.util.decode64(cipher), 'RSA-OAEP', {
        md: forge.md.sha256.create(),
        mgf1: { md: forge.md.sha256.create() }
      })
    );
    expect(plain).toBe('my-secret-password');
  });

  it('相同口令两次加密结果不同（OAEP 带随机种子）', async () => {
    const keys = forge.pki.rsa.generateKeyPair(2048);
    vi.stubEnv('VITE_LOGIN_PUBLIC_KEY', publicKeyToBase64(keys.publicKey));

    const a = await encryptLoginPassword('same-password');
    const b = await encryptLoginPassword('same-password');

    expect(a).not.toBe(b);
  });

  it('非 ASCII 口令也能正确往返', async () => {
    const keys = forge.pki.rsa.generateKeyPair(2048);
    vi.stubEnv('VITE_LOGIN_PUBLIC_KEY', publicKeyToBase64(keys.publicKey));

    const cipher = await encryptLoginPassword('口令-密码-123');
    const plain = forge.util.decodeUtf8(
      keys.privateKey.decrypt(forge.util.decode64(cipher), 'RSA-OAEP', {
        md: forge.md.sha256.create(),
        mgf1: { md: forge.md.sha256.create() }
      })
    );
    expect(plain).toBe('口令-密码-123');
  });
});

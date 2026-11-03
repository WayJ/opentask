/**
 * 登录口令的传输加密（RSA-OAEP / SHA-256）
 *
 * ## 为什么需要它
 *
 * 部署环境目前是**明文 HTTP**（没有域名就没法签 HTTPS 证书），而登录口令如果
 * 明文提交，抓包就能直接拿到账号口令——口令往往在多个系统间复用，泄露代价很大。
 *
 * ## 为什么是非对称
 *
 * 旧版的 `encrypt.ts` 用的是**共享密钥**（AES-ECB，密钥 = MD5(VITE_CIPHER_KEY)），
 * 那份密钥要打进前端 bundle，任何人打开开发者工具就能抠出来 → 「加密的口令」对
 * 中间人而言和明文没区别（这条已登记为 TD10）。
 *
 * 这里改成非对称：
 * - **私钥**只在服务端（`<DATA_DIRECTORY>/login_private.pem`，chmod 600）
 * - **公钥**打进前端 bundle（`VITE_LOGIN_PUBLIC_KEY`，SPKI DER 的 base64）
 *
 * 于是抓到密文的人，没有私钥就解不开口令。
 *
 * ## 为什么用 node-forge 而不是 Web Crypto
 *
 * `crypto.subtle` **只在安全上下文可用**（https / localhost），明文 HTTP 的页面上
 * 它是 undefined。node-forge 是纯 JS 实现，任何上下文都能用。
 *
 * ## 兼容性
 *
 * 没有配置公钥时（本地开发）原样返回明文；服务端解不开时也会回退按明文处理，
 * 因此 CLI 等未接入加密的客户端照常工作。
 */

/** base64 的 SPKI DER → PEM（node-forge 的 publicKeyFromPem 需要 PEM） */
function base64DerToPem(base64Der: string): string {
  const body = base64Der
    .replace(/\s+/g, '')
    .replace(/(.{64})/g, '$1\n')
    .replace(/\n$/, '');
  return `-----BEGIN PUBLIC KEY-----\n${body}\n-----END PUBLIC KEY-----`;
}

/**
 * 用服务端公钥加密登录口令。
 *
 * @param password 明文口令
 * @returns base64 的 RSA-OAEP 密文；未配置公钥时原样返回明文
 */
export async function encryptLoginPassword(password: string): Promise<string> {
  const publicKeyB64 = import.meta.env.VITE_LOGIN_PUBLIC_KEY;
  if (!publicKeyB64) {
    // 未注入公钥（本地开发 / 未接入加密的环境）→ 明文提交，服务端同样回退按明文处理
    return password;
  }

  const forge = await import('node-forge');
  const key = forge.pki.publicKeyFromPem(base64DerToPem(publicKeyB64));

  // OAEP 的摘要与 MGF1 摘要都用 SHA-256（与服务端 login_crypto.py 一致）
  const data = forge.util.encodeUtf8(password);
  const encrypted = key.encrypt(data, 'RSA-OAEP', {
    md: forge.md.sha256.create(),
    mgf1: { md: forge.md.sha256.create() }
  });

  return forge.util.encode64(encrypted);
}

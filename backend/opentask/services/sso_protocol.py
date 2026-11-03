"""上游用户中心（SSO）的协议字面量。

**本模块是全仓唯一保留上游品牌字样的地方。**

背景：本项目对接的是一套外部用户中心（SSO）系统，它的 HTTP 协议里有两处字段名
是上游自己定的、由上游实现强制要求的——我们这边**改了就对端不认**：

- 请求头 ``Jnpf-Origin``：上游用它识别调用端（PC / APP）
- 登录请求体字段 ``jnpf_ticket``：上游登录接口的表单字段之一

因此把这两个字面量集中到本模块，其余代码一律引用常量，仓内其余位置的
品牌字样已全部清掉（见本次改名的说明）。若将来换掉上游对接方，删掉本模块、
把这两处替换成新协议的字段名即可。

其余上游返回字段（``userInfo`` / ``userAccount`` / ``organizeId`` / ``positionId`` …）
本身不带品牌字样，直接按原样使用即可，无需在此声明。
"""

# 上游要求的客户端标识请求头
UPSTREAM_CLIENT_HEADER = "Jnpf-Origin"

# 上游登录接口的表单字段（票据，密码登录时为空）
UPSTREAM_TICKET_FIELD = "jnpf_ticket"

# 上游「当前用户」接口路径
UPSTREAM_CURRENT_USER_PATH = "/api/oauth/CurrentUser"

# 上游「登录」接口路径
UPSTREAM_LOGIN_PATH = "/api/oauth/Login"

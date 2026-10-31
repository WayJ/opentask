# AI 助手组件使用说明

## 组件位置
`frontend/src/components/AiAssistant.vue`

## 功能特性

### 1. 视觉设计
- **折叠状态**: 右下角半圆形机器人按钮，带脉冲动画
- **展开状态**: 圆角聊天窗口，带渐变色头部
- **响应式**: 支持移动端适配

### 2. 交互功能
- **点击展开/收起**: 流畅的弹跳动画效果
- **窗口尺寸**: 4种尺寸可选
  - 小窗口: 380x520px
  - 中窗口: 450x600px (默认)
  - 大窗口: 550x700px
  - 全屏: 75% 宽度, 自适应高度
- **控制按钮**: 缩小、放大、全屏、关闭

### 3. 技术实现
- **图标库**: 使用 @iconify/vue (项目已有依赖)
- **样式**: SCSS + CSS3 动画
- **框架**: Vue 3 Composition API

## 配置说明

### 修改 iframe URL

编辑 `AiAssistant.vue` 第 172 行，修改 iframe 的 src 属性：

```vue
<iframe
  src="http://localhost:5173/"  <!-- 修改为你的 AI 聊天服务地址 -->
  frameborder="0"
  class="chat-iframe"
  @load="onIframeLoad"
  allow="microphone; camera"
></iframe>
```

### 常见 URL 配置示例

1. **本地开发服务**:
   ```vue
   src="http://localhost:5173/"
   ```

2. **生产环境服务**:
   ```vue
   src="https://your-ai-service.com/"
   ```

3. **相对路径**:
   ```vue
   src="/ai-chat/"
   ```

4. **其他端口**:
   ```vue
   src="http://localhost:3000/"
   ```

## 自定义样式

### 修改主题色

编辑 `AiAssistant.vue` 的 SCSS 样式部分：

```scss
// 机器人图标背景色 (第 227 行)
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

// 窗口头部渐变色 (第 365 行)
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

// 脉冲动画边框色 (第 287 行)
border: 2px solid #667eea;
```

### 修改按钮位置

编辑第 196 行：

```scss
.ai-assistant-container {
  position: fixed;
  right: 0;        // 改为 left: 0; 可放到左侧
  bottom: 80px;    // 调整垂直位置
  z-index: 9999;
}
```

## 启动步骤

1. **确保 AI 聊天服务运行**
   - 如果使用本地服务，先启动聊天应用
   - 例如: `cd extensions/chatapp && npm run dev`

2. **启动前端项目**
   ```bash
   cd frontend
   bun run dev
   ```

3. **访问应用**
   - 打开浏览器访问 `http://localhost:9528`
   - 点击右下角的机器人图标

## 注意事项

1. **跨域问题**: 确保 iframe 源支持跨域访问
2. **权限设置**: `allow="microphone; camera"` 用于语音/视频功能
3. **响应式**: 移动端会自动调整窗口大小
4. **性能**: iframe 加载可能需要时间，建议添加 loading 状态

## 扩展功能建议

1. **消息通知**: 添加未读消息提示
2. **快捷键**: 支持键盘快捷键打开/关闭
3. **主题切换**: 支持暗色模式
4. **持久化**: 记住用户的窗口大小偏好
5. **拖拽**: 支持拖拽移动窗口位置

## 依赖说明

此组件**不依赖 Element Plus**，使用项目已有的 @iconify/vue 图标库，无需额外安装依赖。

## 故障排查

### 1. 组件不显示
- 检查 `App.vue` 是否正确导入和注册组件
- 检查 z-index 是否被其他元素覆盖

### 2. iframe 无法加载
- 检查目标服务是否正在运行
- 检查浏览器控制台是否有跨域错误
- 确认 URL 地址正确

### 3. 动画卡顿
- 检查浏览器性能
- 考虑禁用部分动画效果

## 参考资源

- 原始组件: `D:\projects\accs-auto-coding\accs-web-dispose\src\components\AiAssistant.vue`
- Iconify 图标库: https://iconify.design/

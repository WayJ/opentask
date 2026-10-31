# EditableField 可编辑字段组件

## 功能
一个现代化的可编辑字段组件，支持：
- 点击编辑按钮切换到编辑模式
- 使用下拉选择器编辑值
- 保存/取消操作，带有大图标按钮
- 悬停效果和动画
- 支持自定义图标插槽
- 支持标签显示（Tag）

## 使用示例

```vue
<EditableField
  v-model="tempValue"
  v-model:editing="isEditing"
  label="状态"
  :display-value="displayText"
  :options="options"
  :tag-type="tagType"
  @save="handleSave"
  @cancel="handleCancel"
  @start-edit="tempValue = currentValue"
>
  <template #label-icon>
    <icon-mdi-checkbox-marked-circle />
  </template>
</EditableField>
```

## Props
- `modelValue`: 绑定的值
- `editing`: 编辑状态
- `label`: 字段标签
- `displayValue`: 显示的文本值
- `options`: 下拉选项数组
- `tagType`: 标签类型（用于 Tag 组件）
- `placeholder`: 占位符文本
- `selectWidth`: 下拉框宽度
- `loading`: 加载状态
- `clearable`: 是否可清除

## Events
- `update:modelValue`: 值更新
- `update:editing`: 编辑状态更新
- `save`: 保存事件
- `cancel`: 取消事件
- `startEdit`: 开始编辑事件

## Slots
- `label-icon`: 标签图标
- `editor`: 自定义编辑器

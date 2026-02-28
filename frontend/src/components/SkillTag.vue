<template>
  <span
    :class="['skill-tag', `skill-tag--${level}`, { 'skill-tag--active': isActive }, customClass]"
    @click="$emit('click')"
  >
    <el-icon v-if="icon" class="skill-tag__icon">
      <component :is="icon" />
    </el-icon>
    <span class="skill-tag__text">{{ label }}</span>
    <span v-if="matchPercentage" class="skill-tag__percentage">{{ matchPercentage }}%</span>
    <el-icon v-if="closable" class="skill-tag__close" @click.stop="handleClose">
      <Close />
    </el-icon>
  </span>
</template>

<script setup lang="ts">
import { Close } from '@element-plus/icons-vue';

export interface SkillTagProps {
  label: string;
  level?: 'primary' | 'secondary' | 'tertiary' | 'success' | 'info';
  matchPercentage?: number;
  isActive?: boolean;
  closable?: boolean;
  icon?: string;
  customClass?: string;
  type?: string;
}

withDefaults(defineProps<SkillTagProps>(), {
  level: 'primary',
  matchPercentage: undefined,
  isActive: false,
  closable: false,
  icon: undefined,
  customClass: '',
  type: undefined
});

const emit = defineEmits<{
  close: [];
  click: [];
}>();

const handleClose = () => {
  emit('close');
};
</script>

<style scoped lang="scss">
.skill-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  margin: 2px 3px;
  cursor: default;
  transition: all 0.2s;
  white-space: nowrap;
  border: 1px solid transparent;

  // 默认 primary：蓝紫色描边，深色半透明背景
  &--primary {
    background: rgba(99, 102, 241, 0.15);
    border-color: rgba(99, 102, 241, 0.5);
    color: #c7d2fe;

    &:hover {
      background: rgba(99, 102, 241, 0.28);
      border-color: rgba(99, 102, 241, 0.8);
    }
  }

  // secondary：青色/绿色描边
  &--secondary {
    background: rgba(20, 184, 166, 0.15);
    border-color: rgba(20, 184, 166, 0.5);
    color: #99f6e4;

    &:hover {
      background: rgba(20, 184, 166, 0.25);
    }
  }

  // tertiary：灰色描边，低调
  &--tertiary {
    background: rgba(148, 163, 184, 0.1);
    border-color: rgba(148, 163, 184, 0.3);
    color: #94a3b8;
    font-size: 11px;

    &:hover {
      background: rgba(148, 163, 184, 0.18);
    }
  }

  // success：绿色描边
  &--success {
    background: rgba(34, 197, 94, 0.15);
    border-color: rgba(34, 197, 94, 0.5);
    color: #86efac;
  }

  // info：蓝灰色
  &--info {
    background: rgba(96, 165, 250, 0.12);
    border-color: rgba(96, 165, 250, 0.4);
    color: #93c5fd;
  }

  // 激活状态：填充色背景
  &--active {
    background: rgba(99, 102, 241, 0.35);
    border-color: #6366f1;
    color: #e0e7ff;
    font-weight: 600;
  }

  &__icon {
    font-size: 11px;
    opacity: 0.9;
  }

  &__text {
    line-height: 1;
  }

  &__percentage {
    font-size: 11px;
    opacity: 0.75;
    margin-left: 2px;
  }

  &__close {
    font-size: 11px;
    cursor: pointer;
    opacity: 0.6;
    margin-left: 2px;

    &:hover {
      opacity: 1;
    }
  }
}
</style>
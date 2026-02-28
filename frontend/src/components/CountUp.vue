<template>
  <span>{{ displayValue }}</span>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';

interface Props {
  endVal: number;
  duration?: number; // 动画持续时间（秒）
  decimals?: number; // 小数位数
  prefix?: string; // 前缀
  suffix?: string; // 后缀
}

const props = withDefaults(defineProps<Props>(), {
  duration: 2,
  decimals: 0,
  prefix: '',
  suffix: ''
});

const formatNumber = (num: number): string => {
  return num.toFixed(props.decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

const displayValue = ref(props.prefix + formatNumber(0) + props.suffix);

let startTime: number | null = null;
let rafId: number | null = null;

const animate = (timestamp: number) => {
  if (!startTime) startTime = timestamp;
  const progress = timestamp - startTime;
  const percentage = Math.min(progress / (props.duration * 1000), 1);
  const currentValue = percentage * props.endVal;
  
  displayValue.value = props.prefix + formatNumber(currentValue) + props.suffix;
  
  if (percentage < 1) {
    rafId = requestAnimationFrame(animate);
  } else {
    displayValue.value = props.prefix + formatNumber(props.endVal) + props.suffix;
  }
};

const startAnimation = () => {
  startTime = null;
  if (rafId) {
    cancelAnimationFrame(rafId);
  }
  rafId = requestAnimationFrame(animate);
};

watch(() => props.endVal, () => {
  startAnimation();
});

onMounted(() => {
  startAnimation();
});
</script>
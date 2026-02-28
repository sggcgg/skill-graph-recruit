"""
机器学习模块
包含主动学习、知识蒸馏等先进技术
"""
from .active_learning_sampler import ActiveLearningSampler
from .knowledge_distillation import SkillDistillationModel

__all__ = [
    'ActiveLearningSampler',
    'SkillDistillationModel',
]

"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, DECIMAL, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.database import Base
from datetime import datetime


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联关系
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resume = relationship("UserResume", back_populates="user", uselist=False, cascade="all, delete-orphan")
    skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("MatchReport", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    """用户资料表"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(100))
    email = Column(String(100))          # 冗余存储邮箱，方便资料页展示
    phone = Column(String(20))
    city = Column(String(50))
    position = Column(String(100))
    avatar_url = Column(String(255))
    bio = Column(Text)
    job_status = Column(String(50), default='active')   # 求职状态
    experience_years = Column(Integer, default=0)        # 工作年限
    school = Column(String(100))
    major = Column(String(100))
    degree = Column(String(50))
    github_url = Column(String(255))
    linkedin_url = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联关系
    user = relationship("User", back_populates="profile")


class UserResume(Base):
    """用户简历表"""
    __tablename__ = "user_resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(100))
    school = Column(String(100))
    major = Column(String(100))
    degree = Column(String(50))
    skills = Column(JSON)  # 存储技能数组
    expect_cities = Column(JSON)  # 存储期望城市数组
    expect_salary_min = Column(Integer)
    expect_salary_max = Column(Integer)
    work_experience = Column(Text)
    projects = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联关系
    user = relationship("User", back_populates="resume")


class UserSkill(Base):
    """用户技能表"""
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_name = Column(String(100), nullable=False)
    proficiency_level = Column(Integer, default=1)  # 1-5等级
    last_used = Column(Date)
    years_of_experience = Column(DECIMAL(3, 1))  # 小数形式的工作年限
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联关系
    user = relationship("User", back_populates="skills")


class UserFavorite(Base):
    """用户收藏岗位表"""
    __tablename__ = "user_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(String(100), nullable=False)  # 外部招聘数据的job_id
    title = Column(String(255))
    company = Column(String(255))
    salary_range = Column(String(100))
    city = Column(String(50))
    skills = Column(JSON)  # 岗位技能要求
    created_at = Column(DateTime, default=func.now())

    # 设置唯一约束，防止重复收藏
    __table_args__ = (
        # 确保同一用户不能重复收藏同一个岗位
        {'sqlite_autoincrement': True},
    )

    # 关联关系
    user = relationship("User", back_populates="favorites")


class MatchReport(Base):
    """匹配报告表"""
    __tablename__ = "match_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_title = Column(String(255))
    target_position = Column(String(100))
    match_rate = Column(DECIMAL(5, 2))  # 匹配度百分比
    summary = Column(Text)
    recommendations = Column(Text)  # 改进建议
    skills_gap = Column(JSON)  # 技能差距
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联关系
    user = relationship("User", back_populates="reports")


class UserSetting(Base):
    """用户设置表"""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    notifications_enabled = Column(Boolean, default=True)
    email_subscription = Column(Boolean, default=True)
    theme_preference = Column(String(20), default='dark')  # dark/light/auto
    language = Column(String(10), default='zh-CN')
    privacy_level = Column(String(20), default='private')  # public/friends/private
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联关系
    user = relationship("User", back_populates="settings")
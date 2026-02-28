"""
认证相关的Pydantic模型
"""
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import date
from decimal import Decimal


class Token(BaseModel):
    """JWT令牌模型"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = None


class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: EmailStr


class UserCreate(UserBase):
    """用户创建模型"""
    password: str


class UserUpdate(BaseModel):
    """用户更新模型"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class UserProfileBase(BaseModel):
    """用户资料基础模型"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    position: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    job_status: Optional[str] = None
    experience_years: Optional[int] = None
    school: Optional[str] = None
    major: Optional[str] = None
    degree: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class UserProfileCreate(UserProfileBase):
    """用户资料创建模型"""
    user_id: int


class UserProfileUpdate(UserProfileBase):
    """用户资料更新模型"""
    pass


class UserProfileInDB(UserProfileBase):
    """数据库中的用户资料模型"""
    id: int
    user_id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserResumeBase(BaseModel):
    """用户简历基础模型"""
    name: Optional[str] = None
    school: Optional[str] = None
    major: Optional[str] = None
    degree: Optional[str] = None
    skills: Optional[List[str]] = None
    expect_cities: Optional[List[str]] = None
    expect_salary_min: Optional[int] = None
    expect_salary_max: Optional[int] = None
    work_experience: Optional[str] = None
    projects: Optional[str] = None


class UserResumeCreate(UserResumeBase):
    """用户简历创建模型"""
    user_id: int


class UserResumeUpdate(UserResumeBase):
    """用户简历更新模型"""
    pass


class UserResumeInDB(UserResumeBase):
    """数据库中的用户简历模型"""
    id: int
    user_id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserSkillBase(BaseModel):
    """用户技能基础模型"""
    skill_name: str
    proficiency_level: Optional[int] = 1  # 1-5等级
    last_used: Optional[date] = None
    years_of_experience: Optional[Decimal] = None


class UserSkillCreate(UserSkillBase):
    """用户技能创建模型"""
    user_id: int


class UserSkillUpdate(BaseModel):
    """用户技能更新模型"""
    proficiency_level: Optional[int] = None
    last_used: Optional[date] = None
    years_of_experience: Optional[Decimal] = None


class UserSkillInDB(UserSkillBase):
    """数据库中的用户技能模型"""
    id: int
    user_id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserFavoriteBase(BaseModel):
    """用户收藏基础模型"""
    job_id: str
    title: str
    company: str
    salary_range: Optional[str] = None
    city: Optional[str] = None
    skills: Optional[List[str]] = None


class UserFavoriteCreate(UserFavoriteBase):
    """用户收藏创建模型"""
    user_id: int


class UserFavoriteInDB(UserFavoriteBase):
    """数据库中的用户收藏模型"""
    id: int
    user_id: int
    created_at: str

    class Config:
        from_attributes = True


class MatchReportBase(BaseModel):
    """匹配报告基础模型"""
    report_title: Optional[str] = None
    target_position: str
    match_rate: Optional[Decimal] = None
    summary: Optional[str] = None
    recommendations: Optional[str] = None
    skills_gap: Optional[List[dict]] = None


class MatchReportCreate(MatchReportBase):
    """匹配报告创建模型"""
    user_id: int


class MatchReportUpdate(BaseModel):
    """匹配报告更新模型"""
    report_title: Optional[str] = None
    match_rate: Optional[Decimal] = None
    summary: Optional[str] = None
    recommendations: Optional[str] = None
    skills_gap: Optional[List[dict]] = None


class MatchReportInDB(MatchReportBase):
    """数据库中的匹配报告模型"""
    id: int
    user_id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserSettingBase(BaseModel):
    """用户设置基础模型"""
    notifications_enabled: Optional[bool] = True
    email_subscription: Optional[bool] = True
    theme_preference: Optional[str] = "dark"  # dark/light/auto
    language: Optional[str] = "zh-CN"
    privacy_level: Optional[str] = "private"  # public/friends/private


class UserSettingCreate(UserSettingBase):
    """用户设置创建模型"""
    user_id: int


class UserSettingUpdate(UserSettingBase):
    """用户设置更新模型"""
    pass


class UserSettingInDB(UserSettingBase):
    """数据库中的用户设置模型"""
    id: int
    user_id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class LoginResponse(Token):
    """登录响应模型"""
    user: UserInDB
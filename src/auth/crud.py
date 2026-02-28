"""
用户相关数据库操作
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import date
from decimal import Decimal
from src.database.models import User, UserProfile, UserResume, UserSkill, UserFavorite, MatchReport, UserSetting
from src.auth.schemas import (
    UserCreate, UserUpdate, UserProfileCreate, UserProfileUpdate,
    UserResumeCreate, UserResumeUpdate, UserSkillCreate, UserSkillUpdate,
    UserFavoriteCreate, UserFavoriteInDB, MatchReportCreate, MatchReportUpdate,
    UserSettingCreate, UserSettingUpdate
)
from src.auth.security import get_password_hash
from fastapi import HTTPException, status


# 用户操作
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user: UserCreate) -> User:
    """创建用户"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或邮箱已存在"
        )


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """更新用户"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None

    if user_update.username:
        db_user.username = user_update.username
    if user_update.email:
        db_user.email = user_update.email
    if user_update.password:
        db_user.hashed_password = get_password_hash(user_update.password)

    db.commit()
    db.refresh(db_user)
    return db_user


# 用户资料操作
def get_user_profile(db: Session, user_id: int) -> Optional[UserProfile]:
    """获取用户资料"""
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def create_user_profile(db: Session, profile: UserProfileCreate) -> UserProfile:
    """创建用户资料"""
    db_profile = UserProfile(**profile.dict(exclude={'user_id'}), user_id=profile.user_id)
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def update_user_profile(db: Session, user_id: int, profile_update: UserProfileUpdate) -> Optional[UserProfile]:
    """更新用户资料"""
    db_profile = get_user_profile(db, user_id)
    if not db_profile:
        return None

    for field, value in profile_update.dict(exclude_unset=True).items():
        setattr(db_profile, field, value)

    db.commit()
    db.refresh(db_profile)
    return db_profile


# 用户简历操作
def get_user_resume(db: Session, user_id: int) -> Optional[UserResume]:
    """获取用户简历"""
    return db.query(UserResume).filter(UserResume.user_id == user_id).first()


def create_user_resume(db: Session, resume: UserResumeCreate) -> UserResume:
    """创建用户简历"""
    db_resume = UserResume(**resume.dict(exclude={'user_id'}), user_id=resume.user_id)
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return db_resume


def update_user_resume(db: Session, user_id: int, resume_update: UserResumeUpdate) -> Optional[UserResume]:
    """更新用户简历"""
    db_resume = get_user_resume(db, user_id)
    if not db_resume:
        return None

    for field, value in resume_update.dict(exclude_unset=True).items():
        setattr(db_resume, field, value)

    db.commit()
    db.refresh(db_resume)
    return db_resume


# 用户技能操作
def get_user_skills(db: Session, user_id: int) -> List[UserSkill]:
    """获取用户所有技能"""
    return db.query(UserSkill).filter(UserSkill.user_id == user_id).all()


def get_user_skill_by_name(db: Session, user_id: int, skill_name: str) -> Optional[UserSkill]:
    """根据技能名称获取用户技能"""
    return db.query(UserSkill).filter(
        UserSkill.user_id == user_id,
        UserSkill.skill_name == skill_name
    ).first()


def create_user_skill(db: Session, skill: UserSkillCreate) -> UserSkill:
    """创建用户技能"""
    db_skill = UserSkill(**skill.dict(exclude={'user_id'}), user_id=skill.user_id)
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill


def update_user_skill(db: Session, user_id: int, skill_name: str, skill_update: UserSkillUpdate) -> Optional[UserSkill]:
    """更新用户技能"""
    db_skill = get_user_skill_by_name(db, user_id, skill_name)
    if not db_skill:
        return None

    for field, value in skill_update.dict(exclude_unset=True).items():
        setattr(db_skill, field, value)

    db.commit()
    db.refresh(db_skill)
    return db_skill


def delete_user_skill(db: Session, user_id: int, skill_name: str) -> bool:
    """删除用户技能"""
    db_skill = get_user_skill_by_name(db, user_id, skill_name)
    if not db_skill:
        return False

    db.delete(db_skill)
    db.commit()
    return True


# 用户收藏操作
def get_user_favorites(db: Session, user_id: int) -> List[UserFavorite]:
    """获取用户收藏的所有岗位"""
    return db.query(UserFavorite).filter(UserFavorite.user_id == user_id).all()


def get_user_favorite_by_job_id(db: Session, user_id: int, job_id: str) -> Optional[UserFavorite]:
    """根据岗位ID获取用户收藏"""
    return db.query(UserFavorite).filter(
        UserFavorite.user_id == user_id,
        UserFavorite.job_id == job_id
    ).first()


def create_user_favorite(db: Session, favorite: UserFavoriteCreate) -> UserFavorite:
    """创建用户收藏"""
    db_favorite = UserFavorite(**favorite.dict(exclude={'user_id'}), user_id=favorite.user_id)
    try:
        db.add(db_favorite)
        db.commit()
        db.refresh(db_favorite)
        return db_favorite
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该岗位已被收藏"
        )


def delete_user_favorite(db: Session, user_id: int, job_id: str) -> bool:
    """删除用户收藏"""
    db_favorite = get_user_favorite_by_job_id(db, user_id, job_id)
    if not db_favorite:
        return False

    db.delete(db_favorite)
    db.commit()
    return True


# 匹配报告操作
def get_match_reports(db: Session, user_id: int) -> List[MatchReport]:
    """获取用户的所有匹配报告"""
    return db.query(MatchReport).filter(MatchReport.user_id == user_id).all()


def get_match_report_by_id(db: Session, report_id: int) -> Optional[MatchReport]:
    """根据ID获取匹配报告"""
    return db.query(MatchReport).filter(MatchReport.id == report_id).first()


def create_match_report(db: Session, report: MatchReportCreate) -> MatchReport:
    """创建匹配报告"""
    db_report = MatchReport(**report.dict(exclude={'user_id'}), user_id=report.user_id)
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def update_match_report(db: Session, report_id: int, report_update: MatchReportUpdate) -> Optional[MatchReport]:
    """更新匹配报告"""
    db_report = get_match_report_by_id(db, report_id)
    if not db_report:
        return None

    for field, value in report_update.dict(exclude_unset=True).items():
        setattr(db_report, field, value)

    db.commit()
    db.refresh(db_report)
    return db_report


# 用户设置操作
def get_user_setting(db: Session, user_id: int) -> Optional[UserSetting]:
    """获取用户设置"""
    return db.query(UserSetting).filter(UserSetting.user_id == user_id).first()


def create_user_setting(db: Session, setting: UserSettingCreate) -> UserSetting:
    """创建用户设置"""
    db_setting = UserSetting(**setting.dict(exclude={'user_id'}), user_id=setting.user_id)
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting


def update_user_setting(db: Session, user_id: int, setting_update: UserSettingUpdate) -> Optional[UserSetting]:
    """更新用户设置"""
    db_setting = get_user_setting(db, user_id)
    if not db_setting:
        return None

    for field, value in setting_update.dict(exclude_unset=True).items():
        setattr(db_setting, field, value)

    db.commit()
    db.refresh(db_setting)
    return db_setting
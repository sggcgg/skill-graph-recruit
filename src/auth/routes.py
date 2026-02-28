"""
认证和用户管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List
from src.database.database import get_db
from src.database.models import User
from src.auth.schemas import (
    UserCreate, UserInDB, UserProfileInDB, UserProfileUpdate,
    UserResumeInDB, UserResumeUpdate, UserSkillInDB, UserSkillCreate, UserSkillUpdate,
    UserFavoriteInDB, UserFavoriteCreate, MatchReportInDB, MatchReportCreate, MatchReportUpdate,
    UserSettingInDB, UserSettingUpdate, LoginRequest, LoginResponse,
    UserProfileCreate, UserSettingCreate, UserResumeCreate
)
from src.auth.crud import (
    get_user_by_username, get_user_by_email, create_user,
    get_user_profile, create_user_profile, update_user_profile,
    get_user_resume, create_user_resume, update_user_resume,
    get_user_skills, create_user_skill, update_user_skill, delete_user_skill,
    get_user_favorites, create_user_favorite, delete_user_favorite,
    get_match_reports, get_match_report_by_id, create_match_report, update_match_report,
    get_user_setting, create_user_setting, update_user_setting
)
from src.auth.security import verify_password, create_access_token, get_current_user_from_token

router = APIRouter(prefix="/api/auth", tags=["authentication"])
user_router = APIRouter(prefix="/api/user", tags=["user"])

security = HTTPBearer()


def authenticate_user(db: Session, username: str, password: str):
    """验证用户身份"""
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserInDB.from_orm(user)
    }


@router.post("/register", response_model=UserInDB)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名或邮箱是否已存在
    existing_user = get_user_by_username(db, user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    existing_email = get_user_by_email(db, user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 创建用户
    db_user = create_user(db, user)
    
    # 自动创建用户资料和设置
    try:
        create_user_profile(db, UserProfileCreate(user_id=db_user.id))
        create_user_setting(db, UserSettingCreate(user_id=db_user.id))
    except Exception:
        # 如果创建默认资料或设置失败，不影响注册
        pass
    
    return UserInDB.from_orm(db_user)


# 用户资料相关API
@user_router.get("/profile", response_model=UserProfileInDB)
def get_profile(
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """获取用户资料；若记录不存在则自动创建默认资料（兼容老用户）"""
    user_id = get_current_user_from_token(token)
    profile = get_user_profile(db, user_id)
    if not profile:
        # 老用户注册时可能未自动建 profile，这里按需创建
        profile = create_user_profile(db, UserProfileCreate(user_id=user_id))
    # 从 users 表补充 email（email 存在 users，profile 里初始为空）
    if not profile.email:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            profile.email = user.email
            db.commit()
    return UserProfileInDB.from_orm(profile)


@user_router.put("/profile", response_model=UserProfileInDB)
def update_profile(
    profile_update: UserProfileUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """更新用户资料；若记录不存在则先创建再更新（upsert）"""
    user_id = get_current_user_from_token(token)
    profile = update_user_profile(db, user_id, profile_update)
    if not profile:
        # 先补建默认 profile，再应用更新
        create_user_profile(db, UserProfileCreate(user_id=user_id))
        profile = update_user_profile(db, user_id, profile_update)
    if not profile:
        raise HTTPException(status_code=500, detail="用户资料创建失败")
    return UserProfileInDB.from_orm(profile)


# 用户简历相关API
@user_router.get("/resume", response_model=UserResumeInDB)
def get_resume(
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """获取用户简历"""
    user_id = get_current_user_from_token(token)
    resume = get_user_resume(db, user_id)
    if not resume:
        raise HTTPException(status_code=404, detail="用户简历未找到")
    return UserResumeInDB.from_orm(resume)


@user_router.put("/resume", response_model=UserResumeInDB)
def update_resume(
    resume_update: UserResumeUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """更新用户简历（不存在时自动创建）"""
    user_id = get_current_user_from_token(token)
    existing = get_user_resume(db, user_id)
    if not existing:
        # 简历不存在则创建
        create_data = UserResumeCreate(user_id=user_id, **resume_update.dict(exclude_unset=True))
        resume = create_user_resume(db, create_data)
    else:
        resume = update_user_resume(db, user_id, resume_update)
    if not resume:
        raise HTTPException(status_code=500, detail="简历操作失败")
    return UserResumeInDB.from_orm(resume)


# 用户技能相关API
@user_router.get("/skills", response_model=List[UserSkillInDB])
def get_skills(
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """获取用户技能列表"""
    user_id = get_current_user_from_token(token)
    skills = get_user_skills(db, user_id)
    return [UserSkillInDB.from_orm(skill) for skill in skills]


@user_router.post("/skills", response_model=UserSkillInDB)
def add_skill(
    skill: UserSkillCreate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """添加用户技能"""
    user_id = get_current_user_from_token(token)
    # 验证请求中的user_id是否与当前用户一致
    if skill.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权限操作")
    db_skill = create_user_skill(db, skill)
    return UserSkillInDB.from_orm(db_skill)


@user_router.put("/skills/{skill_name}", response_model=UserSkillInDB)
def update_skill(
    skill_name: str,
    skill_update: UserSkillUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """更新用户技能"""
    user_id = get_current_user_from_token(token)
    skill = update_user_skill(db, user_id, skill_name, skill_update)
    if not skill:
        raise HTTPException(status_code=404, detail="技能未找到")
    return UserSkillInDB.from_orm(skill)


@user_router.delete("/skills/{skill_name}")
def remove_skill(
    skill_name: str,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """删除用户技能"""
    user_id = get_current_user_from_token(token)
    success = delete_user_skill(db, user_id, skill_name)
    if not success:
        raise HTTPException(status_code=404, detail="技能未找到")
    return {"message": "技能删除成功"}


# 用户收藏相关API
@user_router.get("/favorites", response_model=List[UserFavoriteInDB])
def get_favorites(
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """获取用户收藏的岗位"""
    user_id = get_current_user_from_token(token)
    favorites = get_user_favorites(db, user_id)
    return [UserFavoriteInDB.from_orm(fav) for fav in favorites]


@user_router.post("/favorites", response_model=UserFavoriteInDB)
def add_favorite(
    favorite: UserFavoriteCreate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """添加收藏岗位"""
    user_id = get_current_user_from_token(token)
    # 验证请求中的user_id是否与当前用户一致
    if favorite.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权限操作")
    db_favorite = create_user_favorite(db, favorite)
    return UserFavoriteInDB.from_orm(db_favorite)


@user_router.delete("/favorites/{job_id}")
def remove_favorite(
    job_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """取消收藏岗位"""
    user_id = get_current_user_from_token(token)
    success = delete_user_favorite(db, user_id, job_id)
    if not success:
        raise HTTPException(status_code=404, detail="收藏记录未找到")
    return {"message": "收藏已取消"}


# 匹配报告相关API
@user_router.get("/reports", response_model=List[MatchReportInDB])
def get_reports(
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """获取用户匹配报告"""
    user_id = get_current_user_from_token(token)
    reports = get_match_reports(db, user_id)
    return [MatchReportInDB.from_orm(report) for report in reports]


@user_router.post("/reports", response_model=MatchReportInDB)
def create_report(
    report: MatchReportCreate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """创建匹配报告"""
    user_id = get_current_user_from_token(token)
    # 验证请求中的user_id是否与当前用户一致
    if report.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权限操作")
    db_report = create_match_report(db, report)
    return MatchReportInDB.from_orm(db_report)


@user_router.put("/reports/{report_id}", response_model=MatchReportInDB)
def update_report(
    report_id: int,
    report_update: MatchReportUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """更新匹配报告"""
    # 验证用户是否有权限修改此报告
    db_report = get_match_report_by_id(db, report_id)
    user_id = get_current_user_from_token(token)
    if not db_report or db_report.user_id != user_id:
        raise HTTPException(status_code=404, detail="匹配报告未找到")
    
    updated_report = update_match_report(db, report_id, report_update)
    if not updated_report:
        raise HTTPException(status_code=404, detail="匹配报告未找到")
    return MatchReportInDB.from_orm(updated_report)


# 用户设置相关API
@user_router.get("/settings", response_model=UserSettingInDB)
def get_settings(
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """获取用户设置"""
    user_id = get_current_user_from_token(token)
    setting = get_user_setting(db, user_id)
    if not setting:
        raise HTTPException(status_code=404, detail="用户设置未找到")
    return UserSettingInDB.from_orm(setting)


@user_router.put("/settings", response_model=UserSettingInDB)
def update_settings(
    setting_update: UserSettingUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """更新用户设置"""
    user_id = get_current_user_from_token(token)
    setting = update_user_setting(db, user_id, setting_update)
    if not setting:
        raise HTTPException(status_code=404, detail="用户设置未找到")
    return UserSettingInDB.from_orm(setting)


# 将路由器添加到主应用
def include_auth_routes(app):
    """将认证路由添加到FastAPI应用"""
    app.include_router(router)
    app.include_router(user_router)
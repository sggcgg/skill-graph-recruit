"""
数据库初始化脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径 - 修正版本
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# 也可以尝试添加当前目录
sys.path.insert(0, str(script_dir))

from src.database.database import init_db, test_connection
from src.database.models import User, UserProfile, UserResume, UserSkill, UserFavorite, MatchReport, UserSetting

def init_database():
    """初始化数据库"""
    print("🔍 检测数据库连接...")
    if test_connection():
        print("✅ 数据库连接正常")
    else:
        print("❌ 数据库连接失败，请检查配置")
        print("💡 提示：请确保MySQL服务正在运行，并且config.yaml中的数据库配置正确")
        return False
    
    print("\n🏗️ 开始初始化数据库表...")
    try:
        init_db()
        print("✅ 数据库表初始化完成")
        
        # 验证表是否创建成功
        from sqlalchemy import inspect
        from src.database.database import engine
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'users', 'user_profiles', 'user_resumes', 'user_skills',
            'user_favorites', 'match_reports', 'user_settings'
        ]
        
        print(f"\n📋 已创建的表: {tables}")
        
        missing_tables = [table for table in expected_tables if table not in tables]
        if missing_tables:
            print(f"⚠️  以下表未创建: {missing_tables}")
        else:
            print("✅ 所有预期的表都已成功创建")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("🔧 MySQL数据库初始化脚本")
    print("="*60)
    
    success = init_database()
    
    if success:
        print("\n🎉 数据库初始化成功！")
        print("💡 现在您可以启动API服务，用户注册和登录功能将可用")
    else:
        print("\n💥 数据库初始化失败！")
        print("💡 请检查错误信息并重试")
        sys.exit(1)
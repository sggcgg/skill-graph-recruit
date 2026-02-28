"""
API服务启动脚本
"""
import sys
from pathlib import Path
import logging

# 添加项目根目录到path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    import uvicorn
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    api_config = config.get('api', {})
    
    print("="*80)
    print("🚀 启动智能招聘分析API服务")
    print("="*80)
    print(f"\n服务地址: http://{api_config.get('host', '0.0.0.0')}:{api_config.get('port', 8000)}")
    print(f"API文档: http://localhost:{api_config.get('port', 8000)}/docs")
    print(f"ReDoc文档: http://localhost:{api_config.get('port', 8000)}/redoc")
    print("\n按 Ctrl+C 停止服务")
    print("="*80 + "\n")
    
    # 启动服务
    uvicorn.run(
        "src.api.main:app",
        host=api_config.get('host', '0.0.0.0'),
        port=api_config.get('port', 8000),
        reload=api_config.get('debug', True),
        log_level="info"
    )

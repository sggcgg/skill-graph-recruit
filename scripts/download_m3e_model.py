"""
加载本地m3e-base中文Embedding模型（无需网络下载）
"""
from sentence_transformers import SentenceTransformer
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_local_m3e():
    """加载本地已下载的m3e-base模型"""
    logger.info("="*60)
    logger.info("开始加载本地m3e-base模型")
    logger.info("="*60)

    # 本地模型目录（修正为实际路径）
    model_dir = Path(__file__).parent / "models" / "m3e-base"

    # 检查目录和关键文件是否存在
    if not model_dir.exists():
        raise FileNotFoundError(f"模型目录不存在: {model_dir.absolute()}")

    required_files = ["config.json", "pytorch_model.bin", "tokenizer.json"]
    missing_files = [f for f in required_files if not (model_dir / f).exists()]
    if missing_files:
        raise FileNotFoundError(f"缺少关键模型文件: {missing_files}\n请从ModelScope下载后放入 {model_dir.absolute()}")

    try:
        # 直接加载本地模型（跳过网络下载）
        logger.info("正在加载本地模型...")
        model = SentenceTransformer(str(model_dir.absolute()))

        logger.info("")
        logger.info("="*60)
        logger.info(f"✅ 模型加载完成！")
        logger.info(f"   加载路径: {model_dir.absolute()}")
        logger.info("="*60)

        # 测试模型
        logger.info("\n【测试模型】")
        test_texts = [
            "Python后端开发工程师",
            "Java高级开发",
            "前端React开发"
        ]

        logger.info(f"测试文本: {test_texts}")
        embeddings = model.encode(test_texts)

        logger.info(f"✅ Embedding维度: {len(embeddings[0])}")
        logger.info(f"✅ 向量形状: {embeddings.shape}")
        logger.info(f"✅ 模型测试通过！")

        logger.info("\n="*60)
        logger.info("🎉 全部完成！现在可以使用向量检索功能了！")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"\n❌ 加载失败: {e}")
        raise

if __name__ == "__main__":
    load_local_m3e()
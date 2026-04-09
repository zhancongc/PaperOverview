"""
支付配置和 Alipay 服务初始化
"""
import os
import logging
import base64

logger = logging.getLogger(__name__)


def _load_public_key_from_file(base_dir: str) -> str | None:
    """从 public_key.txt 读取支付宝公钥"""
    public_key_path = os.path.join(base_dir, "public_key.txt")
    if not os.path.exists(public_key_path):
        logger.warning(f"public_key.txt 不存在: {public_key_path}")
        return None
    try:
        with open(public_key_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # 如果是纯 base64，格式化为 PEM
        if "-----BEGIN" not in content:
            content = content.replace("\n", "").replace("\r", "").replace(" ", "").strip()
            # 每 64 字符换行
            lines = []
            for i in range(0, len(content), 64):
                lines.append(content[i:i+64])
            content_with_newlines = "\n".join(lines)
            pem_content = f"-----BEGIN PUBLIC KEY-----\n{content_with_newlines}\n-----END PUBLIC KEY-----"
            logger.info("从 public_key.txt 读取并格式化支付宝公钥成功")
            return pem_content

        logger.info("从 public_key.txt 读取支付宝公钥成功")
        return content
    except Exception as e:
        logger.error(f"读取 public_key.txt 失败: {e}", exc_info=True)
        return None


def _load_private_key_from_secrets(base_dir: str) -> str | None:
    """
    从 secrets.txt 读取私钥，确保返回 PKCS#1 格式的 PEM
    alipay-sdk-python + rsa 库需要 PKCS#1 格式: -----BEGIN RSA PRIVATE KEY-----
    """
    secrets_path = os.path.join(base_dir, "secrets.txt")
    if not os.path.exists(secrets_path):
        logger.warning(f"secrets.txt 不存在: {secrets_path}")
        return None

    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 第一步：提取纯 base64 内容（移除所有标记、空白、换行）
        content = content.strip()

        # 移除 PEM 标记（如果有）
        if "-----BEGIN" in content:
            lines = content.split("\n")
            base64_lines = []
            in_key = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if "-----BEGIN" in line:
                    in_key = True
                    continue
                if "-----END" in line:
                    break
                if in_key:
                    base64_lines.append(line)
            pure_base64 = "".join(base64_lines)
        else:
            # 已经是纯内容，移除所有空白
            pure_base64 = content.replace("\n", "").replace("\r", "").replace(" ", "").strip()

        logger.info(f"提取到纯 base64 密钥，长度: {len(pure_base64)}")

        # 第二步：格式化为标准 PKCS#1 PEM
        # 每 64 字符换行
        lines = []
        for i in range(0, len(pure_base64), 64):
            lines.append(pure_base64[i:i+64])
        content_with_newlines = "\n".join(lines)

        pkcs1_pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            f"{content_with_newlines}\n"
            "-----END RSA PRIVATE KEY-----"
        )

        logger.info("secrets.txt: 已格式化为 PKCS#1 格式")
        return pkcs1_pem

    except Exception as e:
        logger.error(f"读取 secrets.txt 失败: {e}", exc_info=True)
        return None


def _resolve_cert_path(env_value: str | None, default_name: str, base_dir: str) -> str | None:
    """解析证书路径：环境变量优先，相对路径基于 base_dir 解析"""
    if env_value is None:
        return os.path.join(base_dir, default_name)
    if os.path.isabs(env_value):
        return env_value
    return os.path.join(base_dir, env_value)


def get_payment_config():
    """获取支付配置"""
    # 默认证书路径在 backend 目录下
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 优先从 secrets.txt 读取私钥
    app_private_key = _load_private_key_from_secrets(base_dir) or ""
    if app_private_key:
        logger.info("使用 secrets.txt 中的私钥")
    else:
        # 备用：从环境变量读
        app_private_key = os.getenv("ALIPAY_APP_PRIVATE_KEY", "")
        if app_private_key and app_private_key != "your-alipay-app-private-key":
            logger.info("使用环境变量 ALIPAY_APP_PRIVATE_KEY")

    # 优先从 public_key.txt 读取支付宝公钥
    alipay_public_key = _load_public_key_from_file(base_dir) or ""
    if alipay_public_key:
        logger.info("使用 public_key.txt 中的支付宝公钥")
    else:
        # 备用：从环境变量读
        alipay_public_key = os.getenv("ALIPAY_PUBLIC_KEY", "")
        if alipay_public_key:
            logger.info("使用环境变量 ALIPAY_PUBLIC_KEY")

    return {
        "alipay_app_id": os.getenv("ALIPAY_APP_ID", ""),
        "alipay_app_private_key": app_private_key,
        "alipay_public_key": alipay_public_key,
        "alipay_server_url": os.getenv("ALIPAY_SERVER_URL", "https://openapi.alipay.com/gateway.do"),
        # 证书路径配置：环境变量优先，相对路径基于 backend 目录解析
        "alipay_app_cert_path": _resolve_cert_path(
            os.getenv("ALIPAY_APP_CERT_PATH"), "appCertPublicKey_2021006144609789.crt", base_dir
        ),
        "alipay_alipay_cert_path": _resolve_cert_path(
            os.getenv("ALIPAY_ALIPAY_CERT_PATH"), "alipayCertPublicKey_RSA2.crt", base_dir
        ),
        "alipay_root_cert_path": _resolve_cert_path(
            os.getenv("ALIPAY_ROOT_CERT_PATH"), "alipayRootCert.crt", base_dir
        ),
        "is_dev": os.getenv("IS_DEV", "true").lower() == "true",
        "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:3006"),
        "backend_url": os.getenv("BACKEND_URL", "http://localhost:8006"),
    }


def init_alipay():
    """初始化支付宝服务（延迟导入，避免未安装 SDK 时影响其他功能）"""
    config = get_payment_config()
    is_dev = config["is_dev"]

    if is_dev:
        logger.info("[Payment] 开发模式 - 模拟支付")
        return DevAlipayService()
    else:
        from .alipay import AlipayService

        # 检查证书文件是否存在
        app_cert = config["alipay_app_cert_path"]
        alipay_cert = config["alipay_alipay_cert_path"]
        root_cert = config["alipay_root_cert_path"]

        use_cert_mode = all([
            app_cert and os.path.exists(app_cert),
            alipay_cert and os.path.exists(alipay_cert),
            root_cert and os.path.exists(root_cert),
        ])

        if use_cert_mode:
            logger.info("[Payment] 生产模式 - 证书模式")
            return AlipayService(
                app_id=config["alipay_app_id"],
                app_private_key=config["alipay_app_private_key"],
                alipay_public_key=None,  # 证书模式不传，让 SDK 从证书读取
                app_cert_path=app_cert,
                alipay_cert_path=alipay_cert,
                alipay_root_cert_path=root_cert,
                server_url=config["alipay_server_url"],
            )
        else:
            logger.info("[Payment] 生产模式 - 公钥模式")
            return AlipayService(
                app_id=config["alipay_app_id"],
                app_private_key=config["alipay_app_private_key"],
                alipay_public_key=config["alipay_public_key"],
                server_url=config["alipay_server_url"],
            )


# 全局支付服务实例
_payment_service = None


def get_payment_service():
    """获取支付服务实例"""
    global _payment_service
    if _payment_service is None:
        _payment_service = init_alipay()
    return _payment_service


class DevAlipayService:
    """开发环境模拟支付服务"""

    def create_order(self, out_trade_no: str, total_amount: float, subject: str,
                     timeout_express: str = "15m", return_url: str = None,
                     notify_url: str = None) -> str:
        """模拟支付 - 返回包含模拟参数的回调 URL"""
        from urllib.parse import urlencode
        config = get_payment_config()
        final_return_url = return_url or f"{config['backend_url']}/api/payment/return"
        mock_params = {
            "out_trade_no": out_trade_no,
            "trade_no": f"DEV{out_trade_no[-10:]}",
            "total_amount": f"{total_amount:.2f}",
            "buyer_id": "2088102112345678",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": "true",
        }
        return f"{final_return_url}?{urlencode(mock_params)}"

    def query_order(self, out_trade_no: str):
        """模拟查询 - 返回成功"""
        return {"trade_status": "TRADE_SUCCESS", "trade_no": f"DEV{out_trade_no[-10:]}"}

    def cancel_order(self, out_trade_no: str) -> bool:
        return True


# 用于 DevAlipayService
from datetime import datetime

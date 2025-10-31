# 聊天内容智能分析平台 - 部署指南

## 🚀 部署方式

### 1. 本地开发部署

#### 环境要求
- Python 3.11+
- Node.js 18+
- Conda (推荐)

#### 快速启动
```bash
# 1. 克隆项目
git clone <repository-url>
cd Nexus

# 2. 一键设置环境
./setup.sh

# 3. 配置API密钥
# 编辑 backend/.env 文件，填入你的API密钥

# 4. 启动服务（首次需安装 Playwright 浏览器）
conda activate nexus-chat-analysis
python -m playwright install chromium

# 5. 启动服务
./start_backend.sh    # 终端1
./start_frontend.sh   # 终端2
```

#### 访问地址
- 前端: http://localhost:5173
- 后端: http://localhost:8000
- API文档: http://localhost:8000/docs

### 2. Docker部署

#### 单容器部署
```bash
# 构建镜像
docker build -t nexus-chat-analysis .

# 运行容器
docker run -d \
  --name nexus-chat \
  -p 8000:8000 \
  -e DEEPSEEK_API_KEY=your_key \
  -e DOUBAO_API_KEY=your_key \
  -e SECRET_KEY=your_secret \
  nexus-chat-analysis
```

#### Docker Compose部署
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 云服务器部署

#### 使用Nginx + Gunicorn
```bash
# 1. 安装依赖
sudo apt update
sudo apt install nginx python3-pip nodejs npm

# 2. 克隆项目
git clone <repository-url>
cd Nexus

# 3. 设置环境
./setup.sh

# 4. 配置Nginx
sudo cp nginx.conf /etc/nginx/sites-available/nexus
sudo ln -s /etc/nginx/sites-available/nexus /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 5. 使用Gunicorn启动后端
cd backend
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000

# 6. 构建前端
cd ../frontend
npm run build
sudo cp -r dist/* /var/www/html/
```

## 🔧 环境配置

### 必需的环境变量
```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com

# 豆包API配置
DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MODEL=doubao-seed-1-6-vision-250815

# 数据库配置
DATABASE_URL=sqlite:///./nexus.db

# 安全配置
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用配置
APP_NAME=聊天内容智能分析平台
APP_VERSION=1.0.0
DEBUG=False

# 文件上传配置
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,webp

# CORS配置
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 可选兼容字段（OCR提供方/火山引擎）
```env
OCR_PROVIDER=volc_ocr
VOLC_ACCESS_KEY=your_volc_ak
VOLC_SECRET_KEY=your_volc_sk
VOLC_REGION=cn-north-1
```
> 未使用时可留空；后端会忽略未配置的可选字段。

### 生产环境配置
```env
# 生产环境设置
DEBUG=False
DATABASE_URL=postgresql://user:password@localhost/nexus_db
SECRET_KEY=your_very_secure_secret_key_here
CORS_ORIGINS=https://yourdomain.com
```

## 📊 性能优化

### 后端优化
```text
- OCR调用日志包含阶段计时：编码、构包、发送、解析、总计
- 批量识别默认最多4张图；批量/单图 max_tokens 分别为 1200/1000；请求超时 30s/25s
```

### 前端优化
```bash
# 1. 代码分割
npm run build -- --analyze

# 2. 压缩资源
npm run build -- --minify

# 3. CDN加速
# 配置CDN域名
```

## 🔒 安全配置

### SSL证书配置
```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 防火墙配置
```bash
# 只开放必要端口
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### API安全
```python
# 1. 请求频率限制
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

# 2. 输入验证
# 使用Pydantic进行数据验证

# 3. SQL注入防护
# 使用SQLAlchemy ORM
```

## 📱 移动端部署

### PWA配置
```json
// public/manifest.json
{
  "name": "聊天内容智能分析平台",
  "short_name": "Nexus Chat",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#ffffff"
}
```

### iOS App打包
```bash
# 1. 安装Capacitor
cd frontend
npm install @capacitor/core @capacitor/cli

# 2. 初始化Capacitor
npx cap init

# 3. 添加iOS平台
npx cap add ios

# 4. 构建并运行
npm run build
npx cap sync
npx cap run ios
```

## 🔍 监控和日志

### 应用监控
```python
# 1. 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 2. 指标收集
from prometheus_client import Counter, Histogram
request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')
```

### 日志配置
```python
# 1. 结构化日志
import structlog
logger = structlog.get_logger()

# 2. 日志轮转
from loguru import logger
logger.add("logs/app.log", rotation="1 day", retention="30 days")
```

## 🧪 测试和验证

### 功能测试
```bash
# 运行测试脚本
python test_project.py

# 单元测试
cd backend
pytest tests/

# 前端测试
cd frontend
npm test
```

### 性能测试
```bash
# 使用Apache Bench
ab -n 1000 -c 10 http://localhost:8000/health

# 使用wrk
wrk -t12 -c400 -d30s http://localhost:8000/health
```

## 🚨 故障排除

### 常见问题

#### 1. 后端启动失败
```bash
# 检查端口占用
lsof -i :8000

# 检查依赖
pip install -r requirements.txt

# 检查环境变量
echo $DEEPSEEK_API_KEY
```

#### 2. 前端构建失败
```bash
# 清理缓存
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# 检查Node版本
node --version  # 需要18+
```

#### 3. API调用失败
```bash
# 检查API密钥
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     https://api.deepseek.com/v1/models

# 检查网络连接
ping api.deepseek.com
```

### 日志查看
```bash
# Docker日志
docker logs nexus-chat

# 系统日志
journalctl -u nginx -f

# 应用日志
tail -f logs/app.log
```

## 📈 扩展部署

### 水平扩展
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
    environment:
      - REDIS_URL=redis://redis:6379
```

### 负载均衡
```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}
```

### 数据库集群
```yaml
# 主从复制
services:
  postgres-master:
    image: postgres:15
    environment:
      POSTGRES_REPLICATION_MODE: master
      
  postgres-slave:
    image: postgres:15
    environment:
      POSTGRES_REPLICATION_MODE: slave
```

## 📞 技术支持

如果遇到部署问题，请：

1. 查看日志文件
2. 检查环境配置
3. 运行测试脚本
4. 查看GitHub Issues
5. 联系技术支持

---

**部署完成后，记得：**
- 定期备份数据
- 监控系统性能
- 更新安全补丁
- 备份API密钥


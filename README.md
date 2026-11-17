# CodeCompass

CodeCompass 将学习目标定位到开源仓库的实际源码，按学习者画像生成阅读路线，支持源码研读、学习记录和 Issue 实践准备。

## 安装与使用

1. 使用 Windows 和 64 位 Python 3.12。将 ZIP 完整解压至可写目录。
2. 双击 `启动.cmd`。首次启动会建立虚拟环境并从包内安装依赖，无需联网安装依赖。
3. 用 Edge 或 Chrome 打开 `http://127.0.0.1:8789/`。
4. 点击「建立我的能力画像」，完成经验调查，保存或跳过测评。在仓库导入页可输入 `https://github.com/pallets/itsdangerous` 试用。分析完成后确认学习目标和源码范围，生成学习路线。

导入 GitHub 仓库和刷新 Issue 需要联网。不设密钥也可使用本地源码讲解；如需使用 DeepSeek，启动前在同一 PowerShell 窗口为 `DEEPSEEK_API_KEY` 设置自己的密钥，再运行以下命令。问题及相关源码片段会发给配置中的模型服务。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_product.ps1 -Port 8789
```

端口占用时修改上面的端口并使用对应浏览器地址。学习数据保存在解压目录的 `local_data/`。

## 代码与第三方来源

- 前端：`app/product/`；后端与算法：`src/codecompass/`。
- `benchmarks/sources/` 是内置示例和练习使用的固定源码快照；boltons 和 itsdangerous 使用 BSD-3-Clause，more-itertools 使用 MIT。各快照保留对应原始许可证，来源和提交见 `snapshot.json`。
- `dependencies/` 提供 `requirements.txt` 列出的锁定运行依赖；各 wheel 内含其许可。
- 产品源码基线：`02798b4367ab18300ea80daea40fe5a762f4ff10`。

## 在哪里阅读和复用实现

- GitHub 源码导入与分析：`src/codecompass/product/repositories.py`。
- 阅读计划和重规划：`src/codecompass/product/source_routes.py`、`reading_order.py`、`workspaces.py`。
- 本地源码讲解和可选模型服务：`src/codecompass/product/source_assistant.py`。
- 第三方代码仍按相应目录所附许可证使用。团队自有代码采用 MIT 许可证，见根目录 LICENSE。第三方源码快照、依赖及其他第三方材料仍分别适用其原始许可证与版权声明，不因本项目采用 MIT 而变更授权。

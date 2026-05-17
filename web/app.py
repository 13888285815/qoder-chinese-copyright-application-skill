"""
软件著作权申请材料生成系统 - 网页服务器
提供项目分析、文档生成、在线编辑、PDF导出和分享功能
"""

import os
import sys
import json
import uuid
import zipfile
import urllib.parse
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename

# 版本号（语义化版本2.0.0）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from version import get_version as _get_ver
    __version__ = _get_ver()
except ImportError:
    __version__ = get_version()

from flask import (
    Flask, render_template, request, jsonify,
    send_file, session, redirect, url_for
)

# 将上级目录加入模块搜索路径，以便导入生成器
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_copyright_docs import CopyrightDocGenerator

# ============================================================
# 应用初始化
# ============================================================

应用 = Flask(__name__)
应用.secret_key = "copyright-application-secret-key-2026"
应用.config["GENERATED_FOLDER"] = "generated"
应用.config["UPLOAD_FOLDER"] = "uploads"
应用.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB

# 允许上传的文件扩展名
允许的扩展名 = {
    ".js", ".ts", ".jsx", ".tsx", ".vue",
    ".py", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".json", ".wxml", ".wxss", ".html", ".css", ".scss", ".less",
    ".md", ".txt", ".yaml", ".yml", ".toml",
    ".sh", ".bat", ".sql",
    ".xml", ".gradle", ".properties",
}

# 确保目录存在
os.makedirs(应用.config["GENERATED_FOLDER"], exist_ok=True)
os.makedirs(应用.config["UPLOAD_FOLDER"], exist_ok=True)


def 是否允许的文件(文件名: str) -> bool:
    """检查文件扩展名是否在允许列表中"""
    return Path(文件名).suffix.lower() in 允许的扩展名


def 获取项目目录(项目编号: str) -> str:
    """根据项目编号获取项目目录路径"""
    return os.path.join(应用.config["GENERATED_FOLDER"], 项目编号)


def 读取项目数据(项目编号: str) -> dict:
    """从项目目录读取项目配置数据"""
    配置文件 = os.path.join(获取项目目录(项目编号), "project.json")
    if not os.path.exists(配置文件):
        return None
    with open(配置文件, "r", encoding="utf-8") as f:
        return json.load(f)


def 保存项目数据(项目编号: str, 数据: dict):
    """将项目配置数据写入项目目录"""
    项目目录 = 获取项目目录(项目编号)
    os.makedirs(项目目录, exist_ok=True)
    配置文件 = os.path.join(项目目录, "project.json")
    with open(配置文件, "w", encoding="utf-8") as f:
        json.dump(数据, f, ensure_ascii=False, indent=2)


# ============================================================
# 页面路由
# ============================================================

@应用.route("/")
def 首页():
    """渲染首页"""
    return render_template("index.html")


@应用.route("/editor/<project_id>")
def 编辑器(project_id):
    """渲染编辑器页面"""
    return render_template("editor.html", project_id=project_id)


# ============================================================
# 项目管理接口
# ============================================================

@应用.route("/api/projects", methods=["GET"])
def 获取项目列表():
    """获取所有项目列表"""
    项目列表 = []
    生成目录 = 应用.config["GENERATED_FOLDER"]

    if not os.path.exists(生成目录):
        return jsonify({"success": True, "projects": []})

    for 项目编号 in os.listdir(生成目录):
        项目路径 = os.path.join(生成目录, 项目编号)
        if not os.path.isdir(项目路径):
            continue

        数据 = 读取项目数据(project_id)
        if 数据:
            项目列表.append({
                "id": 项目编号,
                "name": 数据.get("software_name", "未命名项目"),
                "owner": 数据.get("owner_name", ""),
                "type": 数据.get("software_type", ""),
                "created_at": 数据.get("created_at", ""),
                "updated_at": 数据.get("updated_at", ""),
            })

    # 按更新时间倒序排列
    项目列表.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return jsonify({"success": True, "projects": 项目列表, "version": __version__})


@应用.route("/api/projects", methods=["POST"])
def 创建项目():
    """
    创建新项目（表单方式）
    通过用户填写的表单信息直接生成文档
    """
    数据 = request.json
    项目编号 = str(uuid.uuid4())

    # 补充时间信息
    当前时间 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    数据["created_at"] = 当前时间
    数据["updated_at"] = 当前时间
    数据["source"] = "form"  # 标记为表单创建

    # 保存项目数据
    保存项目数据(项目编号, 数据)

    # 使用表单信息生成文档
    从表单生成文档(项目编号, 数据)

    return jsonify({
        "success": True,
        "project_id": 项目编号,
        "message": "项目创建成功"
    })


@应用.route("/api/template", methods=["GET"])
def 获取模板():
    """
    获取新项目模板（云南意念科技默认值）
    """
    return jsonify({
        "success": True,
        "template": {
            "owner_name": "云南意念科技有限公司",
            "software_name": "意念ERP",
            "id_type": "营业执照",
            "id_number": "530111197702274437",
            "address": "云南省昆明市人民西路220号云南软件园",
            "contact": "郑志雄",
            "phone": "13888285815",
            "software_type": "Web应用",
            "industry": "全行业",
            "version": "V2.0.0",
            "dev_purpose": "该项目由云南意念科技开发，旨在打造一款轻量化、易上手的云端 ERP 系统，解决中小企业传统系统成本高、部署难、操作复杂的痛点。面向小微企业与初创团队，提供低成本、免部署的数字化管理方案，助力企业快速实现进销存、财务、客户等核心业务线上化，高效完成基础数字化转型。",
            "main_functions": "意念ERP是一款轻量化开源企业资源管理系统，项目部署于静态网页平台，界面简洁清爽，操作门槛低。系统聚焦中小企业日常经营管理需求，整合采购、销售、库存、账务、客户管理等核心业务模块，实现业务数据一体化统筹。该项目适配多端浏览使用，摒弃传统 ERP 臃肿复杂的架构，主打高效实用、快速上手。可满足小微企业进销存统计、订单流程跟进、货品出入库登记、简易财务对账等基础办公需求，无需复杂部署即可投入使用。适合初创团队、个体商户用于日常业务数字化管理，兼具实用性与拓展性，是低成本实现企业基础数字化转型的优质轻量管理工具。",
            "tech_features": "意念ERP是云南意念科技 2026 年推出的云端轻量化 ERP 系统。采用前后端分离架构，基于静态网页部署，免本地安装、浏览器直接访问。提供开箱即用演示账号，上手零门槛。系统架构简洁高效，适配中小企业，支持快速二次开发与功能拓展，兼顾易用性与可定制性。",
        }
    })


@应用.route("/api/projects/<project_id>", methods=["GET"])
def 获取项目(project_id):
    """获取项目配置数据"""
    数据 = 读取项目数据(project_id)
    if not 数据:
        return jsonify({"success": False, "message": "项目不存在"}), 404
    return jsonify({"success": True, "data": 数据})


@应用.route("/api/projects/<project_id>", methods=["DELETE"])
def 删除项目(project_id):
    """删除项目及其所有文件"""
    项目目录 = 获取项目目录(project_id)
    if not os.path.exists(项目目录):
        return jsonify({"success": False, "message": "项目不存在"}), 404

    shutil.rmtree(项目目录)
    return jsonify({"success": True, "message": "项目已删除"})


@应用.route("/api/projects/upload", methods=["POST"])
def 上传项目分析():
    """
    上传项目源码进行分析
    接受zip压缩包，解压后调用生成器分析项目结构并生成文档
    """
    if "file" not in request.files:
        return jsonify({"success": False, "message": "请上传文件"}), 400

    上传文件 = request.files["file"]
    if not 上传文件.filename:
        return jsonify({"success": False, "message": "文件名为空"}), 400

    if not 上传文件.filename.endswith(".zip"):
        return jsonify({"success": False, "message": "仅支持zip格式压缩包"}), 400

    # 获取额外的表单数据
    著作权人 = request.form.get("owner_name", "")
    证件类型 = request.form.get("id_type", "身份证")
    证件号码 = request.form.get("id_number", "")
    地址 = request.form.get("address", "")
    邮编 = request.form.get("zip_code", "")
    联系人 = request.form.get("contact", "")
    电话 = request.form.get("phone", "")
    邮箱 = request.form.get("email", "")
    开发目的 = request.form.get("dev_purpose", "")
    面向行业 = request.form.get("industry", "")
    主要功能 = request.form.get("main_functions", "")
    技术特点 = request.form.get("tech_features", "")

    项目编号 = str(uuid.uuid4())

    try:
        # 解压上传的项目到临时目录
        临时目录 = tempfile.mkdtemp()
        zip路径 = os.path.join(临时目录, secure_filename(上传文件.filename))
        上传文件.save(zip路径)

        解压目录 = os.path.join(临时目录, "source")
        with zipfile.ZipFile(zip路径, "r") as zf:
            zf.extractall(解压目录)

        # 如果解压后只有一个顶层目录，进入该目录
        顶层内容 = os.listdir(解压目录)
        if len(顶层内容) == 1 and os.path.isdir(os.path.join(解压目录, 顶层内容[0])):
            解压目录 = os.path.join(解压目录, 顶层内容[0])

        # 使用生成器分析项目
        项目输出目录 = 获取项目目录(项目编号)
        os.makedirs(项目输出目录, exist_ok=True)

        生成器 = CopyrightDocGenerator(解压目录, 项目输出目录)
        项目信息 = 生成器.analyze_project()

        # 准备著作权人信息
        著作权人信息 = {
            "name": 著作权人 or "（请填写）",
            "id_type": 证件类型,
            "id_number": 证件号码 or "（请填写）",
            "address": 地址 or "（请填写）",
            "zip_code": 邮编 or "（请填写）",
            "contact": 联系人 or "（请填写）",
            "phone": 电话 or "（请填写）",
            "email": 邮箱 or "（请填写）",
        }

        软件信息 = {
            "dev_purpose": 开发目的,
            "industry": 面向行业,
            "main_functions": 主要功能,
            "tech_features": 技术特点,
        }

        # 生成所有文档
        生成器.generate_all_docs(著作权人信息, 软件信息)

        # 保存项目数据
        当前时间 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        项目数据 = {
            "software_name": 项目信息.get("name", ""),
            "software_short_name": 项目信息.get("name", "").replace("软件", ""),
            "version": 项目信息.get("version", "2.0.0"),
            "software_type": 项目信息.get("type", "通用软件"),
            "owner_name": 著作权人 or "（请填写）",
            "id_type": 证件类型,
            "id_number": 证件号码 or "（请填写）",
            "address": 地址 or "（请填写）",
            "zip_code": 邮编 or "（请填写）",
            "contact": 联系人 or "（请填写）",
            "phone": 电话 or "（请填写）",
            "email": 邮箱 or "（请填写）",
            "code_lines": str(生成器.total_lines),
            "programming_lang": ", ".join(项目信息.get("tech_stack", [])),
            "platform": 项目信息.get("platform", ""),
            "dev_purpose": 开发目的,
            "industry": 面向行业,
            "main_functions": 主要功能,
            "tech_features": 技术特点,
            "features": 项目信息.get("features", []),
            "structure": 项目信息.get("structure", {}),
            "source": "upload",
            "created_at": 当前时间,
            "updated_at": 当前时间,
        }
        保存项目数据(项目编号, 项目数据)

        # 清理临时目录
        shutil.rmtree(临时目录, ignore_errors=True)

        return jsonify({
            "success": True,
            "project_id": 项目编号,
            "project_info": {
                "name": 项目信息.get("name", ""),
                "type": 项目信息.get("type", ""),
                "code_lines": 生成器.total_lines,
                "code_files": len(生成器.code_files),
                "tech_stack": 项目信息.get("tech_stack", []),
            },
            "message": "项目分析完成"
        })

    except Exception as e:
        # 清理临时目录
        shutil.rmtree(临时目录, ignore_errors=True)
        return jsonify({"success": False, "message": f"分析失败：{str(e)}"}), 500


# ============================================================
# 文档接口
# ============================================================

# 文件名映射：内部名 → 显示名
内部名映射 = {
    "软件著作权登记申请表.md": "software-copyright-form.md",
    "用户手册.md": "user-manual.md",
    "设计说明书.md": "design-specification.md",
    "源代码文档.md": "source-code.md",
}

# 反向映射：显示名 → 内部名
显示名映射 = {v: k for k, v in 内部名映射.items()}


@应用.route("/api/projects/<project_id>/documents", methods=["GET"])
def 获取文档列表(project_id):
    """获取项目下所有文档"""
    项目目录 = 获取项目目录(project_id)
    if not os.path.exists(项目目录):
        return jsonify({"success": False, "message": "项目不存在"}), 404

    文档列表 = []
    for 文件名 in os.listdir(项目目录):
        if not 文件名.endswith(".md"):
            continue

        文件路径 = os.path.join(项目目录, 文件名)
        try:
            with open(文件路径, "r", encoding="utf-8") as f:
                内容 = f.read()
        except Exception:
            continue

        显示名 = 显示名映射.get(文件名, 文件名)
        文档列表.append({
            "name": 显示名,
            "filename": 文件名,
            "content": 内容,
            "size": len(内容),
            "modified": datetime.fromtimestamp(
                os.path.getmtime(文件路径)
            ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return jsonify({"success": True, "documents": 文档列表})


@应用.route("/api/projects/<project_id>/documents/<filename>", methods=["GET"])
def 获取文档内容(project_id, filename):
    """获取单个文档内容"""
    实际文件名 = 内部名映射.get(filename, filename)
    文件路径 = os.path.join(获取项目目录(project_id), 实际文件名)

    # 如果映射名不存在，尝试直接查找
    if not os.path.exists(文件路径):
        文件路径 = os.path.join(获取项目目录(project_id), filename)

    if not os.path.exists(文件路径):
        return jsonify({"success": False, "message": "文档不存在"}), 404

    with open(文件路径, "r", encoding="utf-8") as f:
        内容 = f.read()

    return jsonify({"success": True, "content": 内容, "filename": filename})


@应用.route("/api/projects/<project_id>/documents/<filename>", methods=["PUT"])
def 更新文档内容(project_id, filename):
    """更新文档内容"""
    实际文件名 = 内部名映射.get(filename, filename)
    数据 = request.json
    文件路径 = os.path.join(获取项目目录(project_id), 实际文件名)

    # 如果映射名不存在，尝试直接查找
    if not os.path.exists(文件路径):
        文件路径 = os.path.join(获取项目目录(project_id), filename)

    with open(文件路径, "w", encoding="utf-8") as f:
        f.write(数据.get("content", ""))

    # 更新项目修改时间
    项目数据 = 读取项目数据(project_id)
    if 项目数据:
        项目数据["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        保存项目数据(project_id, 项目数据)

    return jsonify({"success": True, "message": "文档保存成功"})


# ============================================================
# 导出接口
# ============================================================

@应用.route("/api/projects/<project_id>/export", methods=["POST"])
def 导出项目(project_id):
    """将项目文档打包为zip导出"""
    项目目录 = 获取项目目录(project_id)
    if not os.path.exists(项目目录):
        return jsonify({"success": False, "message": "项目不存在"}), 404

    压缩文件名 = f"copyright-materials-{project_id[:8]}.zip"
    压缩路径 = os.path.join(应用.config["GENERATED_FOLDER"], 压缩文件名)

    with zipfile.ZipFile(压缩路径, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(项目目录):
            for file in files:
                if not file.endswith(".md"):
                    continue
                文件路径 = os.path.join(root, file)
                # 使用中文文件名作为压缩包内的文件名
                压缩名 = 显示名映射.get(file, file)
                zf.write(文件路径, 压缩名)

    下载名 = f"软件著作权申请材料-{project_id[:8]}.zip"
    return jsonify({
        "success": True,
        "download_url": f"/api/download/{压缩文件名}",
        "download_name": 下载名,
    })


@应用.route("/api/download/<filename>", methods=["GET"])
def 下载文件(filename):
    """下载指定文件"""
    文件路径 = os.path.join(应用.config["GENERATED_FOLDER"], secure_filename(filename))
    if not os.path.exists(文件路径):
        return jsonify({"success": False, "message": "文件不存在"}), 404

    下载名 = filename.replace("copyright-materials-", "软件著作权申请材料-")
    return send_file(文件路径, as_attachment=True, download_name=下载名)


@应用.route("/api/projects/<project_id>/export-pdf", methods=["POST"])
def 导出PDF(project_id):
    """将单个markdown文档转换为PDF（weasyprint自动渲染中文）"""
    项目目录 = 获取项目目录(project_id)
    if not os.path.exists(项目目录):
        return jsonify({"success": False, "message": "项目不存在"}), 404

    数据 = request.json or {}
    目标文件 = 数据.get("filename", "")

    if not 目标文件:
        return jsonify({"success": False, "message": "请指定要转换的文档"}), 400

    实际文件名 = 内部名映射.get(目标文件, 目标文件)
    md路径 = os.path.join(项目目录, 实际文件名)
    if not os.path.exists(md路径):
        md路径 = os.path.join(项目目录, 目标文件)
    if not os.path.exists(md路径):
        return jsonify({"success": False, "message": "文档不存在"}), 404

    with open(md路径, 'r', encoding='utf-8') as f:
        md内容 = f.read()

    first_line = md内容.split('\n')[0]
    标题 = first_line.lstrip('# ').strip() if first_line.startswith('#') else 目标文件.replace('.md', '')
    
    # 使用中文文件名
    中文名 = 显示名映射.get(目标文件, 目标文件)
    pdf路径 = os.path.join(项目目录, 中文名.replace('.md', '.pdf'))
    
    if md转pdf(md内容, 标题, pdf路径):
        下载名 = 中文名.replace('.md', '.pdf')
        return jsonify({
            "success": True,
            "message": "PDF生成成功",
            "pdf_url": f"/api/download-pdf/{project_id}/{urllib.parse.quote(下载名)}",
        })
    else:
        return jsonify({"success": False, "message": "PDF生成失败：未安装PDF转换工具。请安装weasyprint（需GTK库）或pandoc/wkhtmltopdf后重试。"})


@应用.route("/api/projects/<project_id>/export-docx", methods=["POST"])
def 导出DOCX(project_id):
    """将单个markdown文档转换为Word文档"""
    项目目录 = 获取项目目录(project_id)
    if not os.path.exists(项目目录):
        return jsonify({"success": False, "message": "项目不存在"}), 404

    数据 = request.json or {}
    目标文件 = 数据.get("filename", "")

    if not 目标文件:
        return jsonify({"success": False, "message": "请指定要转换的文档"}), 400

    实际文件名 = 内部名映射.get(目标文件, 目标文件)
    md路径 = os.path.join(项目目录, 实际文件名)
    if not os.path.exists(md路径):
        md路径 = os.path.join(项目目录, 目标文件)
    if not os.path.exists(md路径):
        return jsonify({"success": False, "message": "文档不存在"}), 404

    with open(md路径, 'r', encoding='utf-8') as f:
        md内容 = f.read()

    first_line = md内容.split('\n')[0]
    标题 = first_line.lstrip('# ').strip() if first_line.startswith('#') else 目标文件.replace('.md', '')
    
    # 使用中文文件名
    中文名 = 显示名映射.get(目标文件, 目标文件)
    docx路径 = os.path.join(项目目录, 中文名.replace('.md', '.docx'))
    
    if md转docx(md内容, 标题, docx路径):
        下载名 = 中文名.replace('.md', '.docx')
        return jsonify({
            "success": True,
            "message": "Word文档生成成功",
            "docx_url": f"/api/download-docx/{project_id}/{urllib.parse.quote(下载名)}",
        })
    else:
        return jsonify({"success": False, "message": "Word文档生成失败"})


@应用.route("/api/projects/<project_id>/export-all", methods=["POST"])
def 导出全部格式(project_id):
    """将项目所有文档批量转换为PDF和Word"""
    项目目录 = 获取项目目录(project_id)
    if not os.path.exists(项目目录):
        return jsonify({"success": False, "message": "项目不存在"}), 404

    数据 = request.json or {}
    formats = 数据.get("formats", ["pdf", "docx"])

    转换结果 = 批量转换项目文档(project_id, 项目目录)

    import time
    zip名 = f"copyright-all-{project_id[:8]}-{int(time.time())}.zip"
    zip路径 = os.path.join(应用.config["GENERATED_FOLDER"], zip名)

    with zipfile.ZipFile(zip路径, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in os.listdir(项目目录):
            ext = os.path.splitext(file)[1]
            允许格式 = []
            if "pdf" in formats:
                允许格式.append(".pdf")
            if "docx" in formats:
                允许格式.append(".docx")
            if ext in 允许格式:
                file_path = os.path.join(项目目录, file)
                中文名 = 显示名映射.get(file, file)
                zf.write(file_path, 中文名)

    return jsonify({
        "success": True,
        "message": "批量转换完成",
        "download_url": f"/api/download/{zip名}",
        "download_name": f"软件著作权申请材料-全格式.zip",
        "converted": 转换结果,
    })


@应用.route("/api/download-pdf/<project_id>/<filename>", methods=["GET"])
def 下载PDF(project_id, filename):
    实际文件名 = filename.replace(".pdf", ".md")
    pdf路径 = os.path.join(获取项目目录(project_id), 实际文件名).replace(".md", ".pdf")
    if not os.path.exists(pdf路径):
        return jsonify({"success": False, "message": "PDF文件不存在"}), 404
    
    # 使用中文下载名
    中文名 = filename
    if filename in 显示名映射:
        中文名 = 显示名映射[filename].replace(".md", ".pdf")
    elif filename.endswith(".pdf"):
        中文名 = filename  # 已经是中文名
    
    return send_file(pdf路径, as_attachment=True, download_name=中文名)


@应用.route("/api/download-docx/<project_id>/<filename>", methods=["GET"])
def 下载DOCX(project_id, filename):
    实际文件名 = filename.replace(".docx", ".md")
    docx路径 = os.path.join(获取项目目录(project_id), 实际文件名).replace(".md", ".docx")
    if not os.path.exists(docx路径):
        return jsonify({"success": False, "message": "Word文件不存在"}), 404
    
    # 使用中文下载名
    中文名 = filename
    if filename in 显示名映射:
        中文名 = 显示名映射[filename].replace(".md", ".docx")
    elif filename.endswith(".docx"):
        中文名 = filename  # 已经是中文名
    
    return send_file(docx路径, as_attachment=True, download_name=中文名)




# ============================================================
# 分享接口
# ============================================================

@应用.route("/api/projects/<project_id>/share", methods=["POST"])
def 分享项目(project_id):
    """生成项目分享链接"""
    项目目录 = 获取项目目录(project_id)
    if not os.path.exists(项目目录):
        return jsonify({"success": False, "message": "项目不存在"}), 404

    分享链接 = f"{request.host_url}editor/{project_id}"
    return jsonify({"success": True, "share_link": 分享链接})


# ============================================================
# 表单方式生成文档
# ============================================================

def 从表单生成文档(项目编号: str, 数据: dict):
    """
    使用表单填写的信息直接生成文档（不分析源码）
    适用于用户没有源码或只需要快速生成模板的场景
    """
    项目目录 = 获取项目目录(项目编号)
    os.makedirs(项目目录, exist_ok=True)

    著作权人 = 数据.get("owner_name", "未填写")
    软件名称 = 数据.get("software_name", "示例软件")
    软件简称 = 数据.get("software_short_name", 软件名称[:10])
    版本号 = 数据.get("version", "V2.0.0")
    软件类型 = 数据.get("software_type", "小程序")
    证件类型 = 数据.get("id_type", "身份证")
    证件号码 = 数据.get("id_number", "（请填写）")
    地址 = 数据.get("address", "（请填写）")
    邮编 = 数据.get("zip_code", "（请填写）")
    联系人 = 数据.get("contact", "（请填写）")
    电话 = 数据.get("phone", "（请填写）")
    邮箱 = 数据.get("email", "（请填写）")
    代码行数 = 数据.get("code_lines", "15000")
    编程语言 = 数据.get("programming_lang", "JavaScript, TypeScript")
    开发目的 = 数据.get("dev_purpose", "未填写")
    面向行业 = 数据.get("industry", "未填写")
    主要功能 = 数据.get("main_functions", "未填写")
    技术特点 = 数据.get("tech_features", "未填写")
    当前日期 = datetime.now().strftime("%Y-%m-%d")

    # 根据软件类型判断运行环境
    if 软件类型 == "小程序":
        运行平台 = "微信小程序平台"
        开发工具 = "微信开发者工具"
        运行支撑 = "微信小程序基础库"
        运行硬件 = "智能手机"
        安装说明 = "1. 打开微信客户端\n2. 搜索或扫描小程序二维码\n3. 进入小程序即可使用"
    elif 软件类型 == "APP":
        运行平台 = "iOS/Android"
        开发工具 = "Android Studio / Xcode"
        运行支撑 = "iOS 15.0+ / Android 10.0+"
        运行硬件 = "智能手机"
        安装说明 = "1. 访问应用商店下载\n2. 安装应用程序\n3. 启动并注册账号"
    elif 软件类型 == "Web应用":
        运行平台 = "Web浏览器"
        开发工具 = "Visual Studio Code"
        运行支撑 = "Chrome / Firefox / Safari / Edge"
        运行硬件 = "PC或移动设备"
        安装说明 = "1. 打开浏览器\n2. 访问系统网址\n3. 注册/登录账号"
    else:
        运行平台 = "跨平台"
        开发工具 = "Visual Studio Code"
        运行支撑 = "操作系统运行时"
        运行硬件 = "PC或移动设备"
        安装说明 = "1. 下载安装包\n2. 按提示完成安装\n3. 启动软件"

    # ---- 生成申请表 ----
    申请表内容 = f"""# {软件名称} - 软件著作权登记申请表

**生成日期**：{datetime.now().strftime("%Y年%m月%d日")}

---

## 一、软件基本信息

| 字段 | 内容 |
|------|------|
| 软件全称 | {软件名称} |
| 软件简称 | {软件简称} |
| 版本号 | {版本号} |
| 开发完成日期 | {当前日期} |
| 首次发表日期 | {当前日期} |
| 软件分类 | 应用软件-{软件类型} |
| 软件性质 | 原创 |

## 二、著作权人信息

| 字段 | 内容 |
|------|------|
| 著作权人 | {著作权人} |
| 证件类型 | {证件类型} |
| 证件号码 | {证件号码} |
| 地址 | {地址} |
| 邮编 | {邮编} |
| 联系人 | {联系人} |
| 电话 | {电话} |
| 邮箱 | {邮箱} |

## 三、开发者信息

| 字段 | 内容 |
|------|------|
| 开发者 | {著作权人} |
| 证件类型 | {证件类型} |
| 证件号码 | {证件号码} |
| 地址 | {地址} |
| 邮编 | {邮编} |
| 联系人 | {联系人} |
| 电话 | {电话} |
| 邮箱 | {邮箱} |

## 四、技术信息

| 字段 | 内容 |
|------|------|
| 开发的硬件环境 | Intel Core i5 或同等性能CPU，8GB内存 |
| 运行的硬件环境 | {运行硬件} |
| 开发该软件的操作系统 | Windows 11 / macOS |
| 软件开发环境/开发工具 | {开发工具} |
| 该软件的运行平台/操作系统 | {运行平台} |
| 软件运行支撑环境/支持软件 | {运行支撑} |
| 编程语言 | {编程语言} |
| 源程序量 | {代码行数} 行 |
| 开发目的 | {开发目的} |
| 面向领域/行业 | {面向行业} |

## 五、软件功能简介

{主要功能}

## 六、技术特点

{技术特点}

## 七、备注

本软件为原创开发，未使用第三方商业代码。
"""

    with open(os.path.join(项目目录, "software-copyright-form.md"), "w", encoding="utf-8") as f:
        f.write(申请表内容)

    # ---- 生成用户手册 ----
    手册内容 = f"""# {软件名称} 用户手册

**著作权人：{著作权人}**

**软件名称**：{软件名称}
**版本号**：{版本号}
**生成日期**：{当前日期}

---

## 第一章 软件简介

### 1.1 软件概述

{软件名称}是一款{软件类型}软件，运行于{运行平台}，面向{面向行业}领域，旨在{开发目的}。

### 1.2 主要功能

{主要功能}

### 1.3 系统要求

- **运行平台**：{运行平台}
- **编程语言/技术栈**：{编程语言}
- **网络要求**：需要网络连接

## 第二章 安装与使用

### 2.1 安装说明

{安装说明}

### 2.2 首次使用

1. 完成安装或进入应用
2. 注册/登录用户账号
3. 根据引导完成初始设置
4. 开始使用各项功能

## 第三章 功能详细说明

### 3.1 核心功能

{主要功能}

### 3.2 操作步骤

1. 进入对应功能页面
2. 按照界面提示进行操作
3. 确认操作结果
4. 如需修改，返回重新操作

### 3.3 注意事项

- 请确保网络连接正常
- 首次使用建议阅读使用说明
- 重要操作前请确认信息无误
- 定期备份重要数据

## 第四章 常见问题

### 4.1 无法打开应用

**可能原因**：
1. 系统版本不满足要求
2. 安装文件不完整
3. 网络连接异常

**解决方案**：
1. 检查系统版本是否满足要求
2. 重新下载或安装应用
3. 检查网络连接

### 4.2 数据加载失败

**可能原因**：
1. 网络连接不稳定
2. 服务器维护中
3. 本地缓存异常

**解决方案**：
1. 切换网络后重试
2. 稍后再试
3. 清除应用缓存后重试

## 第五章 技术支持

- **著作权人**：{著作权人}
- **联系电话**：{电话}
- **电子邮箱**：{邮箱}
- **官方网站**：tools.yndxw.com
- **当前版本**：{版本号}
- **更新日期**：{当前日期}
"""

    with open(os.path.join(项目目录, "user-manual.md"), "w", encoding="utf-8") as f:
        f.write(手册内容)

    # ---- 生成设计说明书 ----
    设计内容 = f"""# {软件名称} 设计说明书

**著作权人：{著作权人}**

**软件名称**：{软件名称}
**版本号**：{版本号}
**生成日期**：{当前日期}

---

## 第一章 引言

### 1.1 编写目的

本文档详细阐述{软件名称}的设计思路、系统架构、模块划分和实现细节，为软件开发、测试和维护提供技术参考。

### 1.2 开发背景

{开发目的}，因此开发了{软件名称}，面向{面向行业}领域。

### 1.3 设计目标

1. **易用性**：提供简洁直观的用户界面
2. **稳定性**：确保软件稳定运行
3. **可扩展性**：采用模块化设计，便于功能扩展
4. **安全性**：保护用户数据安全

## 第二章 总体设计

### 2.1 系统架构

{软件名称}采用{软件类型}架构，基于{编程语言}技术开发。

**系统架构特点**：
1. 采用分层架构设计
2. 模块化设计，职责清晰
3. 支持跨平台运行

### 2.2 模块划分

1. **主界面模块**：负责用户界面的展示和交互
2. **业务逻辑模块**：处理核心业务逻辑
3. **数据存储模块**：负责数据的存储和管理
4. **工具模块**：提供通用工具函数和辅助方法
5. **网络通信模块**：处理网络请求和数据交互

### 2.3 技术选型

- **编程语言**：{编程语言}
- **开发工具**：{开发工具}
- **运行平台**：{运行平台}
- **运行支撑**：{运行支撑}

### 2.4 运行环境

- **运行平台**：{运行平台}
- **开发工具**：{开发工具}
- **硬件要求**：{运行硬件}

## 第三章 详细设计

### 3.1 主界面模块设计

#### 3.1.1 模块功能

主界面模块负责软件的启动、界面展示和用户交互。

#### 3.1.2 界面布局

采用响应式布局，适配不同屏幕尺寸。主要包含：
1. 顶部导航栏
2. 主内容区域
3. 底部状态栏

#### 3.1.3 交互设计

- **点击交互**：按钮点击触发相应功能
- **滑动交互**：支持手势操作
- **输入交互**：表单输入和验证

### 3.2 业务逻辑模块设计

#### 3.2.1 模块功能

处理软件的核心业务逻辑，包括数据处理、计算和业务规则实现。

#### 3.2.2 数据流

用户界面 → 业务逻辑层 → 数据存储层 → 返回结果

### 3.3 数据存储模块设计

#### 3.3.1 存储方式

采用本地存储和远程服务器存储相结合的方式。

#### 3.3.2 数据格式

- **配置信息**：JSON格式
- **用户数据**：JSON格式
- **缓存数据**：键值对格式

## 第四章 接口设计

### 4.1 内部接口

模块间通信采用函数调用和事件机制。

### 4.2 外部接口

- 网络请求接口
- 数据上报接口
- 第三方服务接口

## 第五章 安全设计

### 5.1 数据安全

- **敏感数据加密**：对密码、个人信息等敏感数据进行加密存储
- **传输安全**：采用HTTPS协议进行数据传输
- **访问控制**：合理的权限管理机制

### 5.2 异常处理

- **输入验证**：对用户输入进行严格验证
- **错误捕获**：完善的异常捕获和处理机制
- **日志记录**：记录关键操作和异常信息

## 第六章 测试设计

### 6.1 测试策略

- **单元测试**：对各个功能模块进行测试
- **集成测试**：测试模块间的交互
- **用户测试**：真实用户使用测试

### 6.2 测试环境

- **测试平台**：{运行平台}
- **测试设备**：{运行硬件}
- **测试工具**：{开发工具}

## 第七章 部署与维护

### 7.1 部署方案

{安装说明}

### 7.2 维护计划

1. **缺陷修复**：及时修复发现的问题
2. **功能更新**：根据用户反馈持续优化
3. **性能优化**：定期优化软件性能
"""

    with open(os.path.join(项目目录, "design-specification.md"), "w", encoding="utf-8") as f:
        f.write(设计内容)

    # ---- 生成源代码文档 ----
    源代码内容 = f"""# {软件名称} 源代码文档

**著作权人：{著作权人}**

**软件名称**：{软件名称}
**版本号**：{版本号}
**生成日期**：{当前日期}
**源程序量**：{代码行数} 行

---

## 说明

本文档为{软件名称}的源代码文档。由于本项目通过表单方式创建，
源代码文档请手动补充实际代码内容，或重新使用"上传源码"功能自动生成。

## 代码文件结构

```
{软件名称}/
├── 入口文件
│   └── app.js / main.js / index.py
├── 页面/视图
│   ├── 首页
│   ├── 列表页
│   └── 详情页
├── 组件
│   ├── 公共组件
│   └── 业务组件
├── 工具/服务
│   ├── 请求封装
│   ├── 数据处理
│   └── 存储管理
└── 配置
    ├── 环境配置
    └── 路由配置
```

## 前30页（核心业务逻辑）

> 请在此处粘贴项目前30页源代码（约1500行），从入口文件开始，按重要性排列。

## 后30页（辅助代码）

> 请在此处粘贴项目后30页源代码（约1500行），从辅助模块开始，倒序排列。
"""

    with open(os.path.join(项目目录, "source-code.md"), "w", encoding="utf-8") as f:
        f.write(源代码内容)


# ============================================================
# 启动服务器
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  软件著作权申请材料生成系统")
    print("=" * 60)
    print("  访问地址：http://localhost:5002")
    print("  功能说明：")
    print("    - 表单填写生成文档")
    print("    - 上传源码自动分析")
    print("    - 在线编辑与导出")
    print("=" * 60)
    应用.run(debug=False, use_reloader=False, host="0.0.0.0", port=5002, threaded=True)


# ============================================================
# 文档格式转换工具
# ============================================================

def md转html(md内容: str, 标题: str = "软件著作权申请材料") -> str:
    """将markdown转换为带样式的中文HTML"""
    import markdown
    from markdown.extensions import tables, fenced_code, codehilite
    
    html内容 = markdown.markdown(
        md内容,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc']
    )
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{标题}</title>
<style>
  @page {{
    size: A4;
    margin: 2cm;
    @top-center {{
      content: "{标题}";
      font-size: 9pt;
      color: #999;
    }}
    @bottom-center {{
      content: "第 " counter(page) " 页";
      font-size: 9pt;
      color: #999;
    }}
  }}
  body {{
    font-family: "Source Han Sans SC", "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 12pt;
    line-height: 1.8;
    color: #333;
    max-width: 100%;
    margin: 0;
    padding: 0;
  }}
  h1 {{
    font-size: 20pt;
    text-align: center;
    color: #1a1a1a;
    border-bottom: 2px solid #1a1a1a;
    padding-bottom: 12px;
    margin-bottom: 24px;
    page-break-after: avoid;
  }}
  h2 {{
    font-size: 16pt;
    color: #333;
    border-left: 4px solid #1a1a1a;
    padding-left: 12px;
    margin-top: 24px;
    page-break-after: avoid;
  }}
  h3 {{
    font-size: 13pt;
    color: #555;
    margin-top: 18px;
  }}
  p {{
    text-indent: 2em;
    margin: 10px 0;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 11pt;
  }}
  th, td {{
    border: 1px solid #ccc;
    padding: 8px 12px;
    text-align: left;
  }}
  th {{
    background: #f5f5f5;
    font-weight: bold;
    text-align: center;
  }}
  code {{
    background: #f5f5f5;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 10pt;
  }}
  pre {{
    background: #f5f5f5;
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 10pt;
    page-break-inside: avoid;
  }}
  hr {{
    border: none;
    border-top: 1px solid #ddd;
    margin: 20px 0;
  }}
  strong {{
    color: #1a1a1a;
  }}
  ul, ol {{
    margin: 10px 0 10px 2em;
  }}
  li {{
    margin: 4px 0;
  }}
  .copyright-header {{
    text-align: center;
    margin-bottom: 30px;
  }}
</style>
</head>
<body>
{html内容}
<footer style="text-align:center;padding:20px;color:#999;font-size:10px;border-top:1px solid #eee;margin-top:40px;">© 2026 云南意念科技有限公司 | tools.yndxw.com | zzx@yndxw.com | 滇ICP备16007314号-1</footer>
</body>
</html>"""


def md转pdf(md内容: str, 标题: str, 输出路径: str) -> bool:
    """将markdown转换为PDF，支持多种后端"""
    import markdown
    import subprocess
    import tempfile
    import os
    
    html = md转html(md内容, 标题)
    
    # 尝试方法1：weasyprint
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        字体配置 = FontConfiguration()
        HTML(string=html).write_pdf(输出路径, font_config=字体配置)
        return True
    except Exception as weasy_error:
        pass
    
    # 尝试方法2：pandoc
    try:
        # 保存HTML到临时文件
        html_path = 输出路径.replace('.pdf', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # 使用pandoc转换为PDF
        result = subprocess.run(
            ['pandoc', html_path, '-o', 输出路径,
             '--pdf-engine=xelatex', '-V', 'mainfont=SimSun',
             '-V', 'geometry:margin=1in', '-V', 'CJKmainfont=SimSun'],
            capture_output=True, timeout=60, check=True
        )
        
        # 清理临时HTML
        if os.path.exists(html_path):
            os.remove(html_path)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # 尝试方法3：wkhtmltopdf
    try:
        # 保存HTML到临时文件
        html_path = 输出路径.replace('.pdf', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        result = subprocess.run(
            ['wkhtmltopdf', '--enable-local-file-access', html_path, 输出路径],
            capture_output=True, timeout=60, check=True
        )
        
        # 清理临时HTML
        if os.path.exists(html_path):
            os.remove(html_path)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print(f"PDF生成失败: weasyprint/pandoc/wkhtmltopdf均不可用，请安装其中之一")
    return False


def md转docx(md内容: str, 标题: str, 输出路径: str) -> bool:
    """将markdown转换为Word文档"""
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    import re
    import markdown
    from markdown.extensions import tables, fenced_code
    
    doc = Document()
    # 设置默认字体
    样式 = doc.styles['Normal']
    字体属性 = 样式.font
    字体属性.name = '宋体'
    字体属性.size = Pt(12)
    # 设置中文字体
    rPr = 样式.element.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), '宋体')
    rPr.insert(0, rFonts)
    
    # 解析markdown
    lines = md内容.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 一级标题
        if line.startswith('# '):
            p = doc.add_heading(line[2:].strip(), level=1)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # 二级标题
        elif line.startswith('## '):
            doc.add_heading(line[3:].strip(), level=2)
        # 三级标题
        elif line.startswith('### '):
            doc.add_heading(line[4:].strip(), level=3)
        # 四级标题
        elif line.startswith('#### '):
            doc.add_heading(line[5:].strip(), level=4)
        # 表格
        elif line.startswith('|'):
            # 收集表格行
            table_lines = []
            while i < len(lines) and lines[i].startswith('|'):
                if not re.match(r'^\|[\s\-\|:]+\|$', lines[i]):
                    table_lines.append(lines[i])
                i += 1
            if table_lines:
                rows_data = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.strip('|').split('|')]
                    rows_data.append(cells)
                if rows_data:
                    cols = len(rows_data[0])
                    tbl = doc.add_table(rows=len(rows_data), cols=cols)
                    tbl.style = 'Table Grid'
                    for ri, row_data in enumerate(rows_data):
                        for ci, cell_text in enumerate(row_data):
                            cell = tbl.rows[ri].cells[ci]
                            cell.text = cell_text
                            if ri == 0:
                                cell.paragraphs[0].runs[0].bold = True
            continue
        # 代码块
        elif line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            if code_lines:
                p = doc.add_paragraph()
                run = p.add_run('\n'.join(code_lines))
                run.font.name = 'Courier New'
                run.font.size = Pt(9)
                rPr = run._element.get_or_add_rPr()
                rFonts = OxmlElement('w:rFonts')
                rFonts.set(qn('w:eastAsia'), '宋体')
                rPr.insert(0, rFonts)
                p.paragraph_format.left_indent = Cm(1)
        # 分隔线
        elif line.strip() == '---':
            doc.add_paragraph('─' * 40)
        # 普通段落
        elif line.strip():
            text = line.strip()
            # 移除markdown标记
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
            
            p = doc.add_paragraph(text)
            p.paragraph_format.first_line_indent = Cm(0.74)  # 2em
        # 空行
        else:
            pass
        
        i += 1
    
    # 添加页脚
    from docx.oxml.ns import qn as ns_qn
    section = doc.sections[0]
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run("© 2026 云南意念科技有限公司 | tools.yndxw.com | zzx@yndxw.com | 滇ICP备16007314号-1")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    rPr = run._element.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(ns_qn('w:eastAsia'), '宋体')
    rPr.insert(0, rFonts)

    doc.save(输出路径)
    return True


def 批量转换项目文档(project_id: str, 项目目录: str):
    """将项目所有markdown文档转换为pdf和docx，使用中文文件名"""
    import os
    结果 = {"pdf": [], "docx": []}
    
    for file in os.listdir(项目目录):
        if not file.endswith('.md'):
            continue
        
        md路径 = os.path.join(项目目录, file)
        with open(md路径, 'r', encoding='utf-8') as f:
            md内容 = f.read()
        
        # 取前50字符作为标题
        first_line = md内容.split('\n')[0] if md内容 else file
        标题 = first_line.lstrip('# ').strip() if first_line.startswith('#') else file.replace('.md', '')
        
        # 中文文件名
        中文名 = 显示名映射.get(file, file)
        
        # PDF
        pdf路径 = os.path.join(项目目录, 中文名.replace('.md', '.pdf'))
        if md转pdf(md内容, 标题, pdf路径):
            结果["pdf"].append(中文名.replace('.md', '.pdf'))
        
        # Word
        docx路径 = os.path.join(项目目录, 中文名.replace('.md', '.docx'))
        if md转docx(md内容, 标题, docx路径):
            结果["docx"].append(中文名.replace('.md', '.docx'))
    
    return 结果

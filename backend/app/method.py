"""Method-evolution view: the skills git repo is the method history."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .config import CONFIG

SKILLS_REPO = Path(CONFIG["skills_repo"])


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(SKILLS_REPO), *args],
        capture_output=True, text=True, timeout=15,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def timeline(limit: int = 50) -> dict:
    raw = git("log", f"-n{limit}", "--pretty=format:%H%x1f%h%x1f%aI%x1f%s%x1f%b%x1e")
    commits = []
    for chunk in raw.split("\x1e"):
        parts = chunk.strip("\n").split("\x1f")
        if len(parts) >= 4:
            commits.append({
                "hash": parts[0].strip(),
                "short": parts[1],
                "date": parts[2],
                "subject": parts[3],
                "body": parts[4].strip() if len(parts) > 4 else "",
            })
    return {
        "head": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "remote": git("remote", "get-url", "origin"),
        "commits": commits,
    }


def skills() -> list[dict]:
    found = []
    for skill_dir in sorted(SKILLS_REPO.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        front = text.split("---", 2)[1] if text.startswith("---\n") else ""
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        desc = re.search(r"^description:\s*(.+)$", front, re.M)
        found.append({
            "dir": skill_dir.name,
            "name": name.group(1).strip() if name else skill_dir.name,
            "description": desc.group(1).strip() if desc else "",
            "body_lines": len(text.splitlines()),
        })
    return found


# ---------- 方法演进脉络:每个版本改了什么、属于哪类 ----------
_CATEGORY_RULES = [
    (re.compile(r"references/module-|references/mechanism"), "机制规则"),
    (re.compile(r"references/historical-training-loop|references/.*loop"), "训练闭环"),
    (re.compile(r"scripts/validate_|scripts/.*seal|scripts/score_|scripts/freeze_"), "校验与封箱"),
    (re.compile(r"scripts/build_live_release|assets/live_release"), "发布链路"),
    (re.compile(r"assets/templates|assets/schemas"), "输出契约"),
    (re.compile(r"scripts/scaffold|scripts/package_self_test|scripts/"), "工具链"),
    (re.compile(r"tests/"), "测试"),
    (re.compile(r"assets/benchmarks|assets/examples"), "课程与示例"),
    (re.compile(r"SKILL\.md$|agents/"), "技能入口"),
]


def _categorize(files: list[str]) -> list[str]:
    cats: list[str] = []
    for f in files:
        for pattern, name in _CATEGORY_RULES:
            if pattern.search(f):
                if name not in cats:
                    cats.append(name)
                break
    return cats or ["其他"]


def evolution(limit: int = 60) -> dict:
    """git log --numstat 解析成结构化脉络:版本 → 类别 → 优化点 → 触及文件。"""
    raw = git("log", f"-n{limit}", "--numstat", "--pretty=format:\x1e%h\x1f%aI\x1f%s\x1f%b\x1d")
    versions = []
    for chunk in raw.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        head, _, stat_part = chunk.partition("\x1d")
        parts = head.split("\x1f")
        if len(parts) < 3:
            continue
        files, adds, dels = [], 0, 0
        for line in stat_part.strip().splitlines():
            cols = line.split("\t")
            if len(cols) == 3:
                a, d, name = cols
                files.append(name)
                adds += int(a) if a.isdigit() else 0
                dels += int(d) if d.isdigit() else 0
        body = parts[3].strip() if len(parts) > 3 else ""
        body = re.sub(r"Co-Authored-By:.*", "", body, flags=re.I).strip()
        points = [ln.strip(" -*") for ln in body.splitlines()
                  if ln.strip().startswith(("-", "*", "1", "2", "3", "4", "5"))][:6]
        versions.append({
            "short": parts[0],
            "date": parts[1],
            "subject": parts[2],
            "body": body,
            "points": points,
            "categories": _categorize(files),
            "files": files[:12],
            "file_count": len(files),
            "adds": adds,
            "dels": dels,
        })
    return {"head": git("rev-parse", "--short", "HEAD"), "versions": versions}


# ---------- 生产 skill 地图:阶段 → 目的 / 硬门槛 / 责任文件(给开发者改方法用) ----------
_LIVE_SKILL = "technology-company-profit-forecasting"

_SKILL_STAGES = [
    {"no": "01", "name": "范围与时间边界", "purpose": "锁定公司口径、财历与 as_of;live 与训练模式路由,时间边界从这里生效。",
     "gates": ["所有证据原始发布时间 ≤ as_of", "财历口径必须显式声明(自然年/财年)"],
     "files": ["SKILL.md", "references/mode-router-and-time-boundary.md", "references/core-forecast-workflow.md"]},
    {"no": "02", "name": "证据摄取与分级(数据处理)", "purpose": "一切数据在这里进包:来源分级 E0(公告/财报)→E4(匿名渠道),记录原始发布时间、内容哈希、用途许可与独立性簇。",
     "gates": ["content_hash 必须真实 sha256 或显式 unhashed:<原因>,不许编造", "非发行人独立来源 ≥2", "E4 只允许用于监控触发,不得进 Base"],
     "files": ["references/core-source-and-evidence.md", "references/research-completeness-and-company-quality.md", "scripts/validate_research_completeness.py"]},
    {"no": "03", "name": "前瞻证据 SignalCards", "purpose": "面向未来的信号卡:家族受控词表、方向/强度/证伪条件、独立性映射;查询日志防答案泄漏。",
     "gates": ["信号 ≥6 · 受控家族 ≥3 · 独立(非官方)家族 ≥1", "技术论文类信号不得直接进 Base 点值", "查询日志禁用结果词(防时间泄漏)"],
     "files": ["references/forward-evidence-and-signal-validation.md", "scripts/validate_forward_evidence_workspace.py"]},
    {"no": "04", "name": "机制路由与建模", "purpose": "利润从哪来:9+1 机制模块(量价成本/产能良率/订阅合同/订单积压/项目转化/平台用量/订户内容/离散会计/口径并表/合资资本 + DTA 子模块)按权重组合,8 个行业透镜提供参数先验。",
     "gates": ["mechanism_weights 必须和为 1", "机制选择要写进 manifest 且与快照一致"],
     "files": ["references/mechanism-router.md"] + ["references/module-*.md"] + ["references/lens-*.md"] + ["references/submodule-dta-valuation-allowance.md"]},
    {"no": "05", "name": "公式化三表模型", "purpose": "model.xlsx 必须公式驱动(收入→利润→现金流勾稽),硬编码数字的工作簿不是模型。",
     "gates": ["公式数 ≥30(manifest 可调)", "#REF!/#NAME? = 硬失败"],
     "files": ["scripts/validate_delivery.py", "assets/examples/generic_v80/README.md"]},
    {"no": "06", "name": "情景与分布输出", "purpose": "FY+1 点值、FY+2 情景(悲观/基准/乐观)、FY+3 分位(p10/p50/p90),快照只允许标准键。",
     "gates": ["canonical 键强制:revenue_point/low/high + profit_point 或 eps_point(方言=拒绝交付)", "scenario_probabilities 和为 1"],
     "files": ["references/core-output-and-valuation.md", "assets/templates/forecast_snapshot_template.json", "assets/schemas/forecast_snapshot.schema.json"]},
    {"no": "07", "name": "估值与买入纪律", "purpose": "DCF/倍数/市场隐含反推三角互证;推荐买入价从悲观公允价加安全边际推导,不许拍脑袋。",
     "gates": ["报告必须含「买入纪律」与「一致性检查」小节", "快照 fair_value 与报告数字必须对账一致"],
     "files": ["references/core-output-and-valuation.md", "references/full-company-delivery-contract.md"]},
    {"no": "08", "name": "独立红队", "purpose": "红队按编号攻击双算、来源独立、估值正常化等;每条 P0/P1 必须闭环或明确降级。",
     "gates": ["开放 P0/P1 时 readiness 必须降为 screen-grade,否则拒绝交付", "红队必须覆盖来源独立性挑战"],
     "files": ["references/full-company-delivery-contract.md"]},
    {"no": "09", "name": "严格交付校验", "purpose": "validate_delivery --strict 是总闸:上述所有门槛在这里机械执行,任何一门不过就不是交付。",
     "gates": ["--strict 模式全部 error 级", "校验结果写入 delivery_validation.json 留痕"],
     "files": ["scripts/validate_delivery.py", "scripts/package_self_test.py"]},
    {"no": "10", "name": "封存与入库", "purpose": "快照哈希封存(训练模式先封箱后见真值),后端摄取为不可变版本行,上看板。",
     "gates": ["训练案例:评分前后各验一次封条;actuals 只进隔离目录", "版本入库后工作区覆盖不再影响历史"],
     "files": ["references/skill-compatibility.md"]},
]


def skill_map() -> dict:
    root = SKILLS_REPO / _LIVE_SKILL
    stages = []
    for stage in _SKILL_STAGES:
        files = []
        for pattern in stage["files"]:
            matches = sorted(root.glob(pattern)) if "*" in pattern else [root / pattern]
            for path in matches:
                rel = str(path.relative_to(root))
                entry = {"path": rel, "exists": path.is_file()}
                if entry["exists"]:
                    try:
                        text = path.read_text(encoding="utf-8", errors="replace")
                        entry["lines"] = len(text.splitlines())
                        for line in text.splitlines():
                            line = line.strip()
                            if line.startswith("#"):
                                entry["title"] = line.lstrip("# ").strip()
                                break
                    except OSError:
                        pass
                files.append(entry)
        stages.append({**stage, "files": files})
    return {"skill": _LIVE_SKILL, "root": str(root), "stages": stages,
            "how_to_change": "改方法 = 编辑对应文件 → 跑 trainer 的 pytest → commit → push;训练轮会沿同一条链自动做(machine 可改,人也可改)。生产 skill 由 build_live_release.py 从 trainer 模板重建,别直接改生产副本。"}


def skill_file(rel_path: str) -> tuple[str, str] | None:
    """Read one file inside the live skill, traversal-safe. Returns (path, text)."""
    root = (SKILLS_REPO / _LIVE_SKILL).resolve()
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix not in {".md", ".py", ".json", ".yaml", ".yml", ".csv", ".jsonl"}:
        return None
    return str(candidate.relative_to(root)), candidate.read_text(encoding="utf-8", errors="replace")[:400_000]

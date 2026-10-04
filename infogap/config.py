"""設定載入:YAML + 環境變數展開。

YAML 中的 "${VAR_NAME}" 會以環境變數取代;缺少的環境變數在「用到該值」時
才會報錯(見 require()),讓只用 Telegram 的人不必設 LINE 的變數。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_ENV_PATTERN = re.compile(r"^\$\{(\w+)\}$")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


class MissingSecretError(RuntimeError):
    """設定值引用的環境變數不存在。失效出聲:不給空字串矇混。"""


def _expand(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    if isinstance(value, str):
        m = _ENV_PATTERN.match(value)
        if m:
            # 延遲報錯:先保留標記,require() 取用時才檢查
            return os.environ.get(m.group(1), value)
    return value


def load_config(path: str | Path | None = None) -> dict:
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"找不到設定檔 {cfg_path},請複製 config/config.example.yaml 為 config/config.yaml"
        )
    with open(cfg_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _expand(raw)


def require(cfg: dict, *keys: str) -> Any:
    """逐層取值;值仍是未展開的 ${VAR} 標記時直接報錯。"""
    node: Any = cfg
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            raise KeyError(f"設定缺少 {'.'.join(keys)}")
        node = node[key]
    if isinstance(node, str) and _ENV_PATTERN.match(node):
        var = _ENV_PATTERN.match(node).group(1)
        raise MissingSecretError(f"環境變數 {var} 未設定(設定項 {'.'.join(keys)})")
    return node

"""解析、匹配和校验上游同步的规则文件。格式见 .github/docs/upstream-sync-design.md 3.1。"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Callable, Iterable

HANDLING = ("follow", "own", "watch", "skip")
RISKS = ("silent", "machine-state", "daily-tool")
GLOB_CHARS = frozenset("*?[")


@dataclass(frozen=True)
class Rule:
    line: int
    kind: str
    pattern: str
    dest: str | None = None
    risk: str | None = None


@dataclass
class Rules:
    base: str | None = None
    handling: list[Rule] = field(default_factory=list)
    risk: list[Rule] = field(default_factory=list)


@dataclass(frozen=True)
class Classification:
    kind: str | None  # None 表示未分类
    local: str | None  # 只有跟随的文件才有本地路径
    risks: tuple[str, ...]
    rule: Rule | None


def parse(text: str) -> tuple[Rules, list[str]]:
    """返回解析结果和语法错误。有错误时，出错的行不进入结果。"""
    rules = Rules()
    errors: list[str] = []
    bases: list[int] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        kind = fields[0]
        if kind == "base":
            if len(fields) != 2:
                errors.append(f"line {number}: base takes exactly one commit")
                continue
            bases.append(number)
            rules.base = fields[1]
        elif kind in HANDLING:
            if len(fields) == 2:
                rules.handling.append(Rule(number, kind, fields[1]))
            elif len(fields) == 4 and fields[2] == ">":
                if kind != "follow":
                    errors.append(f"line {number}: '>' is only allowed on follow rules")
                elif GLOB_CHARS & set(fields[1]):
                    errors.append(f"line {number}: a pattern with '>' must be a literal path")
                else:
                    rules.handling.append(Rule(number, kind, fields[1], dest=fields[3]))
            else:
                errors.append(
                    f"line {number}: expected '{kind} PATTERN' or 'follow PATH > LOCAL_PATH' "
                    "(paths cannot contain spaces)"
                )
        elif kind == "risk":
            if len(fields) != 3:
                errors.append(f"line {number}: expected 'risk CATEGORY PATTERN' (paths cannot contain spaces)")
            elif fields[1] not in RISKS:
                errors.append(f"line {number}: unknown risk category '{fields[1]}', expected one of {', '.join(RISKS)}")
            else:
                rules.risk.append(Rule(number, kind, fields[2], risk=fields[1]))
        else:
            errors.append(f"line {number}: unknown keyword '{kind}'")
    if len(bases) != 1:
        where = f" (lines {', '.join(map(str, bases))})" if bases else ""
        errors.append(f"expected exactly one base line, found {len(bases)}{where}")
    return rules, errors


def matches(pattern: str, path: str) -> bool:
    """按路径层级匹配，和旧清单的规则一致。

    `*`、`?` 和 `[...]` 只匹配一级路径；单独一级的 `**` 匹配零级或多级目录。
    模式匹配到一个目录时，目录下的所有文件也算匹配。
    """
    return _match(pattern.split("/"), path.split("/"))


def _match(pattern: list[str], parts: list[str]) -> bool:
    if not pattern:
        return True
    if not parts:
        return False
    head = pattern[0]
    if head == "**":
        if len(pattern) == 1:
            return True
        return _match(pattern[1:], parts) or _match(pattern, parts[1:])
    return fnmatch.fnmatchcase(parts[0], head) and _match(pattern[1:], parts[1:])


def classify(rules: Rules, path: str) -> Classification:
    rule = None
    for candidate in rules.handling:
        if matches(candidate.pattern, path):
            rule = candidate
    risks = tuple(sorted({r.risk for r in rules.risk if r.risk and matches(r.pattern, path)}))
    if rule is None:
        return Classification(None, None, risks, None)
    local = None
    if rule.kind == "follow":
        local = rule.dest + path[len(rule.pattern):] if rule.dest else path
    return Classification(rule.kind, local, risks, rule)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    unmatched: list[Rule] = field(default_factory=list)
    shadowed: list[Rule] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)


def validate(
    text: str,
    upstream_files: Iterable[str],
    base_exists: Callable[[str], bool],
    local_exists: Callable[[str], bool],
) -> tuple[Rules, Report]:
    """errors 里的问题必须停下来；其余三项只写进报告提醒用户。"""
    rules, errors = parse(text)
    report = Report(errors=errors)
    if rules.base and not base_exists(rules.base):
        report.errors.append(f"base {rules.base} is not on the mirror branch")
    for rule in rules.handling:
        if rule.dest and not local_exists(rule.dest):
            report.errors.append(f"line {rule.line}: local path {rule.dest} does not exist")

    files = list(upstream_files)
    winners: dict[str, Rule] = {}
    for path in files:
        c = classify(rules, path)
        if c.rule is None:
            report.unclassified.append(path)
        else:
            winners[path] = c.rule
    for rule in rules.handling + rules.risk:
        hits = [p for p in files if matches(rule.pattern, p)]
        if not hits:
            report.unmatched.append(rule)
        elif rule.kind != "risk" and all(winners[p] is not rule for p in hits):
            report.shadowed.append(rule)
    return rules, report

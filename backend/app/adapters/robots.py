"""Leitor de robots.txt seguindo a especificação do Google (RFC 9309).

O `urllib.robotparser` do Python não entende curingas (`*`, `$`) e aplica a
primeira regra que casar, o que dá resultado errado em sites como o KaBuM!
(que tem "Disallow: /" seguido de "Allow: /"). Aqui usamos:
- o grupo do user-agent mais específico (ou `*`);
- a regra de caminho MAIS LONGA que casar; em empate, Allow vence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[tuple[bool, str]] = field(default_factory=list)  # (allow?, pattern)


def _pattern_to_regex(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    if anchored:
        pattern = pattern[:-1]
    rx = "".join(".*" if ch == "*" else re.escape(ch) for ch in pattern)
    return re.compile(rx + ("$" if anchored else ""))


class RobotsRules:
    def __init__(self, text: str):
        self.groups: list[_Group] = []
        current: _Group | None = None
        last_was_agent = False
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, value = (p.strip() for p in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if current is None or not last_was_agent:
                    current = _Group()
                    self.groups.append(current)
                current.agents.append(value.lower())
                last_was_agent = True
            elif key in ("allow", "disallow") and current is not None:
                last_was_agent = False
                if value or key == "allow":
                    current.rules.append((key == "allow", value))
            else:
                last_was_agent = False

    def _rules_for(self, agent: str) -> list[tuple[bool, str]]:
        agent = agent.lower()
        specific = [g for g in self.groups if any(a != "*" and a in agent for a in g.agents)]
        if specific:
            return [r for g in specific for r in g.rules]
        return [r for g in self.groups if "*" in g.agents for r in g.rules]

    def can_fetch(self, agent: str, url: str) -> bool:
        parts = urlsplit(url)
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        best_len, best_allow = -1, True
        for allow, pattern in self._rules_for(agent):
            if not pattern:
                continue
            if _pattern_to_regex(pattern).match(path):
                plen = len(pattern)
                if plen > best_len or (plen == best_len and allow):
                    best_len, best_allow = plen, allow
        return best_allow

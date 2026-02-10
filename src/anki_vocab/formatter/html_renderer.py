from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import html

from .html_rules import (
    SKIP_KEYS,
    TAG_OVERRIDES,
    OL_KEYS,
    OL_ITEM_CLASS,
    LIST_ITEM_RULES,
)


class HtmlRenderer:
    """
    규칙(dict)을 해석해서 JSON-like obj(dict/list/scalar)을 HTML로 렌더링하는 엔진.
    """

    def __init__(
        self,
        *,
        safe_class: Callable[[str], str],
        norm_value: Callable[[str, Any], Any],
        join_with: str = "",
    ) -> None:
        self.safe_class = safe_class
        self.norm_value = norm_value
        self.join_with = join_with

    def render(self, obj: Any, *, parent_key: Optional[str] = None) -> str:
        if isinstance(obj, dict):
            return self._render_dict(obj)
        if isinstance(obj, list):
            return self._render_list(obj, parent_key=parent_key)
        return self._render_scalar(obj)

    def _render_dict(self, obj: Dict[str, Any]) -> str:
        parts: List[str] = []

        for k, v in obj.items():
            key = str(k)
            if key in SKIP_KEYS:
                continue

            v = self.norm_value(key, v)

            # senses: <ol class="senses"><li class="sense_item">...</li>...</ol>
            if key in OL_KEYS and isinstance(v, list):
                ol_cls = html.escape(self.safe_class(key), quote=True)
                li_cls = html.escape(self.safe_class(OL_ITEM_CLASS.get(key, "item")), quote=True)

                lis: List[str] = []
                for x in v:
                    inner = self.render(x, parent_key=key)
                    if inner.strip():
                        lis.append(f'<li class="{li_cls}">{inner}</li>')

                parts.append(f'<ol class="{ol_cls}">{"".join(lis)}</ol>')
                continue

            inner = self.render(v, parent_key=key)

            tag = TAG_OVERRIDES.get(key, "span")
            cls = html.escape(self.safe_class(key), quote=True)
            parts.append(f'<{tag} class="{cls}">{inner}</{tag}>')

        return self.join_with.join([p for p in parts if p])

    def _render_list(self, obj: List[Any], *, parent_key: Optional[str]) -> str:
        rule = LIST_ITEM_RULES.get(parent_key or "")

        # examples: wrapper 없이 inner만
        if rule and rule.mode == "raw":
            rendered: List[str] = []
            for x in obj:
                inner = self.render(x, parent_key=parent_key)
                if inner.strip():
                    rendered.append(inner)
            return self.join_with.join(rendered)

        # entries / part_speech: item wrapper
        if rule and rule.mode == "wrap":
            it_tag = rule.item_tag
            it_cls = html.escape(self.safe_class(rule.item_class), quote=True)

            rendered: List[str] = []
            for x in obj:
                inner = self.render(x, parent_key=parent_key)
                if inner.strip():
                    rendered.append(f'<{it_tag} class="{it_cls}">{inner}</{it_tag}>')
            return self.join_with.join(rendered)

        # default list: __item span wrapper
        rendered: List[str] = []
        default_cls = html.escape(self.safe_class("__item"), quote=True)
        for x in obj:
            inner = self.render(x, parent_key=parent_key)
            if inner.strip():
                rendered.append(f'<span class="{default_cls}">{inner}</span>')
        return self.join_with.join(rendered)

    def _render_scalar(self, obj: Any) -> str:
        s = "" if obj is None else str(obj)
        return html.escape(s)

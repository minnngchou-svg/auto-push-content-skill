#!/usr/bin/env python3
"""Monitor AI giveaway signals from linux.do, V2EX, and NodeSeek."""

from __future__ import annotations

import argparse
import email
import html
import imaplib
import json
import re
import smtplib
import ssl
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

try:
    from zoneinfo import ZoneInfo
    from zoneinfo import ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment]


DEFAULT_CONFIG_PATH = Path("config.json")
DEFAULT_STATE_PATH = Path("state.json")
DEFAULT_RUN_LOG_PATH = Path("watcher_runs.jsonl")
DEFAULT_LAST_SENT_BATCH_PATH = Path("last_sent_batch.json")
DEFAULT_SAVED_ARTICLES_DIR = Path("saved_articles")
DEFAULT_SENT_BATCHES_DIR = Path("sent_batches")
DEFAULT_REPLY_STATE_PATH = Path("reply_state.json")
DEFAULT_REPLY_LOG_PATH = Path("reply_actions.jsonl")
DEFAULT_FEEDBACK_PATH = Path("feedback_profiles.json")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)
DEFAULT_SUBJECT_PREFIX = "[linux.do]"
WXPUSHER_API = "https://wxpusher.zjiecode.com/api/send/message"
DEFAULT_PRODUCT_KEYWORDS = [
    "openai",
    "claude",
    "gpt",
    "chatgpt",
    "gemini",
    "cursor",
    "copilot",
    "deepseek",
    "qwen",
    "kimi",
    "豆包",
    "通义",
    "智谱",
    "glm",
    "grok",
    "veo",
    "gemma",
    "mimo",
    "notebooklm",
    "manus",
    "api",
    "token",
    "team",
    "pro",
    "plus",
    "codex",
    "mcp",
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="ignore")


class WatcherError(RuntimeError):
    """Raised for expected runtime failures."""


@dataclass
class Topic:
    source_id: str
    source_label: str
    section: str
    topic_id: int
    title: str
    excerpt: str
    tags: list[str]
    url: str
    created_at_raw: str
    created_at_iso: str
    created_at_display: str
    created_at_ts: float
    score_text: str
    canonical_key: str
    preference_score: int = 0
    merged_sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReplyCommand:
    kind: str
    numbers: list[int] = field(default_factory=list)
    value: str = ""
    raw: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch linux.do/V2EX/NodeSeek and push matched results."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the watcher config JSON file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print matches without sending notifications or updating state.",
    )
    parser.add_argument(
        "--first-run-send",
        action="store_true",
        help="Send matched items on first run instead of just bootstrapping state.",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Delete state before this run.",
    )
    parser.add_argument(
        "--save-numbers",
        help="Save selected topic numbers from the latest sent batch, for example: 1,3,5",
    )
    parser.add_argument(
        "--process-replies-only",
        action="store_true",
        help="Process email replies and save selected topics without fetching new topics.",
    )
    return parser.parse_args()


def load_json(path: Path, *, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise WatcherError(f"File not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WatcherError(f"Invalid JSON in {path}: {exc}") from exc


def save_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def storage_path(config: dict[str, Any], key: str, default_name: str) -> Path:
    config_dir = Path(config.get("_config_dir", "."))
    storage_config = config.get("storage", {})
    return (config_dir / storage_config.get(key, default_name)).resolve()


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def slugify_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.lower()).strip("-")
    return slug[:80] or "topic"


def make_batch_id(checked_at: str) -> str:
    dt = datetime.fromisoformat(checked_at)
    return dt.astimezone(resolve_timezone("Asia/Shanghai") or UTC).strftime("%Y%m%d-%H%M%S")


def request_text(url: str, *, timeout: int, user_agent: str) -> str:
    last_error: WatcherError | None = None
    for attempt in range(3):
        request = Request(
            url,
            headers={
                "Accept": "application/json, text/plain, text/xml, application/xml, */*",
                "User-Agent": user_agent,
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                data = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
            for candidate in (charset, "utf-8", "utf-8-sig", "latin-1"):
                try:
                    return data.decode(candidate, "ignore")
                except LookupError:
                    continue
            return data.decode("utf-8", "ignore")
        except HTTPError as exc:
            raise WatcherError(f"HTTP {exc.code} when requesting {url}") from exc
        except URLError as exc:
            last_error = WatcherError(f"Network error when requesting {url}: {exc.reason}")
        except TimeoutError:
            last_error = WatcherError(f"Request timed out for {url}")
        except OSError as exc:
            last_error = WatcherError(f"Network error when requesting {url}: {exc}")

        if attempt < 2:
            time.sleep(0.8 * (attempt + 1))

    assert last_error is not None
    raise last_error


def request_json(url: str, *, timeout: int, user_agent: str) -> Any:
    text = request_text(url, timeout=timeout, user_agent=user_agent)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise WatcherError(f"Response from {url} is not valid JSON") from exc


def sanitize_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def resolve_timezone(timezone_name: str) -> timezone | None:
    if ZoneInfo is not None:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            pass

    fallback_offsets = {
        "Asia/Shanghai": timezone(timedelta(hours=8)),
        "UTC": UTC,
    }
    return fallback_offsets.get(timezone_name)


def parse_datetime_value(value: Any) -> datetime | None:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=UTC)
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            dt = datetime.fromtimestamp(int(text), tz=UTC)
        else:
            normalized = text.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(normalized)
            except ValueError:
                try:
                    dt = parsedate_to_datetime(text)
                except (TypeError, ValueError, IndexError):
                    return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def format_dt_local(dt: datetime, timezone_name: str) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    tz = resolve_timezone(timezone_name)
    if tz is not None:
        dt = dt.astimezone(tz)
    return dt.strftime("%Y-%m-%d %H:%M")


def build_time_fields(raw_value: Any, timezone_name: str) -> tuple[str, str, str, float]:
    raw_text = str(raw_value or "").strip()
    dt = parse_datetime_value(raw_value)
    if dt is None:
        fallback = raw_text or "unknown"
        return raw_text, "", fallback, 0.0
    return raw_text, dt.isoformat(), format_dt_local(dt, timezone_name), dt.timestamp()


def default_v2ex_entrypoints() -> list[dict[str, Any]]:
    return [
        {"node_name": "openai", "label": "OpenAI"},
        {"node_name": "claude", "label": "Claude"},
        {"node_name": "cursor", "label": "Cursor"},
        {"node_name": "copilot", "label": "GitHub Copilot"},
    ]


def legacy_linux_do_source(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "linux_do",
        "label": "linux.do",
        "enabled": True,
        "kind": "linux_do",
        "base_url": str(source.get("base_url", "https://linux.do")).rstrip("/"),
        "fetch_mode": "latest_json_with_rss_fallback",
        "priority": 10,
        "max_topics": int(source.get("max_topics", 50)),
        "request_timeout_sec": int(source.get("request_timeout_sec", 20)),
        "user_agent": str(source.get("user_agent") or DEFAULT_USER_AGENT),
        "entrypoints": [
            {
                "label": "Latest",
                "list_url": str(source["list_url"]),
                "rss_fallback_url": str(source.get("rss_fallback_url") or "").strip(),
            }
        ],
    }


def normalize_source_config(raw_source: dict[str, Any]) -> dict[str, Any]:
    source = dict(raw_source)
    kind = str(source.get("kind") or source.get("id") or "").strip().lower()
    if not kind:
        raise WatcherError(f"Source is missing kind/id: {source}")

    if kind == "linux.do":
        kind = "linux_do"
    if kind == "nodeseek":
        kind = "rss"

    source_id = str(source.get("id") or kind).strip().replace(".", "_").replace("-", "_")
    label = str(source.get("label") or source_id).strip()
    enabled = bool(source.get("enabled", True))
    base_url = str(source.get("base_url") or "").rstrip("/")
    priority = int(source.get("priority", 999))
    max_topics = int(source.get("max_topics", 50))
    timeout = int(source.get("request_timeout_sec", 20))
    user_agent = str(source.get("user_agent") or DEFAULT_USER_AGENT)
    entrypoints = list(source.get("entrypoints") or [])

    if kind == "linux_do":
        if not base_url:
            base_url = "https://linux.do"
        if not entrypoints:
            entrypoints = [
                {
                    "label": "Latest",
                    "list_url": f"{base_url}/latest.json?order=created&page=0&no_definitions=true",
                    "rss_fallback_url": "",
                }
            ]
    elif kind == "v2ex":
        if not base_url:
            base_url = "https://www.v2ex.com"
        if not entrypoints:
            entrypoints = default_v2ex_entrypoints()
    elif kind == "rss":
        if not entrypoints:
            rss_url = str(source.get("rss_url") or source.get("feed_url") or "").strip()
            if not rss_url:
                raise WatcherError(f"RSS source {label} is missing entrypoints/rss_url")
            entrypoints = [{"label": "Latest", "url": rss_url}]
    else:
        raise WatcherError(f"Unsupported source kind: {kind}")

    return {
        **source,
        "id": source_id,
        "label": label,
        "enabled": enabled,
        "kind": kind,
        "base_url": base_url,
        "priority": priority,
        "max_topics": max_topics,
        "request_timeout_sec": timeout,
        "user_agent": user_agent,
        "entrypoints": entrypoints,
    }


def get_sources(config: dict[str, Any]) -> list[dict[str, Any]]:
    if config.get("_normalized_sources"):
        return list(config["_normalized_sources"])

    raw_sources = config.get("sources")
    if raw_sources:
        sources = [normalize_source_config(item) for item in raw_sources]
    elif config.get("source"):
        sources = [legacy_linux_do_source(config["source"])]
    else:
        raise WatcherError("No source configuration found.")

    sources = [source for source in sources if source.get("enabled", True)]
    if not sources:
        raise WatcherError("No enabled sources found in config.json")
    sources.sort(key=lambda item: int(item.get("priority", 999)))
    config["_normalized_sources"] = sources
    return list(sources)


def get_source_priority_map(config: dict[str, Any]) -> dict[str, int]:
    return {source["id"]: int(source.get("priority", 999)) for source in get_sources(config)}


def topic_record_id(topic: Topic) -> str:
    return f"{topic.source_id}:{topic.topic_id}"


def merged_source_record_ids(topic: Topic) -> list[str]:
    record_ids: list[str] = []
    for item in topic.merged_sources:
        source_id = str(item.get("source_id") or topic.source_id)
        topic_id = str(item.get("topic_id") or topic.topic_id)
        record_ids.append(f"{source_id}:{topic_id}")
    return record_ids or [topic_record_id(topic)]


def detect_product_keywords(config: dict[str, Any]) -> list[str]:
    rules = config.get("filter", {})
    groups = list(rules.get("required_keyword_groups", []))
    if len(groups) >= 2:
        keywords = [str(item).lower() for item in groups[1] if str(item).strip()]
        if keywords:
            return keywords
    return DEFAULT_PRODUCT_KEYWORDS


def normalize_title_for_canonical(title: str) -> str:
    normalized = title.lower()
    normalized = re.sub(r"https?://\S+", " ", normalized)
    normalized = re.sub(r"[\[\]【】()（）'\"“”‘’]", " ", normalized)
    normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized[:120]


def extract_external_reference(text: str, source_base_url: str) -> str:
    source_domain = urlparse(source_base_url).netloc.lower().replace("www.", "")
    for candidate in re.findall(r"https?://[^\s)>\]\"']+", text):
        netloc = urlparse(candidate).netloc.lower().replace("www.", "")
        if netloc and netloc != source_domain:
            parsed = urlparse(candidate)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    return ""


def build_canonical_key(
    *,
    title: str,
    excerpt: str,
    tags: list[str],
    url: str,
    source_base_url: str,
    config: dict[str, Any],
) -> str:
    haystack = "\n".join([title, excerpt, " ".join(tags)]).lower()
    product_keywords = detect_product_keywords(config)
    matched_products = sorted({keyword for keyword in product_keywords if keyword in haystack})
    external_reference = extract_external_reference("\n".join([title, excerpt, url]), source_base_url)
    normalized_title = normalize_title_for_canonical(title)

    if external_reference:
        return f"external:{external_reference}"
    if normalized_title:
        return f"title:{normalized_title}|products:{','.join(matched_products[:6])}"
    return f"url:{url}"


def build_topic(
    *,
    source: dict[str, Any],
    section: str,
    topic_id: int,
    title: str,
    excerpt: str,
    tags: list[str],
    url: str,
    created_value: Any,
    score_text: str,
    config: dict[str, Any],
) -> Topic:
    timezone_name = str(config.get("timezone", "Asia/Shanghai"))
    created_at_raw, created_at_iso, created_at_display, created_at_ts = build_time_fields(
        created_value, timezone_name
    )
    cleaned_tags = [sanitize_text(tag) for tag in tags if sanitize_text(tag)]
    cleaned_title = sanitize_text(title)
    cleaned_excerpt = sanitize_text(excerpt)
    canonical_key = build_canonical_key(
        title=cleaned_title,
        excerpt=cleaned_excerpt,
        tags=cleaned_tags,
        url=url,
        source_base_url=str(source.get("base_url") or url),
        config=config,
    )
    merged_sources = [
        {
            "source_id": source["id"],
            "source_label": source["label"],
            "section": section,
            "url": url,
            "topic_id": topic_id,
            "created_at_display": created_at_display,
            "created_at_ts": created_at_ts,
        }
    ]
    return Topic(
        source_id=source["id"],
        source_label=source["label"],
        section=section,
        topic_id=topic_id,
        title=cleaned_title,
        excerpt=cleaned_excerpt,
        tags=cleaned_tags,
        url=url,
        created_at_raw=created_at_raw,
        created_at_iso=created_at_iso,
        created_at_display=created_at_display,
        created_at_ts=created_at_ts,
        score_text=score_text,
        canonical_key=canonical_key,
        merged_sources=merged_sources,
    )


def extract_topic_id(url: str, guid: str) -> int:
    patterns = [
        r"/topic/(\d+)",
        r"/t/[^/]+/(\d+)",
        r"/post-(\d+)",
        r"/t/(\d+)",
        r"^(\d+)$",
        r"(\d+)(?!.*\d)",
    ]
    for candidate in (url, guid):
        candidate = str(candidate or "").strip()
        if not candidate:
            continue
        for pattern in patterns:
            match = re.search(pattern, candidate)
            if match:
                return int(match.group(1))
    raise WatcherError(f"Could not extract topic id from URL/GUID: {url or guid}")


def normalize_linux_do_json_topics(
    payload: dict[str, Any],
    *,
    source: dict[str, Any],
    config: dict[str, Any],
) -> list[Topic]:
    topics = payload.get("topic_list", {}).get("topics", [])
    normalized_topics: list[Topic] = []
    for item in topics[: int(source.get("max_topics", 50))]:
        topic_id = int(item["id"])
        slug = item.get("slug") or "topic"
        title = item.get("title") or item.get("fancy_title") or ""
        excerpt = item.get("excerpt") or ""
        tags = [str(tag) for tag in item.get("tags", [])]
        created_at_raw = item.get("created_at") or ""
        replies = item.get("reply_count", 0)
        views = item.get("views", 0)
        normalized_topics.append(
            build_topic(
                source=source,
                section="Latest",
                topic_id=topic_id,
                title=title,
                excerpt=excerpt,
                tags=tags,
                url=f"{source['base_url']}/t/{slug}/{topic_id}",
                created_value=created_at_raw,
                score_text=f"replies {replies} / views {views}",
                config=config,
            )
        )
    return normalized_topics


def normalize_rss_topics(
    xml_text: str,
    *,
    source: dict[str, Any],
    config: dict[str, Any],
    default_section: str,
    per_feed_limit: int,
) -> list[Topic]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise WatcherError(f"RSS response for {source['label']} is not valid XML") from exc

    items = root.findall("./channel/item")
    normalized_topics: list[Topic] = []
    for item in items[:per_feed_limit]:
        title = item.findtext("title", default="")
        description = item.findtext("description", default="")
        url = sanitize_text(item.findtext("link", default=""))
        guid = sanitize_text(item.findtext("guid", default=""))
        categories = [sanitize_text(node.text or "") for node in item.findall("category")]
        categories = [category for category in categories if category]
        topic_id = extract_topic_id(url, guid)
        section = categories[0] if categories else default_section
        normalized_topics.append(
            build_topic(
                source=source,
                section=section,
                topic_id=topic_id,
                title=title,
                excerpt=description,
                tags=categories,
                url=url,
                created_value=item.findtext("pubDate", default=""),
                score_text="rss feed",
                config=config,
            )
        )
    return normalized_topics


def normalize_v2ex_topics(
    payload: list[dict[str, Any]],
    *,
    source: dict[str, Any],
    config: dict[str, Any],
    default_section: str,
    per_node_limit: int,
) -> list[Topic]:
    normalized_topics: list[Topic] = []
    for item in payload[:per_node_limit]:
        node = item.get("node", {})
        section = sanitize_text(node.get("title") or default_section or "Latest")
        tags = [sanitize_text(node.get("title") or ""), sanitize_text(node.get("name") or "")]
        normalized_topics.append(
            build_topic(
                source=source,
                section=section,
                topic_id=int(item["id"]),
                title=item.get("title") or "",
                excerpt=item.get("content") or item.get("content_rendered") or "",
                tags=tags,
                url=sanitize_text(item.get("url") or ""),
                created_value=item.get("created") or 0,
                score_text=f"replies {int(item.get('replies', 0))}",
                config=config,
            )
        )
    return normalized_topics


def dedupe_source_topics(topics: list[Topic]) -> list[Topic]:
    by_record: dict[str, Topic] = {}
    for topic in sorted(topics, key=lambda item: item.created_at_ts, reverse=True):
        by_record.setdefault(topic_record_id(topic), topic)
    return list(by_record.values())


def fetch_linux_do_topics(source: dict[str, Any], config: dict[str, Any]) -> list[Topic]:
    entrypoint = dict(source["entrypoints"][0])
    timeout = int(source.get("request_timeout_sec", 20))
    user_agent = str(source.get("user_agent") or DEFAULT_USER_AGENT)
    list_url = str(entrypoint["list_url"])
    rss_fallback_url = str(entrypoint.get("rss_fallback_url") or "").strip()
    try:
        payload = request_json(list_url, timeout=timeout, user_agent=user_agent)
        return normalize_linux_do_json_topics(payload, source=source, config=config)
    except WatcherError:
        if not rss_fallback_url:
            raise
        xml_text = request_text(rss_fallback_url, timeout=timeout, user_agent=user_agent)
        return normalize_rss_topics(
            xml_text,
            source=source,
            config=config,
            default_section=str(entrypoint.get("label") or "Latest"),
            per_feed_limit=int(source.get("max_topics", 50)),
        )


def fetch_v2ex_topics(source: dict[str, Any], config: dict[str, Any]) -> list[Topic]:
    timeout = int(source.get("request_timeout_sec", 20))
    user_agent = str(source.get("user_agent") or DEFAULT_USER_AGENT)
    api_base_url = str(source.get("api_base_url") or "https://www.v2ex.com/api").rstrip("/")
    topics: list[Topic] = []
    default_per_node_limit = int(source.get("per_entry_limit", 20))
    node_errors: list[str] = []
    for entrypoint in source["entrypoints"]:
        node_name = str(entrypoint.get("node_name") or "").strip()
        if not node_name:
            raise WatcherError(f"V2EX entrypoint is missing node_name: {entrypoint}")
        url = str(entrypoint.get("url") or f"{api_base_url}/topics/show.json?node_name={node_name}")
        try:
            payload = request_json(url, timeout=timeout, user_agent=user_agent)
            if not isinstance(payload, list):
                raise WatcherError(f"Unexpected V2EX response for node {node_name}")
            per_node_limit = int(entrypoint.get("limit", default_per_node_limit))
            topics.extend(
                normalize_v2ex_topics(
                    payload,
                    source=source,
                    config=config,
                    default_section=str(entrypoint.get("label") or node_name),
                    per_node_limit=per_node_limit,
                )
            )
        except WatcherError as exc:
            node_errors.append(f"{node_name}: {exc}")
            continue
    if not topics:
        detail = "; ".join(node_errors) or "No V2EX topics fetched."
        raise WatcherError(detail)
    topics = dedupe_source_topics(topics)
    topics.sort(key=lambda item: item.created_at_ts, reverse=True)
    return topics[: int(source.get("max_topics", 50))]


def fetch_rss_source_topics(source: dict[str, Any], config: dict[str, Any]) -> list[Topic]:
    timeout = int(source.get("request_timeout_sec", 20))
    user_agent = str(source.get("user_agent") or DEFAULT_USER_AGENT)
    topics: list[Topic] = []
    default_limit = int(source.get("per_entry_limit", source.get("max_topics", 50)))
    entry_errors: list[str] = []
    for entrypoint in source["entrypoints"]:
        feed_url = str(entrypoint.get("url") or "").strip()
        if not feed_url:
            raise WatcherError(f"RSS entrypoint is missing URL: {entrypoint}")
        try:
            xml_text = request_text(feed_url, timeout=timeout, user_agent=user_agent)
            topics.extend(
                normalize_rss_topics(
                    xml_text,
                    source=source,
                    config=config,
                    default_section=str(entrypoint.get("label") or "Latest"),
                    per_feed_limit=int(entrypoint.get("limit", default_limit)),
                )
            )
        except WatcherError as exc:
            entry_errors.append(f"{feed_url}: {exc}")
            continue
    if not topics:
        detail = "; ".join(entry_errors) or "No RSS topics fetched."
        raise WatcherError(detail)
    topics = dedupe_source_topics(topics)
    topics.sort(key=lambda item: item.created_at_ts, reverse=True)
    return topics[: int(source.get("max_topics", 50))]


def fetch_all_topics(config: dict[str, Any]) -> tuple[list[Topic], list[dict[str, Any]]]:
    topics: list[Topic] = []
    source_errors: list[dict[str, Any]] = []
    for source in get_sources(config):
        try:
            if source["kind"] == "linux_do":
                source_topics = fetch_linux_do_topics(source, config)
            elif source["kind"] == "v2ex":
                source_topics = fetch_v2ex_topics(source, config)
            elif source["kind"] == "rss":
                source_topics = fetch_rss_source_topics(source, config)
            else:
                raise WatcherError(f"Unsupported source kind: {source['kind']}")
        except WatcherError as exc:
            source_errors.append(
                {
                    "source_id": source["id"],
                    "source_label": source["label"],
                    "error": str(exc),
                }
            )
            continue
        topics.extend(source_topics)

    if not topics and source_errors:
        details = "; ".join(f"{item['source_label']}: {item['error']}" for item in source_errors)
        raise WatcherError(f"All sources failed: {details}")
    return dedupe_source_topics(topics), source_errors


def topic_matches(topic: Topic, config: dict[str, Any]) -> bool:
    rules = config["filter"]
    keywords = [str(item).lower() for item in rules.get("keywords", []) if str(item).strip()]
    required_keyword_groups = [
        [str(item).lower() for item in group if str(item).strip()]
        for group in rules.get("required_keyword_groups", [])
    ]
    exclude_keywords = [
        str(item).lower() for item in rules.get("exclude_keywords", []) if str(item).strip()
    ]
    require_any_tags = [str(item).lower() for item in rules.get("require_any_tags", []) if str(item).strip()]

    haystack_parts = [
        topic.title,
        topic.excerpt,
        topic.section,
        topic.source_label,
        " ".join(topic.tags),
    ]
    haystack = "\n".join(haystack_parts).lower()
    topic_tags = {tag.lower() for tag in topic.tags}

    if keywords and not any(keyword in haystack for keyword in keywords):
        return False
    for group in required_keyword_groups:
        if group and not any(keyword in haystack for keyword in group):
            return False
    if exclude_keywords and any(keyword in haystack for keyword in exclude_keywords):
        return False
    if require_any_tags and not topic_tags.intersection(require_any_tags):
        return False
    return True


def choose_primary_topic(current: Topic, candidate: Topic, config: dict[str, Any]) -> Topic:
    priority_map = get_source_priority_map(config)
    current_priority = priority_map.get(current.source_id, 999)
    candidate_priority = priority_map.get(candidate.source_id, 999)
    if candidate_priority < current_priority:
        return candidate
    if candidate_priority > current_priority:
        return current
    if candidate.created_at_ts > current.created_at_ts:
        return candidate
    return current


def merge_topics(topics: list[Topic], config: dict[str, Any]) -> list[Topic]:
    merged: dict[str, Topic] = {}
    priority_map = get_source_priority_map(config)
    for topic in topics:
        existing = merged.get(topic.canonical_key)
        if existing is None:
            merged[topic.canonical_key] = topic
            continue

        primary = choose_primary_topic(existing, topic, config)
        secondary = topic if primary is existing else existing
        merged_sources = {
            f"{item['source_id']}:{item['topic_id']}": item for item in primary.merged_sources
        }
        for item in secondary.merged_sources:
            merged_sources[f"{item['source_id']}:{item['topic_id']}"] = item

        primary.merged_sources = sorted(
            merged_sources.values(),
            key=lambda item: (
                priority_map.get(str(item.get("source_id")), 999),
                -float(item.get("created_at_ts", 0.0)),
            ),
        )
        primary.tags = sorted(set(primary.tags + secondary.tags))
        if len(primary.excerpt) < len(secondary.excerpt):
            primary.excerpt = secondary.excerpt
        if secondary.created_at_ts > primary.created_at_ts:
            primary.created_at_ts = secondary.created_at_ts
            primary.created_at_iso = secondary.created_at_iso
            primary.created_at_raw = secondary.created_at_raw
            primary.created_at_display = secondary.created_at_display
        merged[topic.canonical_key] = primary

    return list(merged.values())


def order_topics_for_sections(topics: list[Topic], config: dict[str, Any]) -> list[Topic]:
    priority_map = get_source_priority_map(config)
    grouped: dict[str, list[Topic]] = {}
    for topic in topics:
        grouped.setdefault(topic.source_id, []).append(topic)

    ordered: list[Topic] = []
    for source_id, _priority in sorted(priority_map.items(), key=lambda item: item[1]):
        source_topics = grouped.pop(source_id, [])
        source_topics.sort(key=lambda item: (item.preference_score, item.created_at_ts), reverse=True)
        ordered.extend(source_topics)
    for source_id in sorted(grouped):
        source_topics = grouped[source_id]
        source_topics.sort(key=lambda item: (item.preference_score, item.created_at_ts), reverse=True)
        ordered.extend(source_topics)
    return ordered


def source_name_map(config: dict[str, Any]) -> dict[str, str]:
    return {source["id"]: source["label"] for source in get_sources(config)}


def format_merged_sources(topic: Topic) -> str:
    items = []
    for item in topic.merged_sources:
        if (
            str(item.get("source_id") or "") == topic.source_id
            and str(item.get("topic_id") or "") == str(topic.topic_id)
        ):
            continue
        source_label = str(item.get("source_label") or topic.source_label)
        section = str(item.get("section") or "").strip()
        if section:
            items.append(f"{source_label} / {section}")
        else:
            items.append(source_label)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return ", ".join(deduped)


def dedupe_preserve_order(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = str(item).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped


def extract_text_fields(record: dict[str, Any]) -> str:
    parts = [
        str(record.get("title", "")),
        str(record.get("excerpt", "")),
        str(record.get("section", "")),
        " ".join(str(tag) for tag in record.get("tags", [])),
    ]
    return "\n".join(parts)


def extract_entry_links(record: dict[str, Any]) -> list[str]:
    source_url = str(record.get("url") or "").strip()
    text = "\n".join([extract_text_fields(record), source_url])
    matches = re.findall(r"https?://[^\s)>\]\"']+", text)
    links: list[str] = []
    for link in matches:
        cleaned = link.rstrip(".,)")
        if cleaned == source_url:
            continue
        links.append(cleaned)
    return dedupe_preserve_order(links)


def detect_product_info(record: dict[str, Any]) -> tuple[str, str]:
    haystack = extract_text_fields(record).lower()
    product_map = [
        ("claude", "Claude", ["claude", "cc plan", "anthropic"]),
        ("openai", "OpenAI", ["openai", "chatgpt", "gpt"]),
        ("cursor", "Cursor", ["cursor"]),
        ("copilot", "GitHub Copilot", ["copilot"]),
        ("gemini", "Gemini", ["gemini"]),
        ("deepseek", "DeepSeek", ["deepseek"]),
        ("qwen", "Qwen", ["qwen", "通义"]),
        ("kimi", "Kimi", ["kimi"]),
        ("doubao", "豆包", ["豆包"]),
        ("grok", "Grok", ["grok"]),
        ("codex", "Codex", ["codex"]),
        ("mcp", "MCP", ["mcp"]),
    ]
    for product_id, label, keywords in product_map:
        if any(keyword in haystack for keyword in keywords):
            return product_id, label
    return "unknown", "Unknown"


def detect_benefit_type_info(record: dict[str, Any]) -> tuple[str, str]:
    haystack = extract_text_fields(record).lower()
    if any(keyword in haystack for keyword in ["兑换码", "激活码", "邀请码", "注册码", "invite"]):
        return "code", "邀请码/兑换码"
    if any(keyword in haystack for keyword in ["抽奖", "开奖", "中奖", "raffle", "lottery"]):
        return "raffle", "抽奖活动"
    if any(keyword in haystack for keyword in ["credits", "credit", "额度", "token", "送码"]):
        return "credits", "免费额度"
    if any(keyword in haystack for keyword in ["免费", "试用", "限时免费", "白嫖", "体验"]):
        return "trial", "免费试用"
    if any(keyword in haystack for keyword in ["教程", "攻略", "指南", "经验", "复盘"]):
        return "guide", "教程经验"
    if any(keyword in haystack for keyword in ["发布", "上线", "开源", "更新", "公告"]):
        return "news", "产品动态"
    return "other", "其他"


def detect_target_audience(record: dict[str, Any]) -> str:
    haystack = extract_text_fields(record).lower()
    audience_map = [
        ("学生", ["学生", "edu", "校园"]),
        ("新用户", ["新用户", "注册", "首次"]),
        ("团队/企业", ["team", "business", "企业", "团队"]),
        ("开发者", ["api", "开发者", "程序员", "codex", "mcp"]),
    ]
    for label, keywords in audience_map:
        if any(keyword in haystack for keyword in keywords):
            return label
    return ""


def detect_requires_invite(record: dict[str, Any]) -> bool | None:
    haystack = extract_text_fields(record).lower()
    if any(keyword in haystack for keyword in ["无需邀请码", "免邀请码", "开放注册", "公开注册"]):
        return False
    if any(keyword in haystack for keyword in ["邀请码", "invite code", "邀请链接", "受邀", "邀请制"]):
        return True
    return None


def parse_datetime_candidates(text: str, timezone_name: str) -> list[datetime]:
    candidates: list[datetime] = []
    tz = resolve_timezone(timezone_name) or UTC

    for match in re.finditer(
        r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:\s+(\d{1,2})(?::(\d{2}))?)?",
        text,
    ):
        year, month, day, hour, minute = match.groups()
        dt = datetime(
            int(year),
            int(month),
            int(day),
            int(hour or 0),
            int(minute or 0),
            tzinfo=tz,
        )
        candidates.append(dt.astimezone(UTC))

    current_year = datetime.now(tz=tz).year
    for match in re.finditer(r"(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2})[:：点](\d{1,2})?)?", text):
        month, day, hour, minute = match.groups()
        dt = datetime(
            current_year,
            int(month),
            int(day),
            int(hour or 0),
            int(minute or 0),
            tzinfo=tz,
        )
        candidates.append(dt.astimezone(UTC))

    for match in re.finditer(
        r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M\s+[A-Z]{2,4}",
        text,
    ):
        parsed = parse_datetime_value(match.group(0))
        if parsed is not None:
            candidates.append(parsed)

    return candidates


def detect_deadline_info(record: dict[str, Any], timezone_name: str) -> tuple[str, str]:
    text = extract_text_fields(record)
    keyword_positions = [
        text.lower().find(keyword)
        for keyword in ["截止", "截至", "结束", "活动时间", "到期", "end", "deadline"]
        if text.lower().find(keyword) >= 0
    ]
    windows: list[str] = []
    if keyword_positions:
        for position in keyword_positions:
            windows.append(text[position : position + 160])
    else:
        windows.append(text)

    matches: list[datetime] = []
    for window in windows:
        matches.extend(parse_datetime_candidates(window, timezone_name))
    if not matches:
        return "", ""
    deadline = max(matches)
    return deadline.isoformat(), format_dt_local(deadline, timezone_name)


def preference_bool_display(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def get_feedback_path(config: dict[str, Any]) -> Path:
    return storage_path(config, "feedback_file", DEFAULT_FEEDBACK_PATH.name)


def load_feedback_data(config: dict[str, Any]) -> dict[str, Any]:
    path = get_feedback_path(config)
    return load_json(
        path,
        default={
            "positive_signals": {},
            "negative_signals": {},
            "history": [],
        },
    )


def save_feedback_data(config: dict[str, Any], data: dict[str, Any]) -> None:
    save_json(get_feedback_path(config), data)


def extract_preference_signals(record: dict[str, Any]) -> list[str]:
    product_id, _ = detect_product_info(record)
    benefit_type, _ = detect_benefit_type_info(record)
    section_slug = normalize_title_for_canonical(str(record.get("section", ""))).replace(" ", "-")
    signals = [
        f"source:{record.get('source_id') or 'linux_do'}",
        f"category:{record.get('category', classify_topic_record(record)[0])}",
        f"benefit:{benefit_type}",
    ]
    if section_slug:
        signals.append(f"section:{section_slug}")
    if product_id != "unknown":
        signals.append(f"product:{product_id}")
    return dedupe_preserve_order(signals)


def score_record_feedback(record: dict[str, Any], feedback_data: dict[str, Any]) -> int:
    positive = dict(feedback_data.get("positive_signals", {}))
    negative = dict(feedback_data.get("negative_signals", {}))
    score = 0
    for signal in extract_preference_signals(record):
        score += int(positive.get(signal, 0))
        score -= int(negative.get(signal, 0))
    return score


def record_from_topic(topic: Topic) -> dict[str, Any]:
    return {
        "source_id": topic.source_id,
        "source_label": topic.source_label,
        "section": topic.section,
        "topic_id": topic.topic_id,
        "title": topic.title,
        "excerpt": topic.excerpt,
        "tags": topic.tags,
        "url": topic.url,
        "created_at_raw": topic.created_at_raw,
        "created_at_iso": topic.created_at_iso,
        "created_at_display": topic.created_at_display,
        "created_at_ts": topic.created_at_ts,
        "score_text": topic.score_text,
        "canonical_key": topic.canonical_key,
        "merged_sources": topic.merged_sources,
        "preference_score": topic.preference_score,
    }


def apply_feedback_scores_to_topics(topics: list[Topic], config: dict[str, Any]) -> list[Topic]:
    feedback_data = load_feedback_data(config)
    for topic in topics:
        topic.preference_score = score_record_feedback(record_from_topic(topic), feedback_data)
    return topics


def enrich_record_metadata(
    record: dict[str, Any],
    *,
    config: dict[str, Any],
    existing: dict[str, Any] | None = None,
    note_override: str | None = None,
) -> dict[str, Any]:
    existing = existing or {}
    normalized_record = {
        **record,
        "source_id": record.get("source_id") or existing.get("source_id") or "linux_do",
        "source_label": record.get("source_label") or existing.get("source_label") or "linux.do",
        "section": record.get("section") or existing.get("section") or "",
    }
    timezone_name = str(config.get("timezone", "Asia/Shanghai"))
    product_id, product_label = detect_product_info(normalized_record)
    benefit_type, benefit_label = detect_benefit_type_info(normalized_record)
    deadline_iso, deadline_display = detect_deadline_info(normalized_record, timezone_name)
    note_value = note_override if note_override is not None else str(existing.get("note") or normalized_record.get("note") or "")
    feedback_data = load_feedback_data(config)

    enriched = {
        **normalized_record,
        "product_id": product_id,
        "product_label": product_label,
        "benefit_type": benefit_type,
        "benefit_type_label": benefit_label,
        "deadline_iso": deadline_iso,
        "deadline_display": deadline_display,
        "target_audience": str(existing.get("target_audience") or detect_target_audience(normalized_record)),
        "requires_invite": (
            existing["requires_invite"]
            if "requires_invite" in existing and existing["requires_invite"] is not None
            else detect_requires_invite(normalized_record)
        ),
        "entry_links": dedupe_preserve_order(
            list(existing.get("entry_links", [])) + extract_entry_links(normalized_record)
        ),
        "note": note_value.strip(),
    }
    enriched["preference_score"] = score_record_feedback(enriched, feedback_data)
    return enriched


def apply_feedback_command(
    config: dict[str, Any],
    record: dict[str, Any],
    *,
    direction: str,
) -> dict[str, Any]:
    feedback_data = load_feedback_data(config)
    bucket_name = "positive_signals" if direction == "like" else "negative_signals"
    bucket = dict(feedback_data.get(bucket_name, {}))
    signals = extract_preference_signals(record)
    for signal in signals:
        bucket[signal] = int(bucket.get(signal, 0)) + 1
    feedback_data[bucket_name] = bucket
    history = list(feedback_data.get("history", []))
    history.append(
        {
            "at": utc_now_iso(),
            "direction": direction,
            "record_id": f"{record.get('source_id') or 'linux_do'}:{record.get('topic_id', 'unknown')}",
            "title": record.get("title", ""),
            "signals": signals,
        }
    )
    feedback_data["history"] = history[-500:]
    save_feedback_data(config, feedback_data)
    return {"direction": direction, "signals": signals}


def get_subject_prefix(config: dict[str, Any]) -> str:
    push_config = config.get("push", {})
    return str(push_config.get("subject_prefix") or DEFAULT_SUBJECT_PREFIX)


def build_plaintext_message(topics: list[Topic], *, batch_id: str, config: dict[str, Any]) -> tuple[str, str]:
    subject = f"{get_subject_prefix(config)}[batch {batch_id}] {len(topics)} new matched topic(s)"
    lines = [
        subject,
        "",
        f"Batch ID: {batch_id}",
        "Reply commands:",
        "- 1 3 5  => save selected items",
        "- 2+     => prefer similar items",
        "- 3-     => push fewer similar items",
        "- 4 note: this looks legit",
        "",
    ]

    ordered_topics = order_topics_for_sections(topics, config)
    source_map = source_name_map(config)
    priority_map = get_source_priority_map(config)
    number = 1
    for source_id, source_label in sorted(source_map.items(), key=lambda item: priority_map.get(item[0], 999)):
        source_topics = [topic for topic in ordered_topics if topic.source_id == source_id]
        if not source_topics:
            continue
        lines.extend([f"=== {source_label} ({len(source_topics)}) ===", ""])
        for topic in source_topics:
            tags = ", ".join(topic.tags) if topic.tags else "none"
            lines.extend(
                [
                    f"{number}. {topic.title}",
                    f"Time: {topic.created_at_display}",
                    f"Section: {topic.section or 'unknown'}",
                    f"Tags: {tags}",
                    f"Score: {topic.score_text}",
                    f"Link: {topic.url}",
                ]
            )
            if len(topic.merged_sources) > 1:
                lines.append(f"Also seen on: {format_merged_sources(topic)}")
            if topic.excerpt:
                lines.append(f"Summary: {topic.excerpt}")
            lines.append("")
            number += 1

    body = "\n".join(lines).strip() + "\n"
    return subject, body


def build_markdown_message(topics: list[Topic], *, batch_id: str, config: dict[str, Any]) -> tuple[str, str]:
    title = f"AI Watcher {len(topics)} new matched topic(s)"
    chunks = [
        f"# {title}",
        "",
        f"- Batch ID: `{batch_id}`",
        "- Reply commands: `1 3 5`, `2+`, `3-`, `4 note: ...`",
        "",
    ]

    ordered_topics = order_topics_for_sections(topics, config)
    source_map = source_name_map(config)
    priority_map = get_source_priority_map(config)
    number = 1
    for source_id, source_label in sorted(source_map.items(), key=lambda item: priority_map.get(item[0], 999)):
        source_topics = [topic for topic in ordered_topics if topic.source_id == source_id]
        if not source_topics:
            continue
        chunks.extend([f"## {source_label} ({len(source_topics)})", ""])
        for topic in source_topics:
            tags = " / ".join(topic.tags) if topic.tags else "none"
            chunks.extend(
                [
                    f"### {number}. [{topic.title}]({topic.url})",
                    f"- Time: {topic.created_at_display}",
                    f"- Section: {topic.section or 'unknown'}",
                    f"- Tags: {tags}",
                    f"- Score: {topic.score_text}",
                ]
            )
            if len(topic.merged_sources) > 1:
                chunks.append(f"- Also seen on: {format_merged_sources(topic)}")
            if topic.excerpt:
                chunks.append(f"- Summary: {topic.excerpt}")
            chunks.append("")
            number += 1
    return title, "\n".join(chunks).strip()


def topic_to_record(topic: Topic, *, number: int) -> dict[str, Any]:
    return {
        "number": number,
        "source_id": topic.source_id,
        "source_label": topic.source_label,
        "section": topic.section,
        "topic_id": topic.topic_id,
        "title": topic.title,
        "excerpt": topic.excerpt,
        "tags": topic.tags,
        "url": topic.url,
        "created_at_raw": topic.created_at_raw,
        "created_at_iso": topic.created_at_iso,
        "created_at_display": topic.created_at_display,
        "created_at_ts": topic.created_at_ts,
        "score_text": topic.score_text,
        "canonical_key": topic.canonical_key,
        "preference_score": topic.preference_score,
        "merged_sources": topic.merged_sources,
    }


def save_last_sent_batch(
    path: Path,
    topics: list[Topic],
    *,
    sent_at: str,
    batch_id: str,
    subject: str,
    config: dict[str, Any],
) -> None:
    ordered_topics = order_topics_for_sections(topics, config)
    payload = {
        "batch_id": batch_id,
        "sent_at": sent_at,
        "subject": subject,
        "topics": [topic_to_record(topic, number=index) for index, topic in enumerate(ordered_topics, start=1)],
    }
    save_json(path, payload)


def save_batch_history(
    batches_dir: Path,
    topics: list[Topic],
    *,
    sent_at: str,
    batch_id: str,
    subject: str,
    config: dict[str, Any],
) -> Path:
    batches_dir.mkdir(parents=True, exist_ok=True)
    batch_path = batches_dir / f"{batch_id}.json"
    save_last_sent_batch(batch_path, topics, sent_at=sent_at, batch_id=batch_id, subject=subject, config=config)
    return batch_path


def parse_selection_numbers(value: str) -> list[int]:
    items = [item for item in re.split(r"[\s,，]+", value.strip()) if item]
    numbers: list[int] = []
    for item in items:
        if not item.isdigit():
            raise WatcherError(f"Invalid selection number: {item}")
        numbers.append(int(item))
    if not numbers:
        raise WatcherError("No selection numbers were provided.")
    return numbers


def classify_topic_record(record: dict[str, Any]) -> tuple[str, str]:
    text_parts = [
        str(record.get("title", "")),
        str(record.get("excerpt", "")),
        str(record.get("section", "")),
        " ".join(str(tag) for tag in record.get("tags", [])),
    ]
    haystack = "\n".join(text_parts).lower()

    offers_keywords = [
        "白嫖",
        "免费",
        "试用",
        "限时免费",
        "兑换码",
        "邀请码",
        "抽奖",
        "赠送",
        "福利",
        "额度",
        "token",
        "credits",
        "credit",
        "plus",
        "team",
        "pro",
    ]
    news_keywords = [
        "快讯",
        "发布",
        "上线",
        "接入",
        "更新",
        "推出",
        "公告",
        "开源",
        "preview",
        "beta",
    ]
    guide_keywords = [
        "教程",
        "攻略",
        "指南",
        "经验",
        "总结",
        "复盘",
        "测评",
        "评测",
        "搭建",
    ]
    tools_keywords = [
        "工具",
        "插件",
        "脚本",
        "项目",
        "workflow",
        "mcp",
        "agent",
        "sdk",
        "extension",
    ]

    if any(keyword in haystack for keyword in offers_keywords):
        return ("offers", "Offers / 福利试用")
    if any(keyword in haystack for keyword in news_keywords):
        return ("news", "News / 产品动态")
    if any(keyword in haystack for keyword in guide_keywords):
        return ("guides", "Guides / 教程经验")
    if any(keyword in haystack for keyword in tools_keywords):
        return ("tools", "Tools / 工具项目")
    return ("other", "Other / 其他")


def article_created_sort_key(record: dict[str, Any]) -> float:
    try:
        return float(record.get("created_at_ts") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def record_unique_key(record: dict[str, Any]) -> str:
    return f"{record.get('source_id') or 'linux_do'}:{record.get('topic_id', 'unknown')}"


def merged_sources_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    items = list(record.get("merged_sources") or [])
    if items:
        return items
    return [
        {
            "source_id": record.get("source_id", "linux_do"),
            "source_label": record.get("source_label", "linux.do"),
            "section": record.get("section", ""),
            "url": record.get("url", ""),
            "topic_id": record.get("topic_id", ""),
            "created_at_display": record.get("created_at_display", ""),
            "created_at_ts": record.get("created_at_ts", 0),
        }
    ]


def additional_sources_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    primary_source_id = str(record.get("source_id") or "")
    primary_topic_id = str(record.get("topic_id") or "")
    extras: list[dict[str, Any]] = []
    for item in merged_sources_for_record(record):
        if (
            str(item.get("source_id") or "") == primary_source_id
            and str(item.get("topic_id") or "") == primary_topic_id
        ):
            continue
        extras.append(item)
    return extras


def render_saved_article(record: dict[str, Any], *, category_label: str, saved_at: str) -> str:
    tags = ", ".join(str(tag) for tag in record.get("tags", [])) or "none"
    merged_sources = additional_sources_for_record(record)
    entry_links = list(record.get("entry_links", []))
    lines = [
        f"# {record['title']}",
        "",
        "## Metadata",
        "",
        f"- Saved at: {saved_at}",
        f"- Category: {category_label}",
        f"- Benefit type: {record.get('benefit_type_label', '其他')}",
        f"- Product: {record.get('product_label', 'Unknown')}",
        f"- Original time: {record.get('created_at_display', 'unknown')}",
        f"- Deadline: {record.get('deadline_display', 'unknown') or 'unknown'}",
        f"- Target audience: {record.get('target_audience', '') or 'unknown'}",
        f"- Requires invite: {preference_bool_display(record.get('requires_invite'))}",
        f"- Preference score: {record.get('preference_score', 0)}",
        f"- Source site: {record.get('source_label', 'unknown')}",
        f"- Source section: {record.get('section', 'unknown') or 'unknown'}",
        f"- Tags: {tags}",
        f"- Source URL: {record['url']}",
    ]
    if entry_links:
        lines.append("- Entry links:")
        for link in entry_links:
            lines.append(f"  - {link}")
    if len(merged_sources) > 1:
        lines.append("- Also seen on:")
        for item in merged_sources:
            source_label = str(item.get("source_label") or "unknown")
            section = str(item.get("section") or "").strip()
            url = str(item.get("url") or "").strip()
            suffix = f" / {section}" if section else ""
            lines.append(f"  - {source_label}{suffix}: {url}")
    if str(record.get("note") or "").strip():
        lines.extend(["", "## Note", "", str(record.get("note")).strip()])
    lines.extend(
        [
            "",
            "## Summary",
            "",
            str(record.get("excerpt") or "No summary captured."),
            "",
        ]
    )
    return "\n".join(lines)


def is_active_offer(record: dict[str, Any]) -> bool:
    if str(record.get("category") or "") != "offers":
        return False
    deadline_iso = str(record.get("deadline_iso") or "").strip()
    if not deadline_iso:
        return True
    deadline = parse_datetime_value(deadline_iso)
    if deadline is None:
        return True
    return deadline >= datetime.now(tz=UTC)


def write_auxiliary_indexes(base_dir: Path, library: list[dict[str, Any]]) -> None:
    active_records = [item for item in library if is_active_offer(item)]
    active_lines = ["# Active Offers", ""]
    if not active_records:
        active_lines.append("No active offers yet.")
    else:
        for item in active_records:
            filename = Path(str(item.get("relative_path") or "")).name
            active_lines.extend(
                [
                    f"## {item['title']}",
                    "",
                    f"- Deadline: {item.get('deadline_display', 'unknown') or 'unknown'}",
                    f"- Product: {item.get('product_label', 'Unknown')}",
                    f"- Source: {item.get('source_label', 'unknown')} / {item.get('section', 'unknown') or 'unknown'}",
                    f"- File: [{filename}]({item['relative_path'].replace(chr(92), '/')})",
                    "",
                ]
            )
    (base_dir / "active_offers.md").write_text(
        "\n".join(active_lines).strip() + "\n",
        encoding="utf-8",
    )

    grouped_by_product: dict[str, list[dict[str, Any]]] = {}
    for item in library:
        grouped_by_product.setdefault(str(item.get("product_label") or "Unknown"), []).append(item)
    product_lines = ["# By Product", ""]
    for product in sorted(grouped_by_product):
        items = sorted(grouped_by_product[product], key=article_created_sort_key, reverse=True)
        product_lines.extend([f"## {product}", ""])
        for item in items:
            filename = Path(str(item.get("relative_path") or "")).name
            product_lines.extend(
                [
                    f"- {item['title']} ({item.get('source_label', 'unknown')})",
                    f"  File: [{filename}]({item['relative_path'].replace(chr(92), '/')})",
                ]
            )
        product_lines.append("")
    (base_dir / "by_product.md").write_text(
        "\n".join(product_lines).strip() + "\n",
        encoding="utf-8",
    )


def rewrite_saved_articles(base_dir: Path, library: list[dict[str, Any]]) -> None:
    for item in library:
        relative_path = Path(str(item.get("relative_path") or ""))
        if not relative_path:
            continue
        article_path = base_dir / relative_path
        article_path.parent.mkdir(parents=True, exist_ok=True)
        article_path.write_text(
            render_saved_article(
                item,
                category_label=str(item.get("category_label") or "Other / 其他"),
                saved_at=str(item.get("saved_at") or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")),
            ),
            encoding="utf-8",
        )


def update_saved_indexes(base_dir: Path, library_path: Path, library: list[dict[str, Any]]) -> None:
    sorted_library = sorted(
        library,
        key=article_created_sort_key,
        reverse=True,
    )

    rewrite_saved_articles(base_dir, sorted_library)

    summary_lines = ["# Saved Articles", ""]
    summary_lines.extend(
        [
            "- Active offers: [active_offers.md](active_offers.md)",
            "- By product: [by_product.md](by_product.md)",
            "",
        ]
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in sorted_library:
        grouped.setdefault(item["category"], []).append(item)

    for category, items in grouped.items():
        label = items[0]["category_label"]
        summary_lines.append(f"## {label}")
        summary_lines.append("")
        summary_lines.append(f"- Count: {len(items)}")
        summary_lines.append(f"- Index: [{category}/index.md]({category}/index.md)")
        summary_lines.append("")

        category_dir = base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        category_lines = [f"# {label}", ""]
        for item in items:
            source_label = item.get("source_label", "unknown")
            merged_sources = additional_sources_for_record(item)
            category_lines.extend(
                [
                    f"## {item['title']}",
                    "",
                    f"- Original time: {item.get('created_at_display', 'unknown')}",
                    f"- Saved at: {item['saved_at']}",
                    f"- Source site: {source_label}",
                    f"- Source section: {item.get('section', 'unknown') or 'unknown'}",
                    f"- Benefit type: {item.get('benefit_type_label', '其他')}",
                    f"- Product: {item.get('product_label', 'Unknown')}",
                    f"- Deadline: {item.get('deadline_display', 'unknown') or 'unknown'}",
                    f"- Note: {item.get('note', '') or 'none'}",
                    f"- Source URL: {item['url']}",
                ]
            )
            if len(merged_sources) > 1:
                category_lines.append(
                    "- Also seen on: "
                    + ", ".join(
                        f"{entry.get('source_label', 'unknown')}"
                        + (f" / {entry.get('section')}" if entry.get("section") else "")
                        for entry in merged_sources
                    )
                )
            category_lines.extend(
                [
                    f"- File: [{Path(item['relative_path']).name}]({Path(item['relative_path']).name})",
                    "",
                ]
            )
        (category_dir / "index.md").write_text(
            "\n".join(category_lines).strip() + "\n",
            encoding="utf-8",
        )

    (base_dir / "README.md").write_text(
        "\n".join(summary_lines).strip() + "\n",
        encoding="utf-8",
    )
    write_auxiliary_indexes(base_dir, sorted_library)
    save_json(library_path, sorted_library)


def load_batch_payload(config: dict[str, Any], *, batch_id: str | None = None) -> dict[str, Any]:
    storage_config = config.get("storage", {})
    config_dir = Path(config.get("_config_dir", "."))
    if batch_id:
        batch_path = (
            config_dir / storage_config.get("sent_batches_dir", DEFAULT_SENT_BATCHES_DIR.name) / f"{batch_id}.json"
        ).resolve()
    else:
        batch_path = (
            config_dir / storage_config.get("last_sent_batch_file", DEFAULT_LAST_SENT_BATCH_PATH.name)
        ).resolve()
    return load_json(batch_path)


def save_selected_articles(
    config: dict[str, Any],
    selection_numbers: list[int],
    *,
    batch_id: str | None = None,
    notes_by_number: dict[int, str] | None = None,
) -> list[Path]:
    storage_config = config.get("storage", {})
    articles_dir = (
        Path(config.get("_config_dir", "."))
        / storage_config.get("saved_articles_dir", DEFAULT_SAVED_ARTICLES_DIR.name)
    ).resolve()
    library_path = articles_dir / "library.json"

    batch = load_batch_payload(config, batch_id=batch_id)
    topics = batch.get("topics", [])
    if not topics:
        raise WatcherError("No topics found in the last sent batch.")

    selected_records: list[dict[str, Any]] = []
    for number in selection_numbers:
        match = next((item for item in topics if int(item["number"]) == number), None)
        if match is None:
            raise WatcherError(f"Selection number {number} was not found in the last sent batch.")
        selected_records.append(match)

    articles_dir.mkdir(parents=True, exist_ok=True)
    library = load_json(library_path, default=[])
    normalized_library: dict[str, dict[str, Any]] = {}
    for item in library:
        normalized_item = enrich_record_metadata(item, config=config, existing=item)
        normalized_library[record_unique_key(normalized_item)] = normalized_item

    saved_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    saved_paths: list[Path] = []
    notes_by_number = notes_by_number or {}

    for record in selected_records:
        source_id = str(record.get("source_id") or "linux_do")
        existing_entry = normalized_library.get(record_unique_key(record), {})
        enriched_record = enrich_record_metadata(
            record,
            config=config,
            existing=existing_entry,
            note_override=notes_by_number.get(int(record["number"])),
        )
        category, category_label = classify_topic_record(record)
        created_text = str(enriched_record.get("created_at_display", "unknown")).replace(":", "-").replace(" ", "_")
        slug = slugify_filename(str(enriched_record["title"]))
        filename = f"{created_text}__{source_id}-{enriched_record['topic_id']}__{slug}.md"
        category_dir = articles_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        article_path = category_dir / filename
        saved_paths.append(article_path)
        normalized_library[record_unique_key(enriched_record)] = {
            **enriched_record,
            "category": category,
            "category_label": category_label,
            "saved_at": str(existing_entry.get("saved_at") or saved_at),
            "relative_path": str(article_path.relative_to(articles_dir)),
        }

    update_saved_indexes(articles_dir, library_path, list(normalized_library.values()))
    return saved_paths


def refresh_saved_library(config: dict[str, Any]) -> None:
    articles_dir = storage_path(config, "saved_articles_dir", DEFAULT_SAVED_ARTICLES_DIR.name)
    library_path = articles_dir / "library.json"
    library = load_json(library_path, default=[])
    if not library:
        return
    normalized_library = [
        enrich_record_metadata(item, config=config, existing=item)
        for item in library
    ]
    update_saved_indexes(articles_dir, library_path, normalized_library)


def decode_header_value(value: str) -> str:
    parts: list[str] = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            try:
                parts.append(chunk.decode(encoding or "utf-8", "ignore"))
            except LookupError:
                parts.append(chunk.decode("utf-8", "ignore"))
        else:
            parts.append(chunk)
    return "".join(parts)


def extract_text_body(message: email.message.Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, "ignore")
            except LookupError:
                decoded = payload.decode("utf-8", "ignore")
            if content_type == "text/plain":
                return decoded
            if content_type == "text/html":
                return sanitize_text(decoded)
        return ""

    payload = message.get_payload(decode=True)
    if payload is None:
        return ""
    charset = message.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, "ignore")
    except LookupError:
        return payload.decode("utf-8", "ignore")


def extract_reply_command_lines(body_text: str) -> list[str]:
    normalized = body_text.replace("\r\n", "\n").replace("\r", "\n")
    collected_lines: list[str] = []
    for line in normalized.split("\n"):
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            if collected_lines:
                break
            continue
        if stripped.startswith(">"):
            break
        if lower.startswith("on ") and "wrote:" in lower:
            break
        if lower.startswith("from:") or lower.startswith("subject:"):
            break
        if lower.startswith("发件人") or lower.startswith("主题"):
            break
        collected_lines.append(stripped)
        if len(collected_lines) >= 10:
            break
    return collected_lines


def extract_reply_numbers(body_text: str) -> list[int]:
    number_tokens = re.findall(r"\b\d+\b", "\n".join(extract_reply_command_lines(body_text)))
    numbers = [int(token) for token in number_tokens]
    deduped: list[int] = []
    seen: set[int] = set()
    for number in numbers:
        if number not in seen:
            seen.add(number)
            deduped.append(number)
    return deduped


def parse_reply_commands(body_text: str) -> list[ReplyCommand]:
    commands: list[ReplyCommand] = []
    for line in extract_reply_command_lines(body_text):
        note_match = re.match(r"^(\d+)\s*note\s*[:：]\s*(.+)$", line, flags=re.IGNORECASE)
        if note_match:
            commands.append(
                ReplyCommand(
                    kind="note",
                    numbers=[int(note_match.group(1))],
                    value=note_match.group(2).strip(),
                    raw=line,
                )
            )
            continue

        if re.fullmatch(r"\d+(?:[\s,，]+\d+)*", line):
            commands.append(
                ReplyCommand(kind="save", numbers=parse_selection_numbers(line), raw=line)
            )
            continue

        if re.fullmatch(r"(?:\d+[+-])(?:[\s,，]+\d+[+-])*", line):
            for token in re.split(r"[\s,，]+", line):
                if not token:
                    continue
                commands.append(
                    ReplyCommand(
                        kind="like" if token.endswith("+") else "dislike",
                        numbers=[int(token[:-1])],
                        raw=token,
                    )
                )
    return commands


def load_batch_records_by_number(
    config: dict[str, Any],
    *,
    batch_id: str | None = None,
) -> dict[int, dict[str, Any]]:
    payload = load_batch_payload(config, batch_id=batch_id)
    topics = list(payload.get("topics", []))
    if not topics:
        raise WatcherError("No topics found in the selected batch.")
    return {int(item["number"]): item for item in topics}


def append_reply_log(path: Path, data: dict[str, Any]) -> None:
    append_jsonl(path, data)


def process_email_replies(config: dict[str, Any]) -> list[dict[str, Any]]:
    email_config = config.get("push", {}).get("email", {})
    if not email_config.get("enabled"):
        return []

    reply_config = email_config.get("reply_processing", {})
    if not reply_config.get("enabled", True):
        return []

    config_dir = Path(config.get("_config_dir", "."))
    storage_config = config.get("storage", {})
    reply_state_path = (
        config_dir / storage_config.get("reply_state_file", DEFAULT_REPLY_STATE_PATH.name)
    ).resolve()
    reply_log_path = (
        config_dir / storage_config.get("reply_log_file", DEFAULT_REPLY_LOG_PATH.name)
    ).resolve()
    reply_state = load_json(reply_state_path, default={"processed_uids": []})
    processed_uids = set(str(item) for item in reply_state.get("processed_uids", []))

    username = str(email_config["username"])
    password = str(email_config["password"])
    imap_host = str(email_config.get("imap_host") or "").strip()
    if not imap_host:
        return []

    mailbox = str(reply_config.get("mailbox", "INBOX"))
    allowed_senders = {
        str(item).lower()
        for item in reply_config.get("allowed_senders", email_config.get("to_addrs", []))
    }
    subject_keyword = str(reply_config.get("subject_keyword", DEFAULT_SUBJECT_PREFIX)).lower()
    max_messages = int(reply_config.get("max_messages", 50))

    actions: list[dict[str, Any]] = []

    with imaplib.IMAP4_SSL(imap_host, int(email_config.get("imap_port", 993))) as imap:
        imap.login(username, password)
        status, _ = imap.select(mailbox, readonly=False)
        if status != "OK":
            raise WatcherError(f"Could not open IMAP mailbox: {mailbox}")
        status, data = imap.uid("search", None, "ALL")
        uids = (data[0].split() if status == "OK" and data and data[0] else [])[-max_messages:]

        for uid in uids:
            uid_text = uid.decode()
            if uid_text in processed_uids:
                continue

            status, msg_data = imap.uid("fetch", uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw_message = msg_data[0][1]
            message = email.message_from_bytes(raw_message)
            subject = decode_header_value(message.get("Subject", ""))
            sender = parseaddr(decode_header_value(message.get("From", "")))[1].lower()
            body_text = extract_text_body(message)

            should_track = subject_keyword in subject.lower()
            if allowed_senders and sender not in allowed_senders:
                should_track = False
            if not should_track:
                continue

            batch_match = re.search(r"\[batch ([^\]]+)\]", subject, flags=re.IGNORECASE)
            batch_id = batch_match.group(1) if batch_match else None
            commands = parse_reply_commands(body_text)

            action: dict[str, Any] = {
                "processed_at": utc_now_iso(),
                "uid": uid_text,
                "from": sender,
                "subject": subject,
                "batch_id": batch_id,
                "commands": [
                    {
                        "kind": command.kind,
                        "numbers": command.numbers,
                        "value": command.value,
                        "raw": command.raw,
                    }
                    for command in commands
                ],
                "status": "ignored",
            }

            if commands:
                try:
                    batch_records = load_batch_records_by_number(config, batch_id=batch_id)
                    save_numbers: set[int] = set()
                    notes_by_number: dict[int, str] = {}
                    feedback_updates: list[dict[str, Any]] = []

                    for command in commands:
                        if command.kind == "save":
                            save_numbers.update(command.numbers)
                        elif command.kind == "note":
                            number = command.numbers[0]
                            if number not in batch_records:
                                raise WatcherError(f"Selection number {number} was not found in the batch.")
                            save_numbers.add(number)
                            notes_by_number[number] = command.value
                        elif command.kind in {"like", "dislike"}:
                            number = command.numbers[0]
                            if number not in batch_records:
                                raise WatcherError(f"Selection number {number} was not found in the batch.")
                            feedback_updates.append(
                                {
                                    "number": number,
                                    **apply_feedback_command(
                                        config,
                                        batch_records[number],
                                        direction=command.kind,
                                    ),
                                }
                            )

                    saved_paths: list[Path] = []
                    if save_numbers:
                        saved_paths = save_selected_articles(
                            config,
                            sorted(save_numbers),
                            batch_id=batch_id,
                            notes_by_number=notes_by_number,
                        )
                    elif feedback_updates:
                        refresh_saved_library(config)

                    action["status"] = "processed"
                    action["saved_paths"] = [str(path) for path in saved_paths]
                    action["feedback_updates"] = feedback_updates
                    action["saved_numbers"] = sorted(save_numbers)
                except WatcherError as exc:
                    action["status"] = "error"
                    action["error"] = str(exc)
            else:
                action["note"] = "No supported commands found in reply body."

            processed_uids.add(uid_text)
            append_reply_log(reply_log_path, action)
            actions.append(action)

        imap.logout()

    save_json(
        reply_state_path,
        {"processed_uids": sorted(processed_uids, key=lambda item: int(item))[-500:]},
    )
    return actions


def send_email(email_config: dict[str, Any], subject: str, body: str) -> None:
    host = str(email_config["smtp_host"])
    port = int(email_config.get("smtp_port", 465))
    username = str(email_config["username"])
    password = str(email_config["password"])
    from_addr = str(email_config.get("from_addr") or username)
    to_addrs = list(email_config["to_addrs"])
    use_ssl = bool(email_config.get("use_ssl", True))
    starttls = bool(email_config.get("starttls", False))
    timeout = int(email_config.get("timeout_sec", 20))

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = ", ".join(to_addrs)
    message.set_content(body)

    context = ssl.create_default_context()

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as server:
            server.login(username, password)
            server.send_message(message)
        save_email_copy_to_sent(email_config, message)
        return

    with smtplib.SMTP(host, port, timeout=timeout) as server:
        server.ehlo()
        if starttls:
            server.starttls(context=context)
            server.ehlo()
        server.login(username, password)
        server.send_message(message)
    save_email_copy_to_sent(email_config, message)


def save_email_copy_to_sent(email_config: dict[str, Any], message: EmailMessage) -> None:
    if not email_config.get("save_to_sent", False):
        return

    imap_host = str(email_config.get("imap_host") or "").strip()
    if not imap_host:
        return

    imap_port = int(email_config.get("imap_port", 993))
    imap_sent_mailbox = str(email_config.get("imap_sent_mailbox", "Sent Messages"))
    username = str(email_config["username"])
    password = str(email_config["password"])

    try:
        with imaplib.IMAP4_SSL(imap_host, imap_port) as imap:
            imap.login(username, password)
            status, _ = imap.append(
                imap_sent_mailbox,
                "\\Seen",
                imaplib.Time2Internaldate(time.time()),
                message.as_bytes(),
            )
            imap.logout()
        if status != "OK":
            raise WatcherError("IMAP append to Sent Messages failed")
    except imaplib.IMAP4.error as exc:
        raise WatcherError(f"IMAP save-to-sent failed: {exc}") from exc


def send_wxpusher(wxpusher_config: dict[str, Any], title: str, body: str) -> None:
    payload = {
        "appToken": str(wxpusher_config["app_token"]),
        "content": body,
        "summary": title[:100],
        "contentType": int(wxpusher_config.get("content_type", 3)),
        "uids": list(wxpusher_config["uids"]),
    }
    request = Request(
        WXPUSHER_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=int(wxpusher_config.get("timeout_sec", 20))) as response:
            body_text = response.read().decode("utf-8")
    except HTTPError as exc:
        raise WatcherError(f"WxPusher HTTP {exc.code}") from exc
    except URLError as exc:
        raise WatcherError(f"WxPusher network error: {exc.reason}") from exc

    try:
        result = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise WatcherError("WxPusher response is not valid JSON") from exc

    if not result.get("success"):
        message = result.get("msg") or result.get("message") or "unknown error"
        raise WatcherError(f"WxPusher rejected the request: {message}")


def push_topics(
    config: dict[str, Any],
    topics: list[Topic],
    *,
    batch_id: str,
    dry_run: bool,
) -> tuple[str, str]:
    ordered_topics = order_topics_for_sections(topics, config)
    subject, plain_body = build_plaintext_message(ordered_topics, batch_id=batch_id, config=config)
    wx_title, markdown_body = build_markdown_message(ordered_topics, batch_id=batch_id, config=config)

    if dry_run:
        print(plain_body)
        return subject, plain_body

    push_config = config["push"]
    enabled_channels: list[str] = []

    email_config = push_config.get("email", {})
    if email_config.get("enabled"):
        enabled_channels.append("email")
        send_email(email_config, subject, plain_body)

    wxpusher_config = push_config.get("wxpusher", {})
    if wxpusher_config.get("enabled"):
        enabled_channels.append("wxpusher")
        send_wxpusher(wxpusher_config, wx_title, markdown_body)

    if not enabled_channels:
        raise WatcherError("No push channel is enabled in config.json")
    return subject, plain_body


def prune_seen_ids(seen_ids: list[str], *, limit: int) -> list[str]:
    deduped: list[str] = []
    seen_set: set[str] = set()
    for item in reversed(seen_ids):
        if item in seen_set:
            continue
        seen_set.add(item)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    deduped.reverse()
    return deduped


def compatible_topic_ids(seen_record_ids: list[str], *, limit: int) -> list[str]:
    legacy_ids: list[str] = []
    for item in seen_record_ids:
        legacy_ids.append(item.split(":", 1)[1] if ":" in item else item)
    return prune_seen_ids(legacy_ids, limit=limit)


def load_seen_record_ids(state: dict[str, Any]) -> set[str]:
    seen_record_ids = {str(item) for item in state.get("seen_record_ids", [])}
    if seen_record_ids:
        return seen_record_ids
    return {f"linux_do:{item}" for item in state.get("seen_topic_ids", [])}


def build_state_snapshot(
    *,
    previous_state: dict[str, Any],
    seen_record_ids: list[str],
    seen_canonical_keys: list[str],
    checked_at: str,
    status: str,
    fetched_count: int,
    matched_count: int,
    new_count: int,
    sent_count: int,
    remaining_count: int,
    source_errors: list[dict[str, Any]],
    max_seen_ids: int,
    error: str | None = None,
    bootstrapped: bool | None = None,
    bootstrapped_at: str | None = None,
) -> dict[str, Any]:
    snapshot = dict(previous_state)
    snapshot["bootstrapped"] = (
        previous_state.get("bootstrapped", False) if bootstrapped is None else bootstrapped
    )
    if bootstrapped_at is not None:
        snapshot["bootstrapped_at"] = bootstrapped_at
    snapshot["seen_record_ids"] = prune_seen_ids(seen_record_ids, limit=max_seen_ids)
    snapshot["seen_canonical_keys"] = prune_seen_ids(seen_canonical_keys, limit=max_seen_ids)
    snapshot["seen_topic_ids"] = compatible_topic_ids(snapshot["seen_record_ids"], limit=max_seen_ids)
    snapshot["last_checked_at"] = checked_at
    snapshot["last_success_at"] = checked_at
    snapshot["last_status"] = status
    snapshot["last_fetch_count"] = fetched_count
    snapshot["last_match_count"] = matched_count
    snapshot["last_new_count"] = new_count
    snapshot["last_sent_count"] = sent_count
    snapshot["last_remaining_count"] = remaining_count
    snapshot["last_source_errors"] = source_errors
    snapshot["last_error"] = error
    if sent_count:
        snapshot["last_sent_at"] = checked_at
    return snapshot


def persist_run_state(
    *,
    state_path: Path,
    run_log_path: Path,
    state: dict[str, Any],
    checked_at: str,
    status: str,
    fetched_count: int,
    matched_count: int,
    new_count: int,
    sent_count: int,
    remaining_count: int,
    source_errors: list[dict[str, Any]],
    dry_run: bool,
    error: str | None = None,
    note: str | None = None,
) -> None:
    if dry_run:
        return

    save_json(state_path, state)
    append_jsonl(
        run_log_path,
        {
            "checked_at": checked_at,
            "status": status,
            "fetched_count": fetched_count,
            "matched_count": matched_count,
            "new_count": new_count,
            "sent_count": sent_count,
            "remaining_count": remaining_count,
            "dry_run": False,
            "error": error,
            "note": note,
            "source_errors": source_errors,
        },
    )


def select_new_topics(
    topics: list[Topic],
    seen_record_ids: set[str],
    seen_canonical_keys: set[str],
) -> list[Topic]:
    new_topics: list[Topic] = []
    for topic in topics:
        if topic.canonical_key in seen_canonical_keys:
            continue
        if any(record_id in seen_record_ids for record_id in merged_source_record_ids(topic)):
            continue
        new_topics.append(topic)
    return new_topics


def extend_seen_state(
    seen_record_ids: list[str],
    seen_canonical_keys: list[str],
    topics: list[Topic],
) -> tuple[list[str], list[str]]:
    new_record_ids = list(seen_record_ids)
    new_canonical_keys = list(seen_canonical_keys)
    for topic in topics:
        new_record_ids.extend(merged_source_record_ids(topic))
        new_canonical_keys.append(topic.canonical_key)
    return new_record_ids, new_canonical_keys


def run() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_json(config_path)
    config["_config_dir"] = str(config_path.parent)

    storage_config = config.get("storage", {})
    state_path = (
        config_path.parent / storage_config.get("state_file", DEFAULT_STATE_PATH.name)
    ).resolve()
    run_log_path = (
        config_path.parent / storage_config.get("run_log_file", DEFAULT_RUN_LOG_PATH.name)
    ).resolve()
    batch_path = (
        config_path.parent
        / storage_config.get("last_sent_batch_file", DEFAULT_LAST_SENT_BATCH_PATH.name)
    ).resolve()
    sent_batches_dir = (
        config_path.parent
        / storage_config.get("sent_batches_dir", DEFAULT_SENT_BATCHES_DIR.name)
    ).resolve()
    max_seen_ids = int(storage_config.get("max_seen_ids", 500))
    checked_at = utc_now_iso()

    if args.process_replies_only:
        actions = process_email_replies(config)
        if not actions:
            print("No new reply emails to process.")
            return 0
        print(f"Processed {len(actions)} reply email(s).")
        for action in actions:
            print(f"{action['status']}: {action['subject']}")
        return 0

    if args.save_numbers:
        numbers = parse_selection_numbers(args.save_numbers)
        saved_paths = save_selected_articles(config, numbers)
        print("Saved selected articles:")
        for path in saved_paths:
            print(path)
        return 0

    default_state = {
        "bootstrapped": False,
        "seen_topic_ids": [],
        "seen_record_ids": [],
        "seen_canonical_keys": [],
    }
    if args.reset_state:
        if not args.dry_run and state_path.exists():
            state_path.unlink()
        state = dict(default_state)
    else:
        state = load_json(state_path, default=default_state)

    seen_record_ids = load_seen_record_ids(state)
    seen_canonical_keys = {str(item) for item in state.get("seen_canonical_keys", [])}

    fetched_count = 0
    matched_count = 0
    new_count = 0
    sent_count = 0
    remaining_count = 0
    source_errors: list[dict[str, Any]] = []

    try:
        topics, source_errors = fetch_all_topics(config)
        fetched_count = len(topics)
        matched_topics = [topic for topic in topics if topic_matches(topic, config)]
        merged_matched_topics = merge_topics(matched_topics, config)
        apply_feedback_scores_to_topics(merged_matched_topics, config)
        merged_matched_topics.sort(key=lambda item: (item.preference_score, item.created_at_ts), reverse=True)
        matched_count = len(merged_matched_topics)

        if not merged_matched_topics:
            updated_state = build_state_snapshot(
                previous_state=state,
                seen_record_ids=list(seen_record_ids),
                seen_canonical_keys=list(seen_canonical_keys),
                checked_at=checked_at,
                status="no_match",
                fetched_count=fetched_count,
                matched_count=0,
                new_count=0,
                sent_count=0,
                remaining_count=0,
                source_errors=source_errors,
                max_seen_ids=max_seen_ids,
            )
            persist_run_state(
                state_path=state_path,
                run_log_path=run_log_path,
                state=updated_state,
                checked_at=checked_at,
                status="no_match",
                fetched_count=fetched_count,
                matched_count=0,
                new_count=0,
                sent_count=0,
                remaining_count=0,
                source_errors=source_errors,
                dry_run=args.dry_run,
                note="No matched topics found.",
            )
            print("No matched topics found.")
            return 0

        if not state.get("bootstrapped") and not args.first_run_send:
            bootstrapped_record_ids, bootstrapped_canonical_keys = extend_seen_state(
                list(seen_record_ids),
                list(seen_canonical_keys),
                merged_matched_topics,
            )
            updated_state = build_state_snapshot(
                previous_state=state,
                seen_record_ids=bootstrapped_record_ids,
                seen_canonical_keys=bootstrapped_canonical_keys,
                checked_at=checked_at,
                status="bootstrapped",
                fetched_count=fetched_count,
                matched_count=matched_count,
                new_count=matched_count,
                sent_count=0,
                remaining_count=0,
                source_errors=source_errors,
                max_seen_ids=max_seen_ids,
                bootstrapped=True,
                bootstrapped_at=checked_at,
            )
            persist_run_state(
                state_path=state_path,
                run_log_path=run_log_path,
                state=updated_state,
                checked_at=checked_at,
                status="bootstrapped",
                fetched_count=fetched_count,
                matched_count=matched_count,
                new_count=matched_count,
                sent_count=0,
                remaining_count=0,
                source_errors=source_errors,
                dry_run=args.dry_run,
                note="Bootstrapped current matches without sending.",
            )
            if args.dry_run:
                print("First run bootstrap preview:")
                print(f"Would mark {matched_count} matched topics as seen without sending.")
                return 0
            print(
                "Bootstrap complete. Current matched topics were marked as seen; "
                "future runs will only push newly matched topics."
            )
            return 0

        new_topics = select_new_topics(merged_matched_topics, seen_record_ids, seen_canonical_keys)
        new_topics.sort(key=lambda item: (item.preference_score, item.created_at_ts), reverse=True)
        new_count = len(new_topics)

        if not new_topics:
            updated_state = build_state_snapshot(
                previous_state=state,
                seen_record_ids=list(seen_record_ids),
                seen_canonical_keys=list(seen_canonical_keys),
                checked_at=checked_at,
                status="no_new",
                fetched_count=fetched_count,
                matched_count=matched_count,
                new_count=0,
                sent_count=0,
                remaining_count=0,
                source_errors=source_errors,
                max_seen_ids=max_seen_ids,
            )
            persist_run_state(
                state_path=state_path,
                run_log_path=run_log_path,
                state=updated_state,
                checked_at=checked_at,
                status="no_new",
                fetched_count=fetched_count,
                matched_count=matched_count,
                new_count=0,
                sent_count=0,
                remaining_count=0,
                source_errors=source_errors,
                dry_run=args.dry_run,
                note="No new matched topics since the last successful run.",
            )
            print("No new matched topics since the last successful run.")
            return 0

        notify_limit = int(config.get("filter", {}).get("max_notify_items", 10))
        topics_to_send = new_topics[:notify_limit]
        topics_to_send = order_topics_for_sections(topics_to_send, config)
        sent_count = len(topics_to_send)
        remaining_count = max(0, new_count - sent_count)
        batch_id = make_batch_id(checked_at)

        subject, _ = push_topics(config, topics_to_send, batch_id=batch_id, dry_run=args.dry_run)

        if args.dry_run:
            return 0

        save_last_sent_batch(
            batch_path,
            topics_to_send,
            sent_at=checked_at,
            batch_id=batch_id,
            subject=subject,
            config=config,
        )
        save_batch_history(
            sent_batches_dir,
            topics_to_send,
            sent_at=checked_at,
            batch_id=batch_id,
            subject=subject,
            config=config,
        )

        updated_record_ids, updated_canonical_keys = extend_seen_state(
            list(seen_record_ids),
            list(seen_canonical_keys),
            topics_to_send,
        )
        updated_state = build_state_snapshot(
            previous_state=state,
            seen_record_ids=updated_record_ids,
            seen_canonical_keys=updated_canonical_keys,
            checked_at=checked_at,
            status="sent",
            fetched_count=fetched_count,
            matched_count=matched_count,
            new_count=new_count,
            sent_count=sent_count,
            remaining_count=remaining_count,
            source_errors=source_errors,
            max_seen_ids=max_seen_ids,
            bootstrapped=True,
        )
        persist_run_state(
            state_path=state_path,
            run_log_path=run_log_path,
            state=updated_state,
            checked_at=checked_at,
            status="sent",
            fetched_count=fetched_count,
            matched_count=matched_count,
            new_count=new_count,
            sent_count=sent_count,
            remaining_count=remaining_count,
            source_errors=source_errors,
            dry_run=False,
        )
        if remaining_count:
            print(
                f"Sent {sent_count} topic(s); "
                f"{remaining_count} matched topic(s) remain for the next run."
            )
        else:
            print(f"Sent {sent_count} topic(s).")
        return 0
    except WatcherError as exc:
        if not args.dry_run:
            error_state = dict(state)
            error_state["last_checked_at"] = checked_at
            error_state["last_status"] = "error"
            error_state["last_fetch_count"] = fetched_count
            error_state["last_match_count"] = matched_count
            error_state["last_new_count"] = new_count
            error_state["last_sent_count"] = sent_count
            error_state["last_remaining_count"] = remaining_count
            error_state["last_source_errors"] = source_errors
            error_state["last_error"] = str(exc)
            save_json(state_path, error_state)
            append_jsonl(
                run_log_path,
                {
                    "checked_at": checked_at,
                    "status": "error",
                    "fetched_count": fetched_count,
                    "matched_count": matched_count,
                    "new_count": new_count,
                    "sent_count": sent_count,
                    "remaining_count": remaining_count,
                    "dry_run": False,
                    "error": str(exc),
                    "note": None,
                    "source_errors": source_errors,
                },
            )
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except WatcherError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

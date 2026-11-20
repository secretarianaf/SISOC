"""Capture public CSS, script, font, and image assets for INS-A comparisons."""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ALLOWED_HOSTS = frozenset(
    {
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "cdn.datatables.net",
    }
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
MAX_ASSET_BYTES = 64 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class AssetURLRejected(ValueError):
    """An external asset URL is outside the approved anonymous CDN allowlist."""


class CacheConflictError(RuntimeError):
    """An existing cache file or manifest cannot safely be reused."""


@dataclass(frozen=True)
class AssetReference:
    """A template URL reference and its original integrity metadata."""

    url: str
    source: str
    integrity: str | None = None


def validate_asset_url(url: str) -> str:
    """Return a normalized HTTPS URL only for approved CDN hosts."""
    candidate = f"https:{url}" if url.startswith("//") else url
    parsed = urlsplit(candidate)
    try:
        port = parsed.port
    except ValueError as exc:
        raise AssetURLRejected(f"invalid port in asset URL: {url}") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        raise AssetURLRejected(f"asset URL is not approved: {url}")
    return candidate


class SafeRedirectHandler(HTTPRedirectHandler):
    """Reject redirects outside the public asset allowlist before following."""

    # urllib requires the inherited redirect_request signature.
    # pylint: disable=too-many-arguments
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_asset_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _TemplateAssetParser(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.assets: list[AssetReference] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        tag = tag.lower()
        if tag == "link" and "stylesheet" in (values.get("rel") or "").lower().split():
            url = values.get("href")
        elif tag == "script":
            url = values.get("src")
        else:
            return
        if not url:
            return
        parsed = urlsplit(url)
        if not parsed.scheme and not parsed.netloc:
            return
        normalized = validate_asset_url(url)
        self.assets.append(
            AssetReference(
                url=normalized,
                source=self.source,
                integrity=values.get("integrity"),
            )
        )


_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_CSS_IMPORT = re.compile(
    r"@import\s+(?:url\(\s*)?(['\"]?)([^'\"\s)]+)\1\s*\)?",
    re.IGNORECASE,
)
_CSS_URL = re.compile(
    r"url\(\s*(?:(['\"])(.*?)\1|([^)]*?))\s*\)", re.IGNORECASE | re.DOTALL
)


def discover_css_assets(css_bytes: bytes, source_url: str) -> list[AssetReference]:
    """Resolve CSS imports and url() references against an approved CSS URL."""
    source_url = validate_asset_url(source_url)
    css = _CSS_COMMENT.sub("", css_bytes.decode("utf-8", errors="replace"))
    imports = [match.group(2) for match in _CSS_IMPORT.finditer(css)]
    remaining = _CSS_IMPORT.sub("", css)
    raw_urls = [
        match.group(2) if match.group(1) else match.group(3)
        for match in _CSS_URL.finditer(remaining)
    ]
    assets: list[AssetReference] = []
    seen: set[str] = set()
    for raw_url in [*imports, *raw_urls]:
        raw_url = raw_url.strip().strip("\"'")
        if not raw_url or raw_url.startswith(("#", "data:", "blob:")):
            continue
        absolute_url = validate_asset_url(urljoin(source_url, raw_url))
        if absolute_url not in seen:
            seen.add(absolute_url)
            assets.append(AssetReference(absolute_url, f"css:{source_url}"))
    return assets


def discover_template_assets(template_paths: list[Path]) -> list[AssetReference]:
    """Discover allowed stylesheet/script URLs from the named HTML templates."""
    assets: list[AssetReference] = []
    for path in template_paths:
        parser = _TemplateAssetParser(str(path))
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        assets.extend(parser.assets)
    return assets


def anonymous_opener():
    """Build a urllib opener that ignores proxy environment and checks redirects."""
    return build_opener(ProxyHandler({}), SafeRedirectHandler())


class PublicAssetCache:
    """Download and verify public assets under a caller-provided scratch root."""

    def __init__(self, output_dir: Path, opener=None):
        self.output_dir = Path(output_dir)
        self.opener = opener or anonymous_opener()

    def capture(self, template_paths: list[Path]) -> dict:
        output_dir = self.output_dir.resolve()
        if output_dir == PROJECT_ROOT or PROJECT_ROOT in output_dir.parents:
            raise ValueError("asset cache output must be outside the repository")
        manifest_path = output_dir / "manifest.json"
        assets_dir = output_dir / "assets"
        existing = self._read_existing_manifest(manifest_path)
        errors: list[dict[str, str]] = []
        assets_dir.mkdir(parents=True, exist_ok=True)
        resolved_assets_dir = assets_dir.resolve()
        if (
            resolved_assets_dir == PROJECT_ROOT
            or PROJECT_ROOT in resolved_assets_dir.parents
        ):
            raise ValueError("asset cache files must remain outside the repository")
        work: deque[AssetReference] = deque()
        try:
            work.extend(discover_template_assets(template_paths))
        except Exception as exc:  # Preserve a machine-readable partial outcome.
            errors.append({"url": "", "error": f"{type(exc).__name__}: {exc}"})

        records, refs_by_url = self._capture_queue(work, assets_dir, existing, errors)
        manifest = self._build_manifest(template_paths, records, refs_by_url, errors)
        self._write_manifest(manifest_path, manifest)
        return manifest

    def _capture_queue(
        self,
        work: deque[AssetReference],
        assets_dir: Path,
        existing: dict[str, dict],
        errors: list[dict[str, str]],
    ) -> tuple[dict[str, dict], dict[str, list[AssetReference]]]:
        records: dict[str, dict] = {}
        refs_by_url: dict[str, list[AssetReference]] = {}
        visited: set[str] = set()
        while work:
            ref = work.popleft()
            url = validate_asset_url(ref.url)
            refs = refs_by_url.setdefault(url, [])
            if ref not in refs:
                refs.append(ref)
            if url in visited:
                continue
            visited.add(url)
            try:
                record, body = self._capture_reference(url, assets_dir, existing)
                records[url] = record
                if self._is_css(url, record.get("content_type", "")):
                    work.extend(discover_css_assets(body, url))
            except Exception as exc:
                errors.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
        return records, refs_by_url

    def _capture_reference(
        self, url: str, assets_dir: Path, existing: dict[str, dict]
    ) -> tuple[dict, bytes]:
        if url in existing:
            record = dict(existing[url])
            body = self._read_cached_asset(assets_dir, record)
            return record, body

        body, content_type = self._download(url)
        digest = hashlib.sha256(body).hexdigest()
        filename = self._filename_for_url(url)
        self._store_bytes(assets_dir / filename, body, digest)
        record = {
            "url": url,
            "filename": filename,
            "sha256": digest,
            "size": len(body),
            "content_type": content_type,
        }
        return record, body

    @staticmethod
    def _build_manifest(
        template_paths: list[Path],
        records: dict[str, dict],
        refs_by_url: dict[str, list[AssetReference]],
        errors: list[dict[str, str]],
    ) -> dict:
        output_records = []
        for url, record in records.items():
            refs = refs_by_url.get(url, [])
            output_records.append(
                {
                    **record,
                    "source": list(dict.fromkeys(ref.source for ref in refs)),
                    "integrity": list(
                        dict.fromkeys(ref.integrity for ref in refs if ref.integrity)
                    ),
                }
            )
        return {
            "schema_version": 2,
            "status": "complete" if not errors else "partial",
            "user_agent": USER_AGENT,
            "source_templates": [str(Path(path).resolve()) for path in template_paths],
            "assets": output_records,
            "errors": errors,
        }

    def _download(self, url: str) -> tuple[bytes, str]:
        url = validate_asset_url(url)
        request = Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            method="GET",
        )
        response = self.opener.open(request, timeout=20)
        try:
            body = response.read(MAX_ASSET_BYTES + 1)
            if len(body) > MAX_ASSET_BYTES:
                raise ValueError(f"asset exceeds {MAX_ASSET_BYTES} bytes")
            headers = response.headers
            content_length = headers.get("Content-Length")
            if content_length is not None:
                expected_size = int(content_length)
                if expected_size < 0 or len(body) != expected_size:
                    raise ValueError(
                        "Incomplete asset response: Content-Length mismatch"
                    )
            content_type = headers.get("Content-Type", "application/octet-stream")
            return body, content_type
        finally:
            response.close()

    @staticmethod
    def _is_css(url: str, content_type: str) -> bool:
        return "text/css" in content_type.lower() or urlsplit(
            url
        ).path.lower().endswith(".css")

    @staticmethod
    def _filename_for_url(url: str) -> str:
        path = urlsplit(url).path
        suffix = Path(path).suffix
        if not re.fullmatch(r"\.[A-Za-z0-9]{1,10}", suffix):
            suffix = ".bin"
        return hashlib.sha256(url.encode("utf-8")).hexdigest() + suffix.lower()

    @staticmethod
    def _read_cached_asset(assets_dir: Path, record: dict) -> bytes:
        filename = record.get("filename", "")
        if Path(filename).name != filename:
            raise CacheConflictError("manifest asset filename escapes cache directory")
        path = assets_dir / filename
        if not path.is_file():
            raise CacheConflictError(f"cached asset is missing: {filename}")
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != record.get("sha256") or len(body) != record.get("size"):
            raise CacheConflictError(
                f"cached asset failed hash/size verification: {filename}"
            )
        return body

    @staticmethod
    def _store_bytes(path: Path, body: bytes, digest: str) -> None:
        if path.exists():
            current = path.read_bytes()
            if hashlib.sha256(current).hexdigest() != digest:
                raise CacheConflictError(
                    f"refusing to overwrite conflicting asset: {path.name}"
                )
            return
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary.write(body)
            temporary_path = Path(temporary.name)
        try:
            if path.exists():
                current = path.read_bytes()
                if hashlib.sha256(current).hexdigest() != digest:
                    raise CacheConflictError(
                        f"refusing to overwrite conflicting asset: {path.name}"
                    )
            else:
                os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _read_existing_manifest(path: Path) -> dict[str, dict]:
        if not path.exists():
            return {}
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CacheConflictError(f"existing manifest is unreadable: {exc}") from exc
        if manifest.get("schema_version") != 2 or not isinstance(
            manifest.get("assets"), list
        ):
            raise CacheConflictError("existing manifest has an unsupported format")
        result = {}
        for record in manifest["assets"]:
            url = validate_asset_url(record.get("url", ""))
            if url in result:
                raise CacheConflictError(f"duplicate URL in existing manifest: {url}")
            result[url] = record
        return result

    @staticmethod
    def _write_manifest(path: Path, manifest: dict) -> None:
        body = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary.write(body)
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="External scratch directory; no cache is written into the repository.",
    )
    args = parser.parse_args(argv)
    templates = [
        PROJECT_ROOT / "src/backends/kernel/templates/includes/base.html",
        PROJECT_ROOT / "src/backends/kernel/templates/scripts/mainscripts.html",
    ]
    manifest = PublicAssetCache(args.output).capture(templates)
    print(
        f"asset_cache={manifest['status']} assets={len(manifest['assets'])} "
        f"errors={len(manifest['errors'])} output={args.output.resolve()}"
    )
    return 0 if manifest["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())

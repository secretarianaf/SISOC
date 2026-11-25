"""Public seam tests for the isolated INS-A public asset cache."""

import tempfile
import unittest
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock, patch

from insumos_visual_assets import (
    SafeRedirectHandler,
    discover_template_assets,
    discover_css_assets,
    PublicAssetCache,
    AssetURLRejected,
    CacheConflictError,
    anonymous_opener,
    validate_asset_url,
    USER_AGENT,
)


class _Response:
    def __init__(self, body, content_type):
        self.body = body
        self.headers = {"Content-Type": content_type}

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]

    def close(self):
        pass


def _response(body, content_type):
    return _Response(body, content_type)


class TemplateAssetDiscoveryTests(unittest.TestCase):
    def test_cache_before_transfer_verification_is_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.json"
            original = b'{"schema_version": 1, "status": "complete", "assets": []}'
            manifest_path.write_bytes(original)
            opener = Mock()
            with self.assertRaises(CacheConflictError):
                PublicAssetCache(root, opener=opener).capture([])
            self.assertEqual(manifest_path.read_bytes(), original)
            opener.open.assert_not_called()

    def test_content_length_must_be_received_before_an_asset_is_cached(self):
        for length, expected in (("4", "complete"), ("20", "partial")):
            with (
                self.subTest(length=length),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                template = root / "base.html"
                template.write_text(
                    '<script src="https://cdn.jsdelivr.net/npm/example.js"></script>',
                    encoding="utf-8",
                )
                response = _Response(b"data", "application/javascript")
                response.headers["Content-Length"] = length
                opener = Mock()
                opener.open.return_value = response
                manifest = PublicAssetCache(root / "cache", opener=opener).capture(
                    [template]
                )
                self.assertEqual(manifest["status"], expected)
                if expected == "partial":
                    self.assertEqual(manifest["assets"], [])
                    self.assertIn("Content-Length", manifest["errors"][0]["error"])
                    self.assertEqual(list((root / "cache" / "assets").iterdir()), [])
                else:
                    self.assertEqual(manifest["assets"][0]["size"], 4)

    def test_url_policy_rejects_credentials_ports_and_unapproved_hosts(self):
        for url in (
            "https://user@cdn.jsdelivr.net/a.css",
            "https://cdn.jsdelivr.net:443/a.css",
            "http://cdn.jsdelivr.net/a.css",
            "https://cdn.jsdelivr.net.evil.example/a.css",
        ):
            with self.subTest(url=url), self.assertRaises(AssetURLRejected):
                validate_asset_url(url)
        self.assertEqual(
            validate_asset_url("//cdn.jsdelivr.net/npm/a.css"),
            "https://cdn.jsdelivr.net/npm/a.css",
        )

    def test_anonymous_opener_disables_environment_proxies(self):
        with patch.dict(
            "os.environ",
            {
                "HTTP_PROXY": "http://proxy.invalid:8080",
                "HTTPS_PROXY": "http://proxy.invalid:8080",
                "ALL_PROXY": "http://proxy.invalid:8080",
            },
        ):
            opener = anonymous_opener()
        proxy_handlers = [
            handler
            for handler in opener.handlers
            if handler.__class__.__name__ == "ProxyHandler"
        ]
        self.assertTrue(all(handler.proxies == {} for handler in proxy_handlers))
        self.assertTrue(
            any(isinstance(handler, SafeRedirectHandler) for handler in opener.handlers)
        )

    def test_extracts_external_stylesheets_and_scripts_with_sri_metadata(self):
        html = """<!doctype html>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/a.css"
              integrity="sha256-style" crossorigin="anonymous">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/a.js"
                integrity="sha384-script"></script>
        <a href="/local-page/">not an asset</a>
        <script src="{% static 'custom/js/local.js' %}"></script>
        """
        with tempfile.TemporaryDirectory() as temporary:
            template = Path(temporary) / "base.html"
            template.write_text(html, encoding="utf-8")

            found = discover_template_assets([template])

        self.assertEqual(
            [(item.url, item.source, item.integrity) for item in found],
            [
                (
                    "https://cdn.jsdelivr.net/npm/a.css",
                    str(template),
                    "sha256-style",
                ),
                (
                    "https://cdnjs.cloudflare.com/ajax/libs/a.js",
                    str(template),
                    "sha384-script",
                ),
            ],
        )

    def test_cache_recurses_deduplicates_and_preserves_raw_bytes(self):
        assets = {
            "https://cdn.jsdelivr.net/npm/example/main.css": (
                b"@import 'nested.css'; @font-face { src: url('../font.woff2'); }",
                "text/css",
            ),
            "https://cdn.jsdelivr.net/npm/example/nested.css": (
                b".icon { src: url('https://fonts.gstatic.com/font.woff2'); }",
                "text/css",
            ),
            "https://cdn.jsdelivr.net/npm/font.woff2": (
                b"font-bytes",
                "font/woff2",
            ),
            "https://fonts.gstatic.com/font.woff2": (b"font-bytes-2", "font/woff2"),
            "https://cdnjs.cloudflare.com/ajax/libs/example.js": (
                b"script-bytes",
                "application/javascript",
            ),
        }
        opener = Mock()
        opener.open.side_effect = lambda request, timeout: _response(
            *assets[request.full_url]
        )
        html = """<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/example/main.css"
                           integrity="sha256-original">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/example/main.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/example.js"
                integrity="sha384-original"></script>"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / "base.html"
            template.write_text(html, encoding="utf-8")
            manifest = PublicAssetCache(root / "cache", opener=opener).capture(
                [template]
            )

            self.assertEqual(manifest["status"], "complete", manifest["errors"])
            self.assertEqual(len(manifest["assets"]), len(assets))
            self.assertEqual(opener.open.call_count, len(assets))
            for call in opener.open.call_args_list:
                headers = {
                    name.lower(): value for name, value in call.args[0].header_items()
                }
                self.assertEqual(headers["user-agent"], USER_AGENT)
                self.assertNotIn("cookie", headers)
                self.assertNotIn("authorization", headers)
            entry = next(
                item for item in manifest["assets"] if item["url"].endswith("/main.css")
            )
            raw = (root / "cache" / "assets" / entry["filename"]).read_bytes()
            self.assertEqual(
                raw,
                assets["https://cdn.jsdelivr.net/npm/example/main.css"][0],
            )
            self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertIn("sha256-original", entry["integrity"])
            saved = json.loads((root / "cache" / "manifest.json").read_text())
            self.assertEqual(saved["assets"], manifest["assets"])

    def test_cache_reuses_verified_bytes_and_reports_corruption_without_repairing(self):
        url = "https://cdn.jsdelivr.net/npm/example/a.css"
        body = b".example { color: black; }"
        opener = Mock()
        opener.open.return_value = _response(body, "text/css")
        html = f'<link rel="stylesheet" href="{url}">'

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / "base.html"
            template.write_text(html, encoding="utf-8")
            first = PublicAssetCache(root / "cache", opener=opener).capture([template])
            self.assertEqual(first["status"], "complete")
            entry = first["assets"][0]
            asset = root / "cache" / "assets" / entry["filename"]

            no_network = Mock()
            reused = PublicAssetCache(root / "cache", opener=no_network).capture(
                [template]
            )
            self.assertEqual(reused["status"], "complete")
            no_network.open.assert_not_called()

            asset.write_bytes(b"corrupted")
            failed = PublicAssetCache(root / "cache", opener=no_network).capture(
                [template]
            )
            self.assertEqual(failed["status"], "partial")
            self.assertIn("failed hash/size verification", failed["errors"][0]["error"])
            self.assertEqual(asset.read_bytes(), b"corrupted")
            saved = json.loads((root / "cache" / "manifest.json").read_text())
            self.assertEqual(saved["status"], "partial")

    def test_fetch_failure_writes_explicit_partial_manifest(self):
        first_url = "https://cdn.jsdelivr.net/npm/example/a.js"
        second_url = "https://cdnjs.cloudflare.com/ajax/libs/example/b.js"
        opener = Mock()
        opener.open.side_effect = [
            _response(b"ok", "application/javascript"),
            OSError("offline"),
        ]

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / "scripts.html"
            template.write_text(
                f'<script src="{first_url}"></script><script src="{second_url}"></script>',
                encoding="utf-8",
            )
            manifest = PublicAssetCache(root / "cache", opener=opener).capture(
                [template]
            )

            self.assertEqual(manifest["status"], "partial")
            self.assertEqual(len(manifest["assets"]), 1)
            self.assertEqual(manifest["errors"][0]["url"], second_url)
            self.assertEqual(
                json.loads((root / "cache" / "manifest.json").read_text())["status"],
                "partial",
            )

    def test_cache_refuses_repository_output_path_before_writing(self):
        project_root = Path(__file__).resolve().parents[3]
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            PublicAssetCache(project_root).capture([])

    def test_redirect_to_host_outside_allowlist_is_rejected(self):
        from urllib.request import Request

        handler = SafeRedirectHandler()
        request = Request("https://cdn.jsdelivr.net/a.css")

        with self.assertRaisesRegex(ValueError, "not approved"):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {"Location": "https://evil.example/payload"},
                "https://evil.example/payload",
            )

    def test_css_imports_and_urls_resolve_relative_to_approved_source(self):
        css = b"""
        /* url(https://evil.example/ignored.woff2) */
        @import url('../css/nested.css') screen;
        @import "fonts.css";
        @font-face { src: url(../webfonts/icon.woff2) format('woff2'); }
        .logo { background-image: url('https://fonts.gstatic.com/logo.svg'); }
        .inline { background-image: url(data:image/svg+xml,%3Csvg%3E); }
        """

        found = discover_css_assets(
            css, "https://cdn.jsdelivr.net/npm/example/css/main.css"
        )

        self.assertEqual(
            [item.url for item in found],
            [
                "https://cdn.jsdelivr.net/npm/example/css/nested.css",
                "https://cdn.jsdelivr.net/npm/example/css/fonts.css",
                "https://cdn.jsdelivr.net/npm/example/webfonts/icon.woff2",
                "https://fonts.gstatic.com/logo.svg",
            ],
        )


if __name__ == "__main__":
    unittest.main()

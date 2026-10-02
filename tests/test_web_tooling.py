"""Offline configuration and launcher safety tests; no external dependencies needed."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
try:
    import tomllib
except ImportError:
    raise unittest.SkipTest('Optional web configuration requires Python 3.11+')
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools/web' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


config = load('configure')
runner = load('run_mcp')


class WebToolingTests(unittest.TestCase):
    def test_config_valid_paths_with_spaces(self):
        data = tomllib.loads(config.render(Path('/tmp/project with spaces')))
        self.assertEqual(set(data['mcp_servers']), set(config.NAMES))
        self.assertEqual(data['mcp_servers']['scrapling_local']['args'][0], '/tmp/project with spaces/tools/web/run_mcp.py')

    def test_bright_disabled_environment_only(self):
        bright = tomllib.loads(config.render(ROOT))['mcp_servers']['brightdata_fallback']
        self.assertFalse(bright['enabled'])
        self.assertEqual(bright['env_vars'], ['API_TOKEN'])
        self.assertNotIn('env', bright)
        self.assertEqual(bright['enabled_tools'], ['search_engine', 'scrape_as_markdown'])

    def test_preserves_existing_settings(self):
        old = 'model = "test"\n[mcp_servers.existing]\ncommand = "safe"\n'
        result = config.merge(old, config.render(ROOT))
        self.assertTrue(result.startswith(old.rstrip()))
        self.assertEqual(tomllib.loads(result)['mcp_servers']['existing']['command'], 'safe')

    def test_conflict_refused(self):
        with self.assertRaises(ValueError):
            config.merge(config.render(ROOT), config.render(ROOT))

    def test_preview_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            result = config.configure(Path(d))
            self.assertFalse(result['written'])
            self.assertFalse((Path(d) / '.codex').exists())

    def test_config_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'elsewhere').mkdir()
            (root / '.codex').symlink_to(root / 'elsewhere', target_is_directory=True)
            with self.assertRaises(ValueError):config.configure(root, write=True)

    def test_bright_missing_key_controlled(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'disabled until API_TOKEN'):
                runner.launch_spec('brightdata')

    def test_playwright_isolated_no_extension_or_profile(self):
        with patch.object(runner, 'browser_path', return_value='/tmp/browser'):
            if not (ROOT / 'tools/web/node_modules/@playwright/mcp/cli.js').exists():
                # Config shape remains testable in an uninstalled clone.
                args = (ROOT / 'tools/web/run_mcp.py').read_text()
                self.assertIn("'--isolated'", args)
                return
            args, env = runner.launch_spec('playwright')
            self.assertIn('--isolated', args)
            self.assertIn('--headless', args)
            self.assertNotIn('--extension', args)
            self.assertNotIn('--storage-state', args)
            self.assertNotIn('--no-sandbox', args)
            self.assertNotIn('API_TOKEN', env)
            self.assertEqual(env['PLAYWRIGHT_MCP_INIT_PAGE'], str(ROOT / 'tools/web/public_guard.cjs'))
            self.assertEqual(env['PLAYWRIGHT_MCP_BLOCK_SERVICE_WORKERS'], 'true')

    def test_browser_receipt_outside_root_refused(self):
        with tempfile.TemporaryDirectory() as d, patch.object(runner, 'ROOT', Path(d)):
            root = Path(d)
            (root / '.web-tools').mkdir()
            (root / 'other').write_text('data')
            (root / '.web-tools/browser.json').write_text(json.dumps({'executable_path': str(root / 'other')}))
            with self.assertRaises(ValueError):runner.browser_path()
    def test_browser_receipt_traversal_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d, patch.object(runner, 'ROOT', Path(d)):
            root = Path(d)
            browsers = root / '.web-tools/browsers'
            browsers.mkdir(parents=True)
            outside = root / 'other'
            outside.write_text('data')
            receipt = root / '.web-tools/browser.json'
            receipt.write_text(json.dumps({'executable_path': str(browsers / '../../other')}))
            with self.assertRaises(ValueError): runner.browser_path()
            (browsers / 'alias').symlink_to(outside)
            receipt.write_text(json.dumps({'executable_path': str(browsers / 'alias')}))
            with self.assertRaises(ValueError): runner.browser_path()
            binary = browsers / 'chromium'
            binary.write_text('data')
            receipt.write_text(json.dumps({'executable_path': str(binary)}))
            self.assertEqual(runner.browser_path(), str(binary))
    def test_unknown_launcher_component_refused(self):
        with self.assertRaises(ValueError): runner.launch_spec('unknown')
    def test_scrapling_uses_current_interpreter_after_checkout_rename(self):
        with tempfile.TemporaryDirectory() as d, patch.object(runner, 'ROOT', Path(d)), patch.object(runner, 'browser_path', return_value='/reviewed/browser'):
            binary = Path(d)/'.venv/bin'
            binary.mkdir(parents=True)
            (binary/'python').write_text('fixture')
            (binary/'scrapling-mcp').write_text('#!/obsolete/checkout/python\n')
            args,env=runner.launch_spec('scrapling')
            self.assertEqual(args[:2],[str(binary/'python'),str(binary/'scrapling-mcp')])
            self.assertNotIn('API_TOKEN',env)

    def test_unsafe_tools_not_enabled(self):
        servers = tomllib.loads(config.render(ROOT))['mcp_servers']
        enabled = servers['playwright_local']['enabled_tools']
        self.assertNotIn('browser_evaluate', enabled)
        self.assertNotIn('browser_run_code_unsafe', enabled)
        self.assertNotIn('browser_file_upload', enabled)
        self.assertNotIn('stealthy_fetch', servers['scrapling_local']['enabled_tools'])


if __name__ == '__main__':
    unittest.main()

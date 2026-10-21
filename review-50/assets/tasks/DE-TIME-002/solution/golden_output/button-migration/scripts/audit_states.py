"""Audit this team's frozen component contract, not generic WCAG certification."""
import argparse
import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.by_id = {}
        self.duplicates = []
        self.old_class = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if 'govuk-button--disabled' in values.get('class', '').split():
            self.old_class = True
        if 'id' in values:
            if values['id'] in self.by_id:
                self.duplicates.append(values['id'])
            self.by_id[values['id']] = {'tag': tag, 'attrs': values}


def audit(html, contract, executable='/usr/bin/chromium'):
    html = Path(html).resolve()
    contract = Path(contract).resolve()
    config = json.loads(contract.read_text())
    assert config['target_version'] == '5.0.0', 'Unsupported contract version; revise policy explicitly'
    parser = Elements()
    parser.feed(html.read_text())
    checks = []

    def record(name, passed, observed):
        checks.append({'check': name, 'pass': bool(passed), 'observed': observed})

    record('no_deprecated_disabled_class', not parser.old_class, parser.old_class)
    record('unique_dom_ids', not parser.duplicates, parser.duplicates)
    for case in config['states']:
        element = parser.by_id.get(case['id'])
        if element is None:
            record('state:' + case['id'], False, 'missing')
            continue
        attrs = element['attrs']
        # Boolean HTML attributes depend on presence, not value truthiness.
        native_disabled = element['tag'] in ('button', 'input') and 'disabled' in attrs
        okay = element['tag'] == case['tag'] and native_disabled == case['disabled']
        if case['tag'] == 'a':
            okay = okay and attrs.get('href') == case['href'] and 'disabled' not in attrs and attrs.get('aria-disabled') != 'true'
        if case['tag'] == 'p':
            okay = okay and not any(k in attrs for k in ('href', 'onclick', 'tabindex', 'role'))
        record('state:' + case['id'], okay, {'tag': element['tag'], 'native_disabled': native_disabled})
    browser_runs = []
    with sync_playwright() as playwright:
        options = {'headless': True, 'args': ['--no-sandbox']}
        if executable:
            options['executable_path'] = executable
        browser = playwright.chromium.launch(**options)
        browser_version = browser.version
        for width, height in [(1280, 900), (390, 844)]:
            context = browser.new_context(viewport={'width': width, 'height': height}, offline=True)
            page = context.new_page()
            errors, remote = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda req: remote.append(req.url) if req.url.startswith(('http:', 'https:')) else None)
            row = {'viewport': [width, height], 'checks': []}

            def test(name, action):
                try:
                    action()
                    row['checks'].append({'check': name, 'pass': True})
                except Exception as exc:
                    row['checks'].append({'check': name, 'pass': False, 'error': str(exc)[:350]})

            page.goto(html.as_uri())
            page.set_default_timeout(2500)

            def must(value):
                if not value:
                    raise AssertionError('Observed DOM behavior did not match contract')

            def labels():
                for c in config['states']:
                    element = page.locator('[id="' + c['id'] + '"]')
                    text = element.input_value() if c['tag'] == 'input' else element.inner_text()
                    must(c['label'] in text)
                must(page.locator('#live-status').get_attribute('role') == 'status')
                must(page.locator('#simulate').is_disabled())
                must('服务器幂等未验' in page.locator('body').inner_text())

            test('labels_initial_gate_and_scope', labels)

            def failure_recovery():
                page.locator('#subject').fill('示例材料')
                page.locator('#outcome').select_option('failure')
                page.locator('#simulate').focus()
                page.keyboard.press('Enter')
                must(page.locator('#simulate').is_disabled())
                must('处理中' in page.locator('#live-status').inner_text())
                page.locator('#live-status').filter(has_text='模拟失败').wait_for()
                must(page.locator('#simulate').is_enabled())
                must(page.locator('#subject').input_value() == '示例材料')
                must('重试' in page.locator('#simulate').inner_text())

            test('keyboard_failure_preserves_data_and_retries', failure_recovery)

            def success_and_doubleclick():
                before = int(page.locator('#attempts').inner_text())
                page.locator('#outcome').select_option('success')
                # Real DOM double activation; the second dispatch cannot start
                # another operation while the first is busy.
                page.locator('#simulate').evaluate('(e)=>{e.click();e.click();document.getElementById("live-form").requestSubmit()}')
                must(page.locator('#simulate').is_disabled())
                page.locator('#live-status').filter(has_text='已生成本机摘要').wait_for()
                must(int(page.locator('#attempts').inner_text()) == before + 1)
                must('示例材料' in page.locator('#summary').inner_text())
                must(page.locator('#simulate').is_enabled())

            test('busy_guard_and_success_summary', success_and_doubleclick)

            def keyboard_navigation():
                page.locator('#s-link').focus()
                page.keyboard.press('Enter')
                must(page.url.endswith('#guide'))
                must(page.locator('#s-empty').is_disabled())
                must(page.locator('#s-boolfalse').is_disabled())
                page.locator('#reset').focus()
                page.keyboard.press('Space')
                must(page.locator('#subject').input_value() == '')
                must(page.locator('#simulate').is_disabled())
                must(int(page.locator('#attempts').inner_text()) == 0)

            test('navigation_and_space_reset', keyboard_navigation)

            def reset_during_busy():
                page.locator('#subject').fill('待取消示例')
                page.locator('#outcome').select_option('success')
                page.locator('#simulate').click()
                must(page.locator('#simulate').is_disabled())
                page.locator('#reset').click()
                page.wait_for_timeout(1100)
                must(page.locator('#summary').inner_text() == '')
                must(page.locator('#subject').input_value() == '')
                must(page.locator('#attempts').inner_text() == '0')
                must('已生成' not in page.locator('#live-status').inner_text())

            test('reset_cancels_inflight_callback', reset_during_busy)

            def layout():
                must(page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                boxes = page.locator('button:visible, input:visible, select:visible, a:visible').evaluate_all('(els)=>els.map(e=>({w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}))')
                must(all(b['w'] >= 44 and b['h'] >= 44 for b in boxes))
                must(not errors and not remote)
                must(context.cookies() == [])

            test('contract_geometry_and_offline_execution', layout)
            row.update(errors=errors, remote_requests=remote)
            browser_runs.append(row)
            context.close()
        browser.close()
    passed = all(r['pass'] for r in checks) and all(t['pass'] for r in browser_runs for t in r['checks'])
    return {'target_version': config['target_version'], 'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'input_sha256': {str(p.name): hashlib.sha256(p.read_bytes()).hexdigest() for p in (html, contract)},
            'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'browser_version': browser_version, 'checks': checks, 'browser_runs': browser_runs, 'pass': passed,
            'scope': 'Frozen team contract on this local prototype; not GOV.UK production equivalence, full WCAG/assistive-technology certification, server idempotency or deployment.',
            'server_idempotency_verified': False, 'production_release': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browser', default='/usr/bin/chromium', help='Empty string uses installed Playwright browser')
    args = parser.parse_args()
    result = audit(args.html, args.contract, args.browser)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pass': result['pass'], 'static_checks': len(result['checks']), 'browser_runs': len(result['browser_runs'])}))
    raise SystemExit(0 if result['pass'] else 2)


if __name__ == '__main__':
    main()

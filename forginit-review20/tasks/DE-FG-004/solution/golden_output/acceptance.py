"""Exercise a local service-form prototype in a real Chromium browser.

These bounded checks do not establish full WCAG conformance or replace an
assistive-technology review. No requests are sent to an external service.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def audit(html_path, output):
    from PIL import Image, ImageStat
    from wcag_contrast_ratio import rgb

    output.mkdir(parents=True, exist_ok=True)
    checks, errors, requests, screenshots = [], [], [], []

    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})

    def shot(page, name):
        path = output / (name + ".png")
        page.screenshot(path=str(path), full_page=True)
        with Image.open(path) as bitmap:
            variance = sum(ImageStat.Stat(bitmap.convert("RGB")).var)
            check(name + ":nonblank", variance > 100)
        screenshots.append({"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    with sync_playwright() as p:
        binary = os.environ.get("CHROMIUM_EXECUTABLE_PATH")
        if not binary and Path("/usr/bin/chromium").exists():
            binary = "/usr/bin/chromium"
        browser = p.chromium.launch(headless=True, executable_path=binary, args=["--no-sandbox"])
        for width, height in ((1280, 900), (390, 844), (320, 800)):
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.set_default_timeout(5000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("http://**/*", lambda route: (requests.append(route.request.url), route.abort()))
            page.route("https://**/*", lambda route: (requests.append(route.request.url), route.abort()))
            prefix = str(width) + ":"
            try:
                page.goto(html_path.resolve().as_uri())
                check(prefix + "language", page.locator("html").get_attribute("lang") == "zh-CN")
                check(prefix + "no-horizontal-overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                check(prefix + "bitmap-loaded", page.locator("header img").evaluate("n => n.complete && n.naturalWidth > 0"))
                shot(page, str(width) + "-contact")
                for identity in ("applicantName", "email", "communityGroup", "next-0"):
                    page.keyboard.press("Tab")
                    check(prefix + "tab:" + identity, page.evaluate("document.activeElement.id") == identity)
                focus_style = page.locator("#next-0").evaluate("n => ({style:getComputedStyle(n).outlineStyle,width:parseFloat(getComputedStyle(n).outlineWidth)})")
                check(prefix + "visible-keyboard-focus", focus_style["style"] != "none" and focus_style["width"] >= 2)
                def computed_contrast(selector, property_name, threshold):
                    colors = page.locator(selector).evaluate("""(n, propertyName) => {
                        let node = n, background;
                        while (node) {
                            const value = getComputedStyle(node).backgroundColor;
                            if (value !== 'rgba(0, 0, 0, 0)' && value !== 'transparent') {
                                background = value; break;
                            }
                            node = node.parentElement;
                        }
                        return {foreground:getComputedStyle(n)[propertyName], background};
                    }""", property_name)
                    import re
                    def channels(value):
                        values = [float(x) for x in re.findall(r"[\d.]+", value or "")]
                        if len(values) not in (3, 4) or (len(values) == 4 and values[3] != 1):
                            raise ValueError("unsupported translucent contrast sample")
                        return tuple(v / 255 for v in values[:3])
                    check(prefix + "computed-contrast:" + selector + ":" + property_name,
                          rgb(channels(colors["foreground"]), channels(colors["background"])) >= threshold)
                computed_contrast("h1", "color", 4.5)
                computed_contrast("#next-0", "color", 4.5)
                computed_contrast("#applicantName", "borderTopColor", 3)
                for button in page.locator("button:visible").all():
                    bounds = button.bounding_box()
                    check(prefix + "button-target", bounds["width"] >= 24 and bounds["height"] >= 24)
                page.locator("#applicantName").fill("演练联系人")
                page.locator("#email").fill("invalid")
                page.locator("#next-0").focus(); page.keyboard.press("Enter")
                check(prefix + "invalid-summary-focus", page.evaluate("document.activeElement.id") == "error-summary")
                check(prefix + "email-identified", page.locator("#email").get_attribute("aria-invalid") == "true")
                check(prefix + "valid-field-preserved", page.locator("#applicantName").input_value() == "演练联系人")
                check(prefix + "error-associated", "email-error" in page.locator("#email").get_attribute("aria-describedby"))
                shot(page, str(width) + "-errors")
                page.locator('#error-list a[href="#email"]').click()
                check(prefix + "summary-link-focus", page.evaluate("document.activeElement.id") == "email")
                page.locator("#email").fill("demo@example.invalid")
                page.locator("#next-0").focus(); page.keyboard.press("Enter")
                check(prefix + "optional-org-not-blocking", page.locator("#step-1").is_visible())
                check(prefix + "next-heading-focused", page.evaluate("document.activeElement.id") == "heading-1")
                page.locator("#eventTitle").fill("社区读书会")
                page.locator("#eventDate").fill("2026-10-31")
                page.locator("#hours").fill("1.5")
                page.locator("#attendees").fill("121")
                page.locator("#next-1").click()
                for identity in ("eventDate", "hours", "attendees"):
                    check(prefix + "reject:" + identity, page.locator("#" + identity).get_attribute("aria-invalid") == "true")
                page.locator("#eventDate").fill("2026-11-18")
                for date, hours, attendees in (("2026-11-01", "1", "1"), ("2026-12-31", "4", "120")):
                    page.locator("#eventDate").fill(date)
                    page.locator("#hours").fill(hours)
                    page.locator("#attendees").fill(attendees)
                    page.locator("#next-1").click()
                    check(prefix + "allowed-boundary:" + date, page.locator("#step-2").is_visible())
                    check(prefix + "computed-fee:" + hours, str(int(hours) * 120) + ".00元" in page.locator("#review-details").inner_text())
                    page.locator("#back-2").click()
                for identity, invalid in (("eventDate", "2027-01-01"), ("hours", "0"), ("hours", "5"),
                                          ("attendees", "0"), ("attendees", "1.5")):
                    page.locator("#" + identity).fill(invalid)
                    page.locator("#next-1").click()
                    check(prefix + "invalid-boundary:" + identity + ":" + invalid,
                          page.locator("#" + identity).get_attribute("aria-invalid") == "true")
                    page.locator("#" + identity).fill({"eventDate":"2026-11-18", "hours":"2", "attendees":"80"}[identity])
                page.locator("#eventDate").fill("2026-11-18")
                page.locator("#hours").fill("2")
                page.locator("#attendees").fill("80")
                page.locator("#accessNeeds").fill("需要无台阶通道")
                page.locator("#next-1").focus(); page.keyboard.press("Enter")
                check(prefix + "review-focus", page.evaluate("document.activeElement.id") == "heading-2")
                review = page.locator("#review-details").inner_text()
                check(prefix + "approved-v2-quote", "240.00元" in review)
                check(prefix + "80-routine", "常规人工审核" in review)
                check(prefix + "previous-information-reused", "演练联系人" in review and "demo@example.invalid" in review)
                shot(page, str(width) + "-review")
                page.locator("#submit-booking").focus(); page.keyboard.press("Enter")
                check(prefix + "pending-not-approved", "尚未批准" in page.locator("#receipt-route").inner_text())
                check(prefix + "receipt-heading-focus", page.evaluate("document.activeElement.id") == "receipt-heading")
                check(prefix + "status-role", page.locator("#receipt-route").get_attribute("role") == "status")
                shot(page, str(width) + "-receipt")
                page.locator("#edit-booking").click(); page.locator("#back-2").click()
                check(prefix + "back-preserves-event", page.locator("#eventTitle").input_value() == "社区读书会")
                page.locator("#attendees").fill("81")
                page.locator("#back-1").click()
                check(prefix + "back-preserves-contact", page.locator("#applicantName").input_value() == "演练联系人")
                page.locator("#communityGroup").focus(); page.keyboard.press("Space")
                check(prefix + "conditional-org-visible", page.locator("#organisation-field").is_visible())
                page.keyboard.press("Tab")
                check(prefix + "conditional-org-tab-order", page.evaluate("document.activeElement.id") == "organisationName")
                page.locator("#next-0").click()
                check(prefix + "org-required-only-for-group", page.locator("#organisationName").get_attribute("aria-invalid") == "true")
                page.locator("#organisationName").fill("演练社区组织")
                page.locator("#next-0").click(); page.locator("#next-1").click()
                review = page.locator("#review-details").inner_text()
                check(prefix + "group-v2-quote", "168.00元" in review)
                check(prefix + "81-safety-escalation", "需额外安全审核" in review)
                page.locator("#submit-booking").click()
                check(prefix + "safety-receipt", "需额外安全审核" in page.locator("#receipt-route").inner_text())
                page.locator("#edit-booking").click(); page.locator("#back-2").click()
                payload = "<img src=x onerror=alert(1)>"
                page.locator("#eventTitle").fill(payload)
                page.locator("#attendees").fill("120"); page.locator("#next-1").click()
                check(prefix + "capacity120-allowed", page.locator("#step-2").is_visible())
                check(prefix + "user-content-is-text", payload in page.locator("#review-details").inner_text() and page.locator("#review-details img").count() == 0)
                check(prefix + "review-no-overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                check(prefix + "no-persistent-data", page.evaluate("localStorage.length === 0 && sessionStorage.length === 0"))
            except Exception as error:
                checks.append({"name": prefix + "browser-flow", "passed": False,
                               "error": type(error).__name__, "detail": str(error)[:1500]})
            finally:
                context.close()
        browser.close()
    check("no-javascript-errors", not errors)
    check("no-external-network", not requests)
    report = dict(passed=all(c["passed"] for c in checks), html_sha256=hashlib.sha256(html_path.read_bytes()).hexdigest(),
                  checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), checks=checks,
                  javascript_errors=errors, external_requests=requests, screenshots=screenshots,
                  limitations="Bounded Chromium keyboard/behavior/layout and sampled computed-color checks only; not full WCAG conformance or assistive-technology approval.")
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(passed=report["passed"], checks=len(checks), screenshots=len(screenshots))))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if audit(args.html, args.report_dir)["passed"] else 1)

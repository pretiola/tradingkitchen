"""Guard shared consent markup and the native newsletter submission contract."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate


FIXTURE = """
<!doctype html><html><head>
<link rel="stylesheet" href="/assets/fonts.ab12cd34.css">
<script src="/assets/analytics.1234abcd.js" defer></script>
</head><body>
<footer><a href="/privacy.html">Privacy policy</a>
<button type="button" data-privacy-open aria-controls="privacy-dialog" aria-haspopup="dialog" hidden>Privacy choices</button></footer>
<dialog id="privacy-dialog" aria-labelledby="privacy-title" aria-describedby="privacy-description">
<h2 id="privacy-title">Your privacy choices</h2><p id="privacy-description">Optional analytics.</p>
<button type="button" data-consent-choice="rejected">Reject optional cookies</button>
<button type="button" data-consent-choice="analytics">Allow analytics only</button>
<button type="button" data-consent-choice="advertising">Allow analytics and advertising</button>
</dialog></body></html>
"""

NEWSLETTER = """
<label for="newsletter-email">Email address</label>
<form id="newsletter-form" action="https://buttondown.com/api/emails/embed-subscribe/tradingkitchen" method="post">
<input id="newsletter-email" type="email" name="email" required aria-describedby="signup-note">
<input type="hidden" name="embed" value="1"><button type="submit">Join the email list</button>
</form><p id="signup-note">Check your inbox to confirm.</p>
<p>Email list powered by <a href="https://buttondown.com/tradingkitchen">Buttondown</a>.
<a href="/privacy.html">Our privacy policy</a>.</p>
"""


class PrivacyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def page(self, html):
        path = self.root / "index.html"
        path.write_text(html, encoding="utf-8")
        with patch.object(validate, "SITE", self.root):
            return validate.Page(path)

    def test_valid_hashed_assets_and_shared_controls(self):
        self.assertEqual(validate.privacy_errors(self.page(FIXTURE)), [])

    def test_missing_or_duplicate_consent_integration_fails(self):
        mutations = (
            (FIXTURE.replace('<script src="/assets/analytics.1234abcd.js" defer></script>', ''), "one deferred first-party"),
            (FIXTURE.replace('</head>', '<script src="/assets/analytics.js" defer></script></head>'), "one deferred first-party"),
            (FIXTURE.replace('id="privacy-dialog"', 'id="wrong-dialog"'), "one privacy dialog"),
            (FIXTURE.replace('data-consent-choice="rejected"', 'data-consent-choice="accept"'), "exactly one reject"),
        )
        for html, expected in mutations:
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in problem for problem in validate.privacy_errors(self.page(html))))

    def test_reopen_control_and_dialog_must_be_accessible(self):
        mutations = (
            (FIXTURE.replace('aria-controls="privacy-dialog"', 'aria-controls="wrong-dialog"'), "must be accessible"),
            (FIXTURE.replace('aria-labelledby="privacy-title"', 'aria-labelledby="missing-title"'), "valid aria-labelledby"),
            (FIXTURE.replace('>Privacy choices</button>', '></button>'), "must be accessible"),
            (FIXTURE.replace('<footer>', '<div>').replace('</footer>', '</div>'), "footer needs one"),
            (FIXTURE.replace('data-consent-choice="rejected"', 'data-consent-choice="rejected" disabled'), "labelled, enabled"),
        )
        for html, expected in mutations:
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in problem for problem in validate.privacy_errors(self.page(html))))

    def test_unexpanded_partials_and_preconsent_google_requests_fail(self):
        additions = (
            ('<!-- include: privacy-dialog -->', "unexpanded shared include"),
            ('<link rel="preconnect" href="https://fonts.gstatic.com">', "external Google Fonts"),
            ('<script src="https://www.googletagmanager.com/gtag/js?id=G-EXAMPLE"></script>', "third-party Google tracking"),
            ('<script>gtag("config", "G-EXAMPLE");</script>', "inline Google tracking"),
        )
        for addition, expected in additions:
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in problem for problem in validate.privacy_errors(self.page(FIXTURE.replace('</body>', addition + '</body>')))))

    def test_stylesheet_and_policy_must_be_first_party(self):
        html = FIXTURE.replace('/assets/fonts.ab12cd34.css', 'https://example.org/assets/fonts.ab12cd34.css')
        self.assertTrue(any("first-party font stylesheet" in problem for problem in validate.privacy_errors(self.page(html))))
        html = FIXTURE.replace('href="/privacy.html"', 'href="https://buttondown.com/legal/privacy"')
        self.assertTrue(any("our privacy policy" in problem for problem in validate.privacy_errors(self.page(html))))

    def test_newsletter_keeps_native_validation_and_clear_attribution(self):
        with patch.object(validate, "errors", []):
            validate.check_newsletter(self.page(NEWSLETTER))
            self.assertEqual(validate.errors, [])
        mutations = (
            (NEWSLETTER.replace('method="post"', 'method="post" novalidate'), "native signup validation"),
            (NEWSLETTER.replace('https://buttondown.com/api/emails/embed-subscribe/tradingkitchen', 'https://example.org/subscribe'), "verified Buttondown endpoint"),
            (NEWSLETTER.replace('Join the email list', 'Continue'), "Join the email list"),
            (NEWSLETTER.replace('Email list powered by', 'Service'), "identify Buttondown"),
            (NEWSLETTER.replace('href="/privacy.html"', 'href="https://buttondown.com/legal/privacy"'), "our own privacy policy"),
        )
        for html, expected in mutations:
            with self.subTest(expected=expected), patch.object(validate, "errors", []):
                validate.check_newsletter(self.page(html))
                self.assertTrue(any(expected in problem for problem in validate.errors))


if __name__ == "__main__":
    unittest.main()

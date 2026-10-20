"""Guard scroll-triggered image requests without losing no-script content."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate


SOURCES = '/assets/images/dish-320.webp 320w, /assets/images/dish-640.webp 640w'
DEFERRED = f'<img data-defer-image src="data:image/svg+xml,%3Csvg%3E%3C/svg%3E" data-src="/assets/images/dish-640.webp" data-srcset="{SOURCES}" sizes="50vw" width="640" height="480" alt="Finished dish" loading="eager">'
FALLBACK = f'<img src="/assets/images/dish-640.webp" srcset="{SOURCES}" sizes="50vw" width="640" height="480" alt="Finished dish" loading="lazy">'
LOADER = '<script src="/assets/homepage-images.1234abcd.js" defer></script>'
HOMEPAGE = f'{LOADER}{DEFERRED}<noscript>{FALLBACK}</noscript>'


class DeferredImageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for asset in ('assets/images/dish-320.webp', 'assets/images/dish-640.webp', 'assets/homepage-images.1234abcd.js'):
            path = self.root / asset
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture')

    def errors(self, html=HOMEPAGE, name='index.html'):
        path = self.root / name
        path.write_text(html, encoding='utf-8')
        with patch.object(validate, 'SITE', self.root), patch.object(validate, 'errors', []):
            validate.check_images(validate.Page(path))
            return validate.errors.copy()

    def test_deferred_homepage_and_noscript_fallback_are_valid(self):
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.errors(FALLBACK, 'recipe.html'), [])

    def test_real_image_requests_cannot_leak_before_scroll(self):
        mutations = (
            (HOMEPAGE.replace('src="data:image/svg+xml,%3Csvg%3E%3C/svg%3E"', 'src="/assets/images/dish-640.webp"'), 'inline image placeholder'),
            (HOMEPAGE.replace('data-defer-image ', f'data-defer-image srcset="{SOURCES}" '), 'must not expose a preloaded srcset'),
            (HOMEPAGE.replace('loading="eager"', 'loading="lazy"'), 'must use loading=eager'),
        )
        for html, expected in mutations:
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in error for error in self.errors(html)))

    def test_responsive_deferred_sources_must_be_valid_existing_local_assets(self):
        mutations = (
            (HOMEPAGE.replace('data-src="/assets/images/dish-640.webp"', 'data-src="https://elsewhere.example/dish.webp"'), 'must be a local asset'),
            (HOMEPAGE.replace('/assets/images/dish-320.webp', '/assets/images/missing.webp'), 'missing local target'),
            (HOMEPAGE.replace('dish-320.webp 320w', 'dish-320.webp broken'), 'invalid width-based srcset'),
            (HOMEPAGE.replace(f'data-srcset="{SOURCES}"', ''), 'responsive data-srcset and sizes'),
        )
        for html, expected in mutations:
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in error for error in self.errors(html)))

    def test_loader_is_required_once_and_only_on_homepage(self):
        for html in (HOMEPAGE.replace(LOADER, ''), HOMEPAGE + LOADER, HOMEPAGE.replace('homepage-images.1234abcd.js" defer', 'homepage-images.1234abcd.js"')):
            with self.subTest(html=html):
                self.assertTrue(any('expected one deferred first-party homepage image loader' in error for error in self.errors(html)))
        self.assertTrue(any('homepage image loader belongs only' in error for error in self.errors(LOADER + FALLBACK, 'recipe.html')))
        self.assertTrue(any('only visible homepage images' in error for error in self.errors(DEFERRED, 'recipe.html')))

    def test_every_live_homepage_image_is_deferred(self):
        self.assertTrue(any('all visible homepage images' in error for error in self.errors(HOMEPAGE + FALLBACK)))

    def test_noscript_fallback_preserves_sources_and_description(self):
        self.assertTrue(any('one noscript fallback' in error for error in self.errors(LOADER + DEFERRED)))
        for fallback in (FALLBACK.replace('Finished dish', 'Different dish'), FALLBACK.replace('sizes="50vw"', 'sizes="100vw"')):
            with self.subTest(fallback=fallback):
                self.assertTrue(any('noscript image must preserve' in error for error in self.errors(f'{LOADER}{DEFERRED}<noscript>{fallback}</noscript>')))


if __name__ == '__main__':
    unittest.main()

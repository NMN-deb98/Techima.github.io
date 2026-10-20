import json
import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

os.environ["FLASK_SECRET_KEY"] = "test-only-secret-do-not-use-in-production"
os.environ["CMS_USERNAME"] = "test-owner"
os.environ["CMS_PASSWORD_HASH"] = ""
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GITHUB_TOKEN"] = ""

from werkzeug.security import generate_password_hash
os.environ["CMS_PASSWORD_HASH"] = generate_password_hash("test-password")

from app import app, db, Article
from scripts import build_articles as generator

class CmsSmokeTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def csrf(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        match = re.search(rb'name="csrf" value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def login(self):
        token = self.csrf()
        response = self.client.post("/login", data={
            "csrf": token, "username": "test-owner", "password": "test-password"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("نمای کلی".encode(), response.data)

    def test_health_and_owner_login(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 302)
        self.login()
        self.assertEqual(self.client.get("/articles").status_code, 200)
        self.assertEqual(self.client.get("/articles/new").status_code, 200)

    def test_draft_is_saved_without_github_token(self):
        self.login()
        with self.client.session_transaction() as sess:
            token = sess["csrf"]
        response = self.client.post("/articles/new", data={
            "csrf": token, "title": "مقاله آزمایشی", "slug": "test-article",
            "description": "توضیح آزمایشی", "body": "# متن آزمایشی",
            "status": "draft", "tags": "تست", "image": "", "image_alt": ""
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            article = Article.query.filter_by(slug="test-article").first()
            self.assertIsNotNone(article)
            self.assertEqual(article.status, "draft")

class GeneratorTests(unittest.TestCase):
    def test_markdown_script_is_sanitized(self):
        article = {
            "slug": "test-article", "title": "عنوان تست", "description": "توضیح تست",
            "body": "متن سالم\n\n<script>alert(1)</script>",
            "datePublished": "2026-10-20", "dateModified": "2026-10-20", "tags": []
        }
        output = generator.render_article(article)
        self.assertNotIn("<script>alert(1)</script>", output)
        self.assertIn('type="application/ld+json"', output)
        self.assertIn('rel="canonical"', output)

    def test_sitemap_preserves_site_urls_and_removes_stale_cms_urls(self):
        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sitemap.xml"
            root = ET.Element(f"{{{namespace}}}urlset")
            for url in [
                generator.BASE_URL + "/",
                generator.BASE_URL + "/articles/old-cms-post/",
            ]:
                node = ET.SubElement(root, f"{{{namespace}}}url")
                ET.SubElement(node, f"{{{namespace}}}loc").text = url
            ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
            old_path = generator.SITEMAP_PATH
            generator.SITEMAP_PATH = path
            try:
                generator.update_sitemap([])
            finally:
                generator.SITEMAP_PATH = old_path
            content = path.read_text(encoding="utf-8")
            self.assertIn(generator.BASE_URL + "/", content)
            self.assertNotIn("old-cms-post", content)

    def test_empty_article_list_does_not_change_existing_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.html"
            original = "<html><body><main>Existing content</main></body></html>"
            path.write_text(original, encoding="utf-8")
            old_path = generator.INDEX_PATH
            generator.INDEX_PATH = path
            try:
                generator.update_articles_index([])
            finally:
                generator.INDEX_PATH = old_path
            self.assertEqual(path.read_text(encoding="utf-8"), original)

if __name__ == "__main__":
    unittest.main()

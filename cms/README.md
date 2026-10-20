# Techima CMS publishing foundation

This directory documents the first integration layer for the Techima CMS.

## Current repository findings

- The public website is a static GitHub Pages site under the project path `/Techima.github.io/`.
- The current article listing lives at `articles/index.html`.
- Older files such as `articles/article-1.html` use a different, legacy asset layout. The generator intentionally creates new articles in clean, separate paths such as `articles/example-slug/index.html` rather than overwriting legacy files.
- The existing Cloudflare Worker in `backend/worker.js` handles public comment submissions only; it is not an article CMS or an owner approval interface.

## Article content contract

Place one JSON file per article in `content/articles/`. A file can use this shape:

```json
{
  "slug": "my-first-article",
  "title": "عنوان مقاله",
  "description": "توضیح کوتاه و یکتای مقاله",
  "status": "draft",
  "datePublished": "2026-10-20",
  "dateModified": "2026-10-20",
  "tags": ["آموزش", "وب"],
  "body": "# تیتر اصلی متن\n\nمتن مقاله با Markdown."
}
```

Only items whose `status` is exactly `published` are generated. Slugs must contain lowercase English letters, digits and single hyphens. The build produces static HTML, adds article URLs to `sitemap.xml`, and inserts article cards in the existing articles index.

## Important safety boundary

This is only the static publishing foundation. It is not yet the finished admin UI, login/session system, secure GitHub API bridge, media library, comments moderation panel, scheduled publishing, or complete CMS. Do not add a GitHub token to website files or commit secrets. The workflow must be tested on a separate branch before any production merge.

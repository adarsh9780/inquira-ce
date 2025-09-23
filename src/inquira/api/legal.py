from fastapi import APIRouter, Response
import importlib.resources

router = APIRouter(prefix="/legal", tags=["Legal"])


@router.get("/terms", summary="Terms & Conditions (Markdown)")
async def get_terms_markdown():
    """Return the Terms & Conditions as Markdown text.

    Media type is `text/markdown` so browser/clients can render or display
    it appropriately. The content is packaged with the application under
    `inquira/legal/terms.md`.
    """
    try:
        terms_path = importlib.resources.files("inquira").joinpath("legal", "terms.md")
        content = terms_path.read_text(encoding="utf-8")
        return Response(content, media_type="text/markdown; charset=utf-8")
    except Exception as e:
        # Fallback plain text error
        return Response(
            f"Terms not available: {e}",
            media_type="text/plain; charset=utf-8",
            status_code=500,
        )


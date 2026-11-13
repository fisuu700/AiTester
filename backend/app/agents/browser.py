"""Helper Playwright partagé par les agents navigateur."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.agents.base import AgentContext


@asynccontextmanager
async def browser_page(ctx: AgentContext) -> AsyncIterator["object"]:
    """Ouvre un Chromium headless et fournit une page configurée."""
    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent=ctx.user_agent,
        ignore_https_errors=True,
    )
    page = await context.new_page()
    try:
        yield page
    finally:
        try:
            await context.close()
            await browser.close()
        finally:
            await playwright.stop()

"""Moteur UI : pilotage Playwright d'un navigateur réel + nettoyage DOM via BeautifulSoup4.

Le nettoyage supprime <script>, <style>, <svg>, les commentaires HTML et les
attributs non essentiels afin de réduire la taille du payload envoyé à l'IA
(économie RAM + latence).
"""

from __future__ import annotations

import base64
import uuid
from typing import Optional

from bs4 import BeautifulSoup, Comment
from playwright.async_api import (
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from app.config import settings
from app.schemas import UIAction

STRIPPED_TAGS = ("script", "style", "svg", "noscript", "iframe", "link", "meta")
STRIPPED_ATTRS = ("style", "class", "id", "data-reactid", "aria-hidden", "tabindex")
DOM_MAX_CHARS = 20000


def clean_dom(html: str, max_chars: int = DOM_MAX_CHARS) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(STRIPPED_TAGS):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for element in soup.find_all(True):
        for attr in STRIPPED_ATTRS:
            element.attrs.pop(attr, None)
    text = str(soup)
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


class UIEngine:
    def __init__(self, logger, screenshots_dir: str) -> None:
        self.log = logger
        self.screenshots_dir = screenshots_dir
        self._playwright = None
        self.browser = None
        self.context = None
        self.page: Optional[Page] = None

    async def start(self, target_url: str, headless: bool | None = None) -> None:
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(headless=settings.browser_headless if headless is None else headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            base_url=target_url,
        )
        self.page = await self.context.new_page()

    async def stop(self) -> None:
        for closer in (self.context, self.browser):
            if closer:
                try:
                    await closer.close()
                except Exception:  # noqa: BLE001
                    pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:  # noqa: BLE001
                pass

    async def current_dom(self) -> str:
        if not self.page:
            return ""
        try:
            html = await self.page.content()
        except PlaywrightError:
            return ""
        return clean_dom(html)

    async def _screenshot(self, run_id: str, step_index: int) -> Optional[str]:
        if not self.page:
            return None
        path = f"{self.screenshots_dir}/{run_id}_step{step_index:02d}_{uuid.uuid4().hex[:6]}.png"
        try:
            await self.page.screenshot(path=path, full_page=False)
        except PlaywrightError as exc:
            self.log.warning(f"Échec de la capture d'écran : {exc}")
            return None
        return path

    async def run_action(
        self, run_id: str, step_index: int, action: str, selector: str, value: Optional[str]
    ) -> UIAction:
        """Exécute une action atomique dans le navigateur réel."""
        if not self.page:
            return UIAction(
                action=action, selector=selector, value=value, ok=False, error="Page non initialisée"
            )
        ok, error = True, None
        try:
            timeout = settings.browser_timeout_ms
            if action == "goto":
                target = selector if selector.startswith("http") else (selector if selector else value)
                await self.page.goto(str(target), timeout=timeout, wait_until="domcontentloaded")
            elif action == "click":
                await self.page.click(selector, timeout=timeout)
            elif action == "fill":
                await self.page.fill(selector, value or "", timeout=timeout)
            elif action == "select":
                await self.page.select_option(selector, value or "", timeout=timeout)
            elif action == "press":
                await self.page.press(selector or "body", value or "Enter", timeout=timeout)
            elif action == "wait":
                await self.page.wait_for_timeout(500)
            elif action == "assert_text":
                body_text = await self.page.inner_text("body")
                if value and value.lower() not in body_text.lower():
                    ok = False
                    error = f"Texte attendu introuvable : « {value} »"
            else:
                ok = False
                error = f"Action inconnue : {action}"
        except PlaywrightTimeoutError as exc:
            ok, error = False, f"Délai dépassé ({selector or action}) : {exc}"
        except PlaywrightError as exc:
            ok, error = False, f"Erreur Playwright : {exc}"

        screenshot = await self._screenshot(run_id, step_index)
        dom_preview = (await self.current_dom())[:1500]
        return UIAction(
            action=action,
            selector=selector,
            value=value,
            ok=ok,
            error=error,
            screenshot=screenshot,
            dom_preview=dom_preview,
        )


def screenshot_to_data_url(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as fh:
            return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        return None

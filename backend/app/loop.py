"""Fabrique de boucle d'événements compatible Playwright sous Windows.

Par défaut, uvicorn 0.54+ utilise une ``SelectorEventLoop`` sur Windows dès que
``--reload`` (ou ``--workers``) est actif — voir ``uvicorn/loops/asyncio.py``.
Or ``asyncio.create_subprocess_exec`` (utilisé par Playwright pour lancer
Chromium) n'est pas implémenté sur cette boucle et lève ``NotImplementedError``,
ce qui faisait échouer silencieusement les agents Performance et Accessibilité.

Cette fabrique force la ``ProactorEventLoop`` sur Windows, même en mode reload,
afin que les agents navigateur fonctionnent.

Utilisation :

    uvicorn app.main:app --reload --loop app.loop:proactor_loop_factory

Note : uvicorn appelle cette fonction sans argument pour créer la boucle
(``Config.get_loop_factory`` renvoie la fonction telle quelle, puis
``asyncio.Runner`` l'invoque).
"""

from __future__ import annotations

import asyncio
import sys


def proactor_loop_factory() -> asyncio.AbstractEventLoop:
    """Crée une boucle d'événements supportant les sous-processus."""
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop()
    return asyncio.SelectorEventLoop()

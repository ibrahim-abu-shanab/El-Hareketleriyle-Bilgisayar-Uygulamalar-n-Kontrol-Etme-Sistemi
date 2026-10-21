# JestKontrol — project rules

Hand-gesture computer control system (Python 3.12, MediaPipe, OpenCV, CustomTkinter). Requirements: `Hafta2_Gereksinim_Analiz_Raporu.docx`; UI mockups: `design/`.

## Architecture (Clean Architecture)
- Layers in `src/jestkontrol/`: `domain` ← `application` ← `infrastructure` / `ui`. Dependencies point inward only.
  - `domain`: pure Python (stdlib only), entities, value objects, settings.
  - `application`: use cases, recognizers, ports (`Protocol`s). Imports `domain` only.
  - `infrastructure`: adapters for ports (OpenCV, MediaPipe, PyAutoGUI, pycaw, JSON/CSV storage, Win32).
  - `ui`: CustomTkinter GUI; imports `application`/`domain` only, receives `AppServices`.
  - `bootstrap.py`: the only composition root that wires application ports to infrastructure adapters (`application/services.py` assembles the object graph).
- `tests/test_architecture.py` enforces the dependency rule by scanning imports.

## Code rules
- Clean Code, SOLID, DRY. Small single-purpose classes/functions, intention-revealing names, no magic numbers (name them or put them in `Settings`).
- Depend on abstractions (ports), inject dependencies through constructors; new gesture = new recognizer + handler, no edits to existing ones (OCP).
- Identifiers and comments in English; user-facing strings live in `application/i18n/catalog_tr.py` and `catalog_en.py` (same keys, enforced by tests).
- Design tokens: `ui/assets/tokens.json` must equal `design/tokens.json` (test). Gesture art PNGs in `ui/assets/art/` were rasterized from `design/project/art/*.svg`.
- Pure logic is tested with pytest and fakes for every port; never require a camera in unit tests.

## UI threading rules
- Tk is touched only on the UI thread. Callbacks from the capture/hotkey threads go through `UiDispatcher.post` (pages: `Page.on_ui_thread`).
- Pages register subscriptions with `Page.listen(...)` so they are removed when the page is destroyed.
- Garbage collection runs only on the UI thread (`ui/app.py`): collecting Tk images on the capture thread stalls the camera loop.

## Workflow
- Run the app: `.venv\Scripts\python -m jestkontrol` (GUI) or `... -m jestkontrol --headless --mode mouse --debug`.
- Run tests: `.venv\Scripts\python -m pytest`.
- graphify: use `graphify-out/` (`graphify query` / `explain`) first for navigation, and run `graphify update .` after every change before finishing a task.

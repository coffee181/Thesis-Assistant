# Open Source README Design

## Goal

Rewrite the repository README so Thesis Assistant looks like a usable open-source desktop application, not a development log.

## Current Status

This README polish is blocked by the desktop UI redesign in `docs/superpowers/specs/2026-06-05-desktop-ui-redesign-design.md`.

Do not generate final README screenshots from the current control-panel UI. The README should be updated only after the redesigned desktop interface has been implemented and visually reviewed.

## Audience

The README should serve two audiences:

- Researchers or students who want to install the Windows app and use it for literature work.
- Developers who want to inspect, build, test, or package the project.

## Direction

Use the approved Hybrid direction:

- Lead with product value, screenshots, installation, and quick start.
- Keep development, testing, and release build instructions later in the file.
- Keep the tone concrete and honest: this is a local-first MVP, not a finished commercial product.

## Required README Structure

1. Product title and one-sentence description.
2. Badges for Windows, Tauri, React, FastAPI, local-first storage, and supported model providers.
3. A primary screenshot near the top.
4. A compact "Why Thesis Assistant" section.
5. Screenshot gallery with real app screenshots stored under `docs/assets/screenshots/`.
6. Feature list grouped by user workflow.
7. Installation and quick start for normal Windows users.
8. Privacy and data notes.
9. Model provider settings.
10. Development commands.
11. Release build instructions.
12. Test commands and roadmap.

## Screenshot Requirements

Use real application screenshots instead of mockups. The screenshots should be generated from a temporary local demo library and must not require committing the source PDF or library data.

Target files:

- `docs/assets/screenshots/workbench.png`
- `docs/assets/screenshots/reader-assistant.png`

Optional third screenshot if it can be produced reliably:

- `docs/assets/screenshots/discovery-import.png`

## Non-Goals

- Do not redesign the application UI.
- Do not add new product behavior.
- Do not commit generated installers, local libraries, source PDFs, secrets, or temporary screenshot tooling.

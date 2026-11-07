<p align="center">
  <img src="docs/star5/star5-search-ocean.jpg" alt="Star5 Search: research, answered" width="100%">
</p>

<h1 align="center"><img src="docs/star5/icon.png" alt="" width="44" align="center">&nbsp;Star5 Search</h1>

<p align="center">
  <b>A private, self-hosted research assistant for the web.</b><br>
  Ask a question and get a cited answer, from a 30-second reply to a multi-level investigation.
</p>

---

Star5 Search reads the web for you. It plans its searches, reads the pages, and writes an
answer with numbered citations. Every claim can be checked against its source. It runs on
your own server behind your own login. Your questions, history and files stay with you.

## Three levels of depth

| Mode | Typical time | Use it for |
|---|---|---|
| ⚡ **Veloce** (Fast) | **~30 s** | Direct answers: facts, prices, opening hours, "find me a good … near me" |
| 📚 **Standard** | **2-3 min** | A complete, sourced report across many sources |
| 🔭 **Approfondita** (Deep) | **5-8 min** | Complex questions explored over several levels of sub-questions |

- **Veloce** is a purpose-built pipeline with no agent loop:
  1. A small model writes 2-3 sharp queries.
  2. Every query runs on **Brave, Bing and DuckDuckGo at once**, with a timeout per engine.
  3. The best pages are read within 8 seconds.
  4. One strong model writes a concise answer with citations.

  Measured: 21-29 s, with 6-10 cited sources.
- **Standard** and **Approfondita** use the [GPT Researcher](https://github.com/assafelovic/gpt-researcher)
  agent. Before the search starts, a research brief turns the question into a goal, a
  deliverable and search hints. "Find me a good psychologist" therefore yields a shortlist of
  named people, not an essay on prices.

## What you get

- **Answers with sources.** Sources appear as cards, cited sources first, and likely
  official sites are flagged. Each card shows which engines found it, and the answer says how many sources each engine contributed (used, read, cited) and whether one timed out. The answer has numbered citations and a table of contents. You
  can download it as PDF, Word or Markdown.
- **Conversations.** Ask follow-ups on the report ("from the report") or start a new web
  search with the previous context. The history is always visible: the latest searches are
  on the home page and the full history is in the sidebar, the same on every device.
- **Guide a running answer.** While a search or report chat can still take directions,
  the follow-up box shows two choices: "Guide this answer" (coral) adds directions, files
  or a location to it, "New question" queues a separate question that starts when the
  current answer ends. The "Guide this answer" link under a running turn picks that turn.
  Directions can change the scope or answer language; later ones take precedence.
  Research may search the web again and rewrite the answer, taking extra time and tokens.
  The UI shows whether each direction was applied or failed. When the answer starts
  finalizing, the guide option disappears and an unsent draft with its files switches to
  "New question", with a notice.
- **Listen.** "Listen" under a finished answer reads it aloud with an Azure neural voice
  (Dragon HD) in the answer's language. It starts within a few seconds: the text is sent in
  growing chunks while the previous one plays. Headings, paragraphs and list items are read;
  tables, code, links and the reference list are skipped. The paragraph being read is
  highlighted. While it plays, a speed pill (1× to 2×, and 0.75×) and a stop button appear
  next to it. It keeps playing with the screen locked and shows on the lock screen and
  in headphone controls. The audio is cached on the server, so replaying it is free.
  Each answer has a cap on the characters it can have voiced: twice its length plus 4,000.
- **Share to search (Android).** The installed PWA appears in Android's Share menu for
  links, text, photos, video, audio and documents. Shared content is staged temporarily
  in IndexedDB by the service worker, imported into the home composer, and sent only
  after the user reviews and submits the question.
- **Attachments.**
  - Photos, including HEIC: the vision model reads visible text, brands and places.
  - Audio and voice recordings: transcribed locally with Whisper.
  - Video: frames plus the transcript of the soundtrack.
  - Documents: PDF (OCR when scanned), Word, PowerPoint, Excel, EPUB, HTML and text.

  You can ask "where can I buy this?" with a photo, or "is this quote fair?" with a PDF.
  Up to 10 files can be attached to each direction. Large extracted texts are shared
  fairly within the model's context budget and explicitly marked when truncated; queries
  derived from them may be sent to the configured external search providers.
- **Your location, on request.** GPS is used only for the question you attach it to. It is
  rounded to about 100 m before reverse geocoding, so "near me" means near you.
- **Your choice of reasoning.** Pick automatic, low, medium, high, very high or maximum.
  The choice is remembered for the next searches.
- **Live progress.** You see the plan, the queries, the pages read and the writing step.
  Closing the tab does not stop a search, and you can come back to it later.
- **Token counter.** Each answer shows the model tokens it used, and each conversation
  shows its total.
- **Multilingual.** The interface is in Italian, French and English. The answer follows the
  language of the question, or the one you choose.

## Search engines

Every query goes to **Brave** (official API), **Bing** and **DuckDuckGo** (both through
[ddgs](https://pypi.org/project/ddgs/)) in parallel. Each engine has a deadline that depends
on the mode:

| Mode | Engine timeout |
|---|---|
| Veloce | 5 s |
| Standard | 8 s |
| Approfondita | 12 s |
| Report chat | 6 s |

An engine that is late or fails is simply left out of that query. Results are merged one per
engine at a time, deduplicated, and keep the list of engines that found them. Standard and
Approfondita use at most 1.5 times the per-engine count per query, so three engines do not
triple the pages to read.
## Privacy and security

- **Self-hosted.** It runs in your own container behind your own sign-in (nginx
  `auth_request`, Google login restricted to the owners).
- **No shared caching.** Every response is `Cache-Control: private, no-store`.
- **Locked-down pages.** The CSP is strict, with no inline code. Page text is inserted as
  text and Markdown is sanitised.
- **Safe uploads.** Originals are served only as sandboxed downloads. Unused uploads are
  deleted automatically.
- **Public sites only.** The fast reader fetches only public internet hosts, never LAN or
  loopback addresses.

## How it is built

```
browser ──▶ nginx (login, no-store) ──▶ FastAPI app (star5/)
                                          ├─ Veloce pipeline (star5/fast.py)
                                          ├─ GPT Researcher agent (Standard, Approfondita)
                                          ├─ attachments: media worker + Whisper (separate venv)
                                          ├─ read aloud: star5/speech.py ─▶ proxy /speech/tts (Azure Speech)
                                          └─ SQLite: threads, turns, uploads
models:  any OpenAI-compatible endpoint (here an Azure proxy with "fast" and "frontier" aliases)
search:  Brave Search API + Bing + DuckDuckGo (ddgs), in parallel, deduplicated, timeout per mode
```

All Star5 code lives in [`star5/`](star5) and [`star5_main.py`](star5_main.py), on top of an
unmodified GPT Researcher, so upstream improvements can still be merged. The upstream web
UI and API are not served.

## Running it

Requirements: Python 3.12 and an OpenAI-compatible model endpoint. A
[Brave Search API](https://brave.com/search/api/) key is recommended; Bing and DuckDuckGo need none.

```bash
pip install -r requirements.txt
export CONFIG_PATH=/path/to/config.json   # models, retriever = brave, token limits
export BRAVE_API_KEY=...                  # and the model endpoint variables
uvicorn star5_main:app --host 127.0.0.1 --port 8000
```

Put it behind a reverse proxy that authenticates users.

Attachments need a second environment (`av`, `faster-whisper`, `pillow-heif`) pointed to by
`STAR5_MEDIA_PYTHON`.

"Listen" posts SSML to `$AZURE_OPENAI_ENDPOINT/speech/tts` with `AZURE_OPENAI_API_KEY`: the
proxy forwards it to Azure Speech with its managed identity. Audio is cached in
`$STAR5_DATA/speech/<turn>/` and deleted with the thread.

Tests: `python -m unittest star5.tests.test_star5`.

## Credits

Star5 Search is built on [GPT Researcher](https://github.com/assafelovic/gpt-researcher) by
Assaf Elovic and contributors, released under the Apache 2.0 license (see [LICENSE](LICENSE)).
The original project README is kept in [UPSTREAM-README.md](UPSTREAM-README.md).

<p align="center">
  <img src="docs/star5/star5-search-emerald.jpg" alt="Star5 Search, emerald edition" width="70%">
</p>

# Research: Selenium 4.x concurrency & waits for the scraper

Current anti-patterns: new Chrome + `ChromeDriverManager().install()` per product page, fixed
`time.sleep()`, drivers leaked on exception. All three are fixable with stock Selenium 4.

## 1. Thread-local driver reuse with ThreadPoolExecutor

One driver per **worker thread**, not per task. `ThreadPoolExecutor` has `initializer=` but **no
finalizer**, so cleanup must be explicit. Reliable recipe: `threading.local()` + a global registry
of created drivers + `try/finally` around `executor.shutdown()` (and `atexit` as a safety net).

```python
import atexit, threading
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver

_tls = threading.local()
_drivers: list[webdriver.Chrome] = []      # every driver ever created
_lock = threading.Lock()

def get_driver() -> webdriver.Chrome:
    d = getattr(_tls, "driver", None)
    if d is None:
        d = webdriver.Chrome(options=build_options())   # see §2/§4
        _tls.driver = d
        with _lock:
            _drivers.append(d)
    return d

def quit_all():
    with _lock:
        for d in _drivers:
            try: d.quit()
            except Exception: pass
        _drivers.clear()

atexit.register(quit_all)                  # net for hard exits / KeyboardInterrupt

def scrape(url):
    d = get_driver()
    try:
        d.get(url); return parse(d)
    except Exception as e:
        return {"url": url, "error": str(e)}   # never let the thread die holding a driver

with ThreadPoolExecutor(max_workers=4, initializer=_tls_init) as ex:  # initializer optional
    try:
        results = list(ex.map(scrape, urls))
    finally:
        quit_all()                          # deterministic; atexit becomes a no-op
```

Notes:
- `initializer=` runs once per worker thread — fine for eager driver creation, but lazy
  `get_driver()` is better: threads that never get work don't spawn Chrome.
- Do **not** rely on `weakref.finalize` on the driver: threads outlive tasks, GC timing is
  unspecified, and a finalizer running during interpreter shutdown may fail to reach the network.
- `driver.quit()` (not `close()`) is what kills the chromedriver process. A leaked `quit()` leaves
  a zombie `chromedriver` + `Google Chrome for Testing` per page — the current leak.
- Cap `max_workers` at ~4–8: each Chrome is 200–400 MB RSS.
- Reuse is safe only if you reset state between tasks when needed (`delete_all_cookies()`); for a
  read-only scraper it's fine.

## 2. Driver binary: drop webdriver-manager

`ChromeDriverManager().install()` does a network round-trip (version JSON + possible zip download)
and disk I/O; per-page it is the single biggest fixed cost, and it is the usual source of
"connection refused"/rate-limit flakiness in threads (concurrent writes to `~/.wdm`).

**Selenium Manager** is built into `selenium >= 4.6` (announced in the Selenium 4.6.0 release blog,
"Introducing Selenium Manager", Nov 2022; fully supported and default since 4.11 which also
auto-downloads the *browser*). So:

```python
driver = webdriver.Chrome(options=opts)   # no Service, no path, no webdriver-manager
```

Selenium Manager resolves/downloads the matching chromedriver from Chrome-for-Testing endpoints,
caches it in `~/.cache/selenium`, and its resolution is done once per process in practice.

Recommendation: **remove `webdriver-manager` from requirements.txt** and delete all
`Service(ChromeDriverManager().install())` calls. Pin `selenium>=4.15`.

If you must keep webdriver-manager (offline/proxy constraints), at minimum resolve the path once at
module import and reuse the string:

```python
DRIVER_PATH = ChromeDriverManager().install()      # module-level, once
service = Service(DRIVER_PATH)                     # new Service per driver, same path
```
(`Service` objects are not reusable across drivers — the path string is.)

## 3. Replace `time.sleep` with WebDriverWait / expected_conditions

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

wait = WebDriverWait(driver, 15, poll_frequency=0.3)

wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#product-title")))   # in DOM
wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".price")))         # rendered
btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".load-more")))     # enabled+visible
wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".spinner")))
```

**"Load more" → list must grow** (the case fixed sleeps are usually hiding):

```python
ITEMS = (By.CSS_SELECTOR, ".product-card")
before = len(driver.find_elements(*ITEMS))
btn.click()
wait.until(lambda d: len(d.find_elements(*ITEMS)) > before)
```
Loop until the count stops increasing or the button disappears; that replaces `while: click; sleep(3)`.

**Pagination / full page swap** — `staleness_of` on an anchor element from the old page:

```python
old = driver.find_element(By.CSS_SELECTOR, "#results")
driver.find_element(By.CSS_SELECTOR, ".next-page").click()
wait.until(EC.staleness_of(old))
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#results .product-card")))
```

Other useful ECs: `text_to_be_present_in_element`, `url_contains`, `number_of_windows_to_be`,
`all_of` / `any_of` / `none_of` (Selenium 4 combinators). Set
`driver.implicitly_wait(0)` — never mix implicit and explicit waits (documented as producing
unpredictable total timeouts).

## 4. Chrome options for scraping throughput

```python
def build_options():
    o = webdriver.ChromeOptions()
    o.add_argument("--headless=new")           # Chrome 109+ "new" headless == real Chrome
    o.add_argument("--disable-gpu")
    o.add_argument("--no-sandbox")             # needed in Docker/CI; weakens sandbox
    o.add_argument("--disable-dev-shm-usage")  # avoids /dev/shm exhaustion in containers
    o.add_argument("--window-size=1920,1080")  # headless default is 800x600 → lazy content hides
    o.add_argument("--blink-settings=imagesEnabled=false")
    o.add_argument("--disable-extensions")
    o.add_argument("--disable-notifications")
    o.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...")
    o.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    })
    o.page_load_strategy = "eager"             # fires on DOMContentLoaded, skips images/subresources
    return o
```

Trade-offs:
- `page_load_strategy="eager"` is the biggest cheap win, but SPA content still needs explicit waits;
  `"none"` is faster still and requires waits for *everything*.
- Blocking images breaks scrapers that need `img[src]` — if you extract image URLs, keep images
  disabled but read the attribute (the URL is in the DOM even when not fetched). Verify per site.
- Headless is detectable (`navigator.webdriver`, missing plugins, UA containing "HeadlessChrome" in
  old headless). `--headless=new` plus a real UA fixes the obvious tells; heavy anti-bot (Cloudflare,
  DataDome) still flags it — fall back to headful or undetected-chromedriver only if blocked.
- `--no-sandbox` on a dev macOS box is unnecessary; keep it only for Docker/root.

## 5. macOS `Status code was: -9`

-9 = the chromedriver process was killed with `SIGKILL` by macOS before it could speak. Two causes:
1. **Gatekeeper quarantine** on a driver downloaded by Python (webdriver-manager) rather than by a
   browser-signed installer: the unsigned/unnotarized binary is killed on exec.
   Fix: `xattr -d com.apple.quarantine <path>` (or `xattr -cr ~/.wdm`).
2. **webdriver-manager returning the wrong file** — historically it handed back
   `THIRD_PARTY_NOTICES.chromedriver` from the extracted zip; executing that dies immediately.

Selenium Manager avoids both: it downloads from the official Chrome-for-Testing endpoints into
`~/.cache/selenium`, sets the exec bit, and picks the real binary — so §2's recommendation also
removes the top macOS failure mode. (If it ever recurs: `rm -rf ~/.cache/selenium ~/.wdm`.)

## 6. Robust clicks & stale elements

```python
def safe_click(driver, el, wait):
    try:
        wait.until(EC.element_to_be_clickable(el)).click()
    except (ElementClickInterceptedException, ElementNotInteractableException):
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)   # bypasses overlays/cookie banners
```
JS click ignores overlays entirely — good for banners, bad because it can "succeed" on a hidden
element; prefer dismissing the consent overlay once per session first.

```python
def retry_stale(fn, attempts=3, delay=0.4):
    for i in range(attempts):
        try: return fn()
        except StaleElementReferenceException:
            if i == attempts - 1: raise
            time.sleep(delay)            # only legitimate sleep: backoff, not a wait
```
Better: never hold `WebElement` references across a navigation/re-render — re-find by locator, or
iterate `range(len(...))` and re-query each index.

## Unresolved questions

- Which target site(s)? Anti-bot posture decides headless vs headful and whether images can be
  blocked (some sites lazy-load prices via image-triggered IO observers).
- Is any per-task state (login/session cookies) required? That changes whether driver reuse needs a
  reset step between products.
- Actual `max_workers` ceiling depends on the machine's RAM and the site's rate limits — needs a
  measured run, not a guess.
- Does the pipeline need image binaries downloaded? If yes, do it with `requests`, not the browser.

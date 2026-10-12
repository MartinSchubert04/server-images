// Runtime half of the Athanor themes, listed under frontend.extra_module_url in configuration.yaml.
// A theme can only set CSS variables, so the parts of the portfolio that need markup or live data
// live here: the fonts, the NetHack status line, the brand of the sidebar and the hero card.
// Nothing shows unless an Athanor theme is the active one.

const VGA = '"PxPlus IBM VGA 8x16", "Cascadia Mono", Consolas, "Courier New", monospace'
const DISPLAY = '"Jacquard 24", "PxPlus IBM VGA 8x16", serif'
const THEMES = ["Athanor", "Athanor Umber", "Athanor Cinnabar"]
// Theme -> [palette when dark, palette when light]
const PALETTE = { Athanor: ["Srcery", "Vellum"], "Athanor Umber": ["Umber", "Vellum"], "Athanor Cinnabar": ["Cinnabar", "Orpiment"] }

// ----- Fonts. @font-face only registers at document level.
// PxPlus IBM VGA 8x16: The Ultimate Oldschool PC Font Pack by VileR (CC BY-SA 4.0). Jacquard 24: OFL.
if (!document.getElementById("athanor-fonts")) {
  const style = document.createElement("style")
  style.id = "athanor-fonts"
  style.textContent = `
@font-face {
  font-family: "PxPlus IBM VGA 8x16";
  src: url("/local/athanor/fonts/PxPlus_IBM_VGA_8x16.ttf") format("truetype");
  font-display: swap;
}
@font-face {
  font-family: "Jacquard 24";
  src: url("/local/athanor/fonts/jacquard-24-latin-400-normal.woff2") format("woff2");
  font-display: swap;
}`
  document.head.appendChild(style)
}

// ----- Home Assistant access
const app = () => document.querySelector("home-assistant")
const getHass = () => app()?.hass
const themeActive = () => getComputedStyle(document.documentElement).getPropertyValue("--athanor-ink").trim() !== ""

function findDeep(selector, root = document, depth = 6) {
  const hit = root.querySelector(selector)
  if (hit || depth === 0) return hit
  for (const el of root.querySelectorAll("*")) {
    if (el.shadowRoot) {
      const inner = findDeep(selector, el.shadowRoot, depth - 1)
      if (inner) return inner
    }
  }
  return null
}

function navigate(path) {
  history.pushState(null, "", path)
  window.dispatchEvent(new CustomEvent("location-changed"))
}

function setTheme(theme) {
  app()?.dispatchEvent(new CustomEvent("settheme", { detail: { theme }, bubbles: true, composed: true }))
}

function currentTheme(hass) {
  const name = hass?.themes?.theme
  return THEMES.includes(name) ? name : THEMES[0]
}

const paletteLabel = (hass) => PALETTE[currentTheme(hass)][hass?.themes?.darkMode === false ? 1 : 0]

/** Views of the dashboard on screen, with the index of the open one. */
function currentViews() {
  const [, panel, view] = location.pathname.split("/")
  const views = findDeep("ha-panel-lovelace")?.lovelace?.config?.views ?? []
  let index = views.findIndex((v) => v.path === view)
  if (index < 0) index = Number.isInteger(Number(view)) && view !== undefined ? Number(view) : 0
  return { panel, views, index: Math.min(Math.max(index, 0), Math.max(views.length - 1, 0)) }
}

// ----- Almanac, ported from the portfolio (src/lib/almanac.ts). Uses the location of the instance.
const CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
const DAY_RULER = [3, 6, 2, 5, 1, 4, 0]
const HOUR_MS = 3_600_000
const DAY_MS = 24 * HOUR_MS
const SYNODIC_DAYS = 29.530588853
const NEW_MOON_2000 = Date.UTC(2000, 0, 6, 18, 14)

const wallClock = (at) => new Date(at.getTime() - at.getTimezoneOffset() * 60_000)

function sunTimes(at, lat, lon) {
  const wall = wallClock(at)
  const midnight = Date.UTC(wall.getUTCFullYear(), wall.getUTCMonth(), wall.getUTCDate())
  const n = Math.floor((midnight - Date.UTC(wall.getUTCFullYear(), 0, 0)) / DAY_MS)
  const rad = Math.PI / 180
  const declination = -23.44 * Math.cos(((2 * Math.PI) / 365) * (n + 10)) * rad
  const x = -Math.tan(lat * rad) * Math.tan(declination)
  const hourAngle = Math.acos(Math.max(-1, Math.min(1, x))) / rad
  const b = (2 * Math.PI * (n - 81)) / 364
  const equationOfTime = 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b)
  const noonUtcHours = 12 - lon / 15 - equationOfTime / 60
  return {
    rise: new Date(midnight + (noonUtcHours - hourAngle / 15) * HOUR_MS),
    set: new Date(midnight + (noonUtcHours + hourAngle / 15) * HOUR_MS),
  }
}

/** The planetary day runs from sunrise to sunrise; each half is split into twelve unequal hours. */
function planetaryHour(now, lat, lon) {
  let sun = sunTimes(now, lat, lon)
  if (now < sun.rise) sun = sunTimes(new Date(now.getTime() - DAY_MS), lat, lon)
  const isDay = now < sun.set
  const daylight = sun.set - sun.rise
  const span = (isDay ? daylight : DAY_MS - daylight) / 12
  const index = Math.min(11, Math.floor((now - (isDay ? sun.rise : sun.set)) / span)) + (isDay ? 0 : 12)
  const ruler = DAY_RULER[wallClock(sun.rise).getUTCDay()]
  return { day: CHALDEAN[ruler], hour: CHALDEAN[(ruler + index) % 7] }
}

function moon(now) {
  const age = ((((now - NEW_MOON_2000) / DAY_MS) % SYNODIC_DAYS) + SYNODIC_DAYS) % SYNODIC_DAYS
  const phase =
    age < 1 || age > SYNODIC_DAYS - 1 ? "new" : Math.abs(age - SYNODIC_DAYS / 2) < 1 ? "full" : age < SYNODIC_DAYS / 2 ? "waxing" : "waning"
  return { ageDays: Math.floor(age), phase }
}

function moonLine(now) {
  const { ageDays, phase } = moon(now)
  return phase === "new" || phase === "full" ? `Moon ${phase}` : `Moon ${phase}, ${ageDays} days old`
}

const ordinalRules = new Intl.PluralRules("en", { type: "ordinal" })
const ORDINAL = { one: "st", two: "nd", few: "rd", other: "th" }

function longDate(now) {
  const parts = new Intl.DateTimeFormat("en", { weekday: "long", day: "numeric", month: "long" }).formatToParts(now)
  const get = (type) => parts.find((p) => p.type === type)?.value ?? ""
  const day = Number(get("day"))
  return `${get("weekday")}, the ${day}${ORDINAL[ordinalRules.select(day)]} of ${get("month")}`
}

function statusClock(now) {
  const parts = new Intl.DateTimeFormat("en", {
    weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(now)
  const get = (type) => parts.find((p) => p.type === type)?.value ?? ""
  return `${get("weekday")} ${get("day")} ${get("month")} ${get("hour")}:${get("minute")}`
}

// Major arcana with their Golden Dawn attributions
const ARCANA = [
  "0|The Fool|beginnings, a leap", "I|The Magician|will, craft", "II|The High Priestess|secrets, intuition",
  "III|The Empress|abundance", "IV|The Emperor|order, authority", "V|The Hierophant|tradition, teaching",
  "VI|The Lovers|choice, union", "VII|The Chariot|drive, victory", "VIII|Strength|courage, patience",
  "IX|The Hermit|solitude, search", "X|Wheel of Fortune|turning luck", "XI|Justice|balance, truth",
  "XII|The Hanged Man|surrender, a new view", "XIII|Death|endings, change", "XIV|Temperance|mixing, measure",
  "XV|The Devil|bondage, appetite", "XVI|The Tower|upheaval", "XVII|The Star|hope, renewal",
  "XVIII|The Moon|illusion, dreams", "XIX|The Sun|joy, clarity", "XX|Judgement|awakening", "XXI|The World|completion",
]

function fnv1a(text) {
  let hash = 0x811c9dc5
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i)
    hash = Math.imul(hash, 0x01000193)
  }
  return hash >>> 0
}

const today = (now) => wallClock(now).toISOString().slice(0, 10)

function cardOfTheDay(now) {
  const [numeral, name, meaning] = ARCANA[fnv1a(today(now)) % ARCANA.length].split("|")
  return { numeral, name, meaning }
}

/** Symmetric 5x5 identicon, as the host sigil of the terminal splash. Rows of booleans. */
function sigilCells(seed) {
  const bytes = Array.from({ length: 15 }, (_, i) => fnv1a(`${seed}:${i}`) & 0xff)
  return Array.from({ length: 5 }, (_, y) => [0, 1, 2, 1, 0].map((x) => (bytes[y * 3 + x] & 1) === 1))
}

function sigilSvg(seed) {
  const cells = sigilCells(seed)
    .flatMap((row, y) => row.map((inked, x) => (inked ? `<rect x="${8 + x * 12}" y="${8 + y * 12}" width="12" height="12"/>` : "")))
    .join("")
  return `<svg width="76" height="76" viewBox="0 0 76 76" shape-rendering="crispEdges" aria-hidden="true" fill="currentColor">
    <rect x="1" y="1" width="74" height="74" fill="none" stroke="currentColor" stroke-width="2"/>${cells}</svg>`
}

// ----- What the house is doing
const QUIET = new Set(["sensor", "sun", "weather", "number", "select", "text", "event", "update", "button", "image", "tts", "stt", "conversation"])

function census(hass) {
  const states = Object.values(hass?.states ?? {})
  const dead = states.filter((s) => s.state === "unavailable").length
  let latest
  for (const s of states) {
    if (QUIET.has(s.entity_id.split(".")[0]) || s.state === "unavailable" || s.state === "unknown") continue
    if (!latest || s.last_changed > latest.last_changed) latest = s
  }
  return { total: states.length, dead, automations: states.filter((s) => s.entity_id.startsWith("automation.") && s.state === "on").length, latest }
}

const escapeHtml = (text) => String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c])

// ----- Status line: the NetHack bar at the bottom of the portfolio
class AthanorStatus extends HTMLElement {
  connectedCallback() {
    this.attachShadow({ mode: "open" }).innerHTML = `
<style>
  :host {
    position: fixed; right: 0; bottom: 0; left: 0; z-index: 4; display: none; box-sizing: border-box;
    height: calc(34px + env(safe-area-inset-bottom)); padding: 0 16px env(safe-area-inset-bottom);
    align-items: center; gap: 16px; white-space: nowrap; overflow: hidden;
    background: var(--app-header-background-color); border-top: 2px solid var(--athanor-rule);
    color: var(--athanor-tan); font: 16px/32px ${VGA}; font-variant-numeric: tabular-nums; -webkit-font-smoothing: none;
  }
  :host([shown]) { display: flex; }
  b { font-weight: 400; color: var(--app-header-text-color); }
  .raven { min-width: 0; overflow: hidden; text-overflow: ellipsis; color: var(--athanor-dim); }
  .push { margin-left: auto; }
  button { all: unset; cursor: pointer; }
  button:hover, button:focus-visible { color: var(--app-header-text-color); }
  @media (max-width: 1023px) { .raven, .wide { display: none; } }
  @media (max-width: 639px) { .mid { display: none; } }
</style>
<span id="level"></span><span id="ents" class="mid"></span><span id="dead" class="mid"></span><span id="auto" class="wide"></span>
<span id="raven" class="raven"></span>
<button id="tint" class="push mid" title="Change the palette"></button><span id="clock"></span><span id="hour" class="mid"></span><span id="moon" class="mid"></span>`
    this.shadowRoot.getElementById("tint").addEventListener("click", () => {
      const hass = getHass()
      setTheme(THEMES[(THEMES.indexOf(currentTheme(hass)) + 1) % THEMES.length])
      setTimeout(() => this.tick(), 200)
    })
    this.tick()
    this.timer = setInterval(() => this.tick(), 1000)
  }

  disconnectedCallback() {
    clearInterval(this.timer)
  }

  set(id, html) {
    const el = this.shadowRoot.getElementById(id)
    if (el.innerHTML !== html) el.innerHTML = html
  }

  tick() {
    const hass = getHass()
    const { panel, views, index } = currentViews()
    const onDashboard = hass?.panels?.[panel]?.component_name === "lovelace"
    // The bar is a dashboard thing; settings pages keep their own floating buttons down there
    const shown = Boolean(hass) && themeActive() && onDashboard
    this.toggleAttribute("shown", shown)
    document.documentElement.style.setProperty("--athanor-status-height", shown ? "34px" : "0px")
    if (!hass || !themeActive()) return
    document.documentElement.style.setProperty("--athanor-brand", `"@ ${(hass.user?.name ?? "home").toLowerCase()}"`)
    if (!shown) return

    const sidebar = findDeep("ha-sidebar")?.getBoundingClientRect()
    this.style.left = sidebar && sidebar.width > 0 && sidebar.left >= 0 && innerWidth > 870 ? `${sidebar.right}px` : "0px"

    const now = new Date()
    const { total, dead, automations, latest } = census(hass)
    const title = views[index]?.title ?? hass.panels[panel]?.title ?? "Home"
    this.set("level", `Dlvl:${index + 1} <b>${escapeHtml(title)}</b>`)
    this.set("ents", `Ents:${total}`)
    this.set("dead", `Dead:${dead}`)
    this.set("auto", `Auto:${automations}`)
    this.set(
      "raven",
      latest ? `A raven arrives: <b>${escapeHtml(latest.attributes.friendly_name ?? latest.entity_id)}</b> is ${escapeHtml(latest.state)}` : "awaiting a raven…",
    )
    this.set("tint", `Tint:<b>${paletteLabel(hass)}</b>`)
    this.set("clock", statusClock(now))
    this.set("hour", `Hour of ${planetaryHour(now, hass.config.latitude, hass.config.longitude).hour}`)
    this.set("moon", `Moon: ${moon(now).phase}`)
  }
}


// ----- Hero card: the lock screen of the portfolio. Plate on the left, a rule, the text panel on the right.
const PLATES = [
  ["dore-satan-despair", "Gustave Doré, Paradise Lost, Satan in despair (1866)"],
  ["friedrich-wanderer", "Caspar David Friedrich, Wanderer above the Sea of Fog (c. 1818)"],
  ["dore-satan-angels", "Gustave Doré, Paradise Lost, Satan and the angels (1866)"],
  ["cabanel-fallen-angel", "Alexandre Cabanel, The Fallen Angel (1847)"],
  ["dore-satan-profile", "Gustave Doré, Paradise Lost, Satan on the rock (1866)"],
  ["blake-ancient-of-days", "William Blake, The Ancient of Days (1794)"],
  ["dore-satan-falls", "Gustave Doré, Paradise Lost, the fall of Satan (1866)"],
  ["dore-death-pale-horse", "Gustave Doré, Death on the Pale Horse (1865)"],
  ["dore-satan-rises", "Gustave Doré, Paradise Lost, Satan rises from the lake (1866)"],
  ["dore-angel-israelites", "Gustave Doré, An Angel Appears to the Israelites (1866)"],
]
const SEEN_KEY = "athanor:plates-seen"

/** Playlist shuffle: no plate repeats until all have been shown. */
function drawPlate() {
  let seen = []
  try {
    seen = JSON.parse(localStorage.getItem(SEEN_KEY) ?? "[]").filter((n) => Number.isInteger(n) && n >= 0 && n < PLATES.length)
  } catch {}
  let pool = PLATES.map((_, i) => i).filter((i) => !seen.includes(i))
  if (pool.length === 0) {
    const last = seen[seen.length - 1]
    seen = []
    pool = PLATES.map((_, i) => i).filter((i) => i !== last)
  }
  const pick = pool[Math.floor(Math.random() * pool.length)]
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify([...seen, pick]))
  } catch {}
  return pick
}

class AthanorHeroCard extends HTMLElement {
  setConfig(config) {
    this.config = config ?? {}
  }

  getCardSize() {
    return this.config?.compact ? 7 : 12
  }

  getGridOptions() {
    return { columns: "full" }
  }

  set hass(hass) {
    this._hass = hass
    if (!this.shadowRoot) this.build()
    this.update()
  }

  disconnectedCallback() {
    clearInterval(this.timer)
    this.timer = undefined
  }

  connectedCallback() {
    if (this.shadowRoot && !this.timer) this.timer = setInterval(() => this.update(), 30_000)
  }

  build() {
    this.plate = drawPlate()
    this.attachShadow({ mode: "open" }).innerHTML = `
<style>
  /* Outside an Athanor theme the card borrows the colors of whatever theme is active */
  :host {
    --ink: var(--athanor-ink, var(--primary-background-color));
    --rule: var(--athanor-rule, var(--divider-color));
    --dim: var(--athanor-dim, var(--secondary-text-color));
    --cream: var(--athanor-cream, var(--primary-text-color));
    --amber: var(--athanor-amber, var(--primary-color));
    --plate: var(--athanor-plate, var(--primary-text-color));
    --plate-ground: var(--athanor-plate-ground, transparent);
    display: block; container-type: inline-size; color: var(--cream); font: 16px/24px ${VGA}; -webkit-font-smoothing: none;
  }
  .hero {
    box-sizing: border-box; display: grid; align-items: center; gap: 32px 64px; max-width: 1280px; margin: 0 auto;
    padding: 32px 32px calc(48px + var(--athanor-status-height, 0px));
  }
  .rule { display: none; align-self: stretch; background: var(--rule); }
  @media (min-width: 1024px) {
    .hero { grid-template-columns: 512px 2px minmax(0, 1fr); min-height: calc(100dvh - var(--header-height, 56px)); }
    .rule { display: block; }
  }
  /* Compact: a masthead above other cards instead of a full page. Sized by its column, not the window */
  .hero.compact { min-height: 0; max-width: none; margin: 0; padding: 0 0 16px; grid-template-columns: minmax(0, 1fr); gap: 24px 40px; }
  .hero.compact .rule { display: none; }
  .hero.compact .frame { height: 256px; max-width: none; }
  .hero.compact h1 { font-size: 72px; }
  @container (min-width: 760px) {
    .hero.compact { grid-template-columns: 320px 2px minmax(0, 1fr); }
    .hero.compact .rule { display: block; }
    .hero.compact .frame { height: 400px; }
  }
  [hidden] { display: none !important; }
  figure { margin: 0; }
  /* The plate is shown at its natural size and cropped by its frame, never rescaled */
  .frame { position: relative; overflow: hidden; width: 100%; max-width: 512px; height: 256px; background: var(--plate-ground); cursor: pointer; }
  @media (min-width: 640px) { .frame { height: 480px; } }
  @media (min-width: 1024px) { .frame { height: min(640px, calc(100dvh - 224px)); } }
  .ink { position: absolute; inset: 0; background: var(--plate); image-rendering: pixelated;
    -webkit-mask: var(--src) center / auto no-repeat; mask: var(--src) center / auto no-repeat; }
  /* The terminal prints an image row by row; the cover slides away in the same steps */
  .cover { position: absolute; inset: 0; background: var(--ink); transform: translateY(100%); }
  @media (prefers-reduced-motion: no-preference) { .cover { animation: print 900ms steps(20, end) both; } }
  @keyframes print { from { transform: translateY(0); } to { transform: translateY(100%); } }
  figcaption { margin-top: 12px; color: var(--dim); }
  .text { display: flex; flex-direction: column; gap: 24px; min-width: 0; max-width: 592px; }
  .host { display: flex; align-items: center; gap: 16px; color: var(--dim); }
  .host svg { flex: none; color: var(--amber); }
  h1 { margin: 0; font: 400 72px/1 ${DISPLAY}; letter-spacing: 0; text-wrap: balance; }
  @media (min-width: 640px) { h1 { font-size: 96px; } }
  p { margin: 0; }
  .pitch { margin-top: 16px; max-width: 52ch; }
  .amber { color: var(--amber); }
  .dim { color: var(--dim); }
  /* Two concentric amber frames, as on the terminal lock screen */
  input {
    box-sizing: border-box; width: calc(100% - 8px); max-width: 384px; height: 44px; margin: 4px; padding: 0 12px;
    background: var(--ink); color: var(--cream); caret-color: var(--amber); font: inherit;
    border: 2px solid var(--amber); border-radius: 0; outline: none;
    box-shadow: 0 0 0 2px var(--ink), 0 0 0 4px var(--amber);
  }
  input::placeholder { color: var(--dim); opacity: 1; }
  input:focus-visible { border-color: var(--cream); box-shadow: 0 0 0 2px var(--ink), 0 0 0 4px var(--cream); }
  label { display: block; margin-bottom: 8px; }
  #reply { margin-top: 8px; min-height: 24px; color: var(--dim); }
  .figures { display: flex; flex-wrap: wrap; gap: 16px 48px; }
  .figures strong { display: block; font: 400 48px/1 ${DISPLAY}; color: var(--cream); font-variant-numeric: tabular-nums; }
  .figures span { color: var(--dim); }
</style>
<div class="hero" id="hero">
  <figure>
    <div class="frame" id="frame" title="Next plate"><div class="ink" id="ink"></div><div class="cover" id="cover"></div></div>
    <figcaption id="caption"></figcaption>
  </figure>
  <div class="rule"></div>
  <div class="text">
    <div class="host" id="hostline"><span id="sigil"></span><p id="host"></p></div>
    <div><h1 id="name" translate="no"></h1><p class="pitch" id="pitch"></p></div>
    <p><span id="date"></span><br /><span class="amber" id="hours"></span><br /><span class="dim" id="moon"></span><br /><span class="dim" id="card"></span></p>
    <form id="form">
      <label for="word"><span class="amber">@</span> <span id="who"></span>, speak the word:</label>
      <input id="word" autocomplete="off" spellcheck="false" placeholder="help…" />
      <p id="reply" aria-live="polite">Try “help”.</p>
    </form>
    <div class="figures" id="figures"></div>
  </div>
</div>`
    const root = this.shadowRoot
    root.getElementById("frame").addEventListener("click", () => this.nextPlate())
    root.getElementById("form").addEventListener("submit", (event) => {
      event.preventDefault()
      const input = root.getElementById("word")
      root.getElementById("reply").textContent = this.speak(input.value.trim().toLowerCase())
      input.value = ""
    })
    // compact, host and prompt are card options; a full page shows everything
    root.getElementById("hero").classList.toggle("compact", Boolean(this.config.compact))
    root.getElementById("hostline").hidden = this.config.host === false
    root.getElementById("form").hidden = this.config.prompt === false
    this.showPlate()
    if (!this.timer) this.timer = setInterval(() => this.update(), 30_000)
  }

  showPlate() {
    const [id, caption] = PLATES[this.plate]
    const root = this.shadowRoot
    root.getElementById("ink").style.setProperty("--src", `url("/local/athanor/plates/tan/${id}.png")`)
    root.getElementById("caption").textContent = caption
    // Restart the print-in animation
    const cover = root.getElementById("cover")
    cover.style.animation = "none"
    void cover.offsetWidth
    cover.style.animation = ""
  }

  nextPlate() {
    this.plate = drawPlate()
    this.showPlate()
    return PLATES[this.plate][1]
  }

  /** The prompt answers like a text adventure, and every answer does something real. */
  speak(word) {
    const hass = this._hass
    const { panel, views } = currentViews()
    const rooms = views.filter((v) => v.title).map((v, i) => ({ name: v.title.toLowerCase(), path: `/${panel}/${v.path ?? i}` }))
    const exits = Object.values(hass.panels)
      .filter((p) => p.title && p.url_path !== panel)
      .map((p) => ({ name: (hass.localize?.(`panel.${p.title}`) || p.title).toLowerCase(), path: `/${p.url_path}` }))
    if (!word) return "Silence. Try “help”."
    if (word === "help") return `Rooms: ${rooms.map((r) => r.name).join(", ")}. Also: exits, plate, tint, or a palette name.`
    if (word === "exits") return `Exits: ${exits.map((e) => e.name).join(", ")}.`
    if (word === "plate") return `A new plate: ${this.nextPlate()}.`
    if (word === "tint") {
      setTheme(THEMES[(THEMES.indexOf(currentTheme(hass)) + 1) % THEMES.length])
      return "The light changes."
    }
    const theme = THEMES.find((t) => PALETTE[t].some((p) => p.toLowerCase() === word))
    if (theme) {
      setTheme(theme)
      return `The room is re-inked in ${word}.`
    }
    const door = [...rooms, ...exits].find((d) => d.name === word) ?? [...rooms, ...exits].find((d) => d.name.startsWith(word))
    if (door) {
      navigate(door.path)
      return `You walk to ${door.name}.`
    }
    return `Nothing here answers to “${word}”.`
  }

  set(id, value, html = false) {
    const el = this.shadowRoot.getElementById(id)
    if (html ? el.innerHTML !== value : el.textContent !== value) el[html ? "innerHTML" : "textContent"] = value
  }

  update() {
    const hass = this._hass
    if (!hass || !this.shadowRoot) return
    const now = new Date()
    const { day, hour } = planetaryHour(now, hass.config.latitude, hass.config.longitude)
    const card = cardOfTheDay(now)
    const { total, dead, automations } = census(hass)
    const user = (hass.user?.name ?? "visitor").toLowerCase()
    this.set("sigil", sigilSvg(`${hass.config.location_name}:${today(now)}`), true)
    this.set("host", `${escapeHtml(user)}@${escapeHtml((hass.config.location_name ?? "home").toLowerCase())}<br />sigil of the day<br />core ${escapeHtml(hass.config.version)}`, true)
    this.set("name", this.config.name ?? hass.config.location_name ?? "Home")
    this.set("pitch", this.config.pitch ?? "A house that has been running in a scriptorium for a few centuries.")
    this.set("date", longDate(now))
    this.set("hours", `Day of ${day === "Sun" || day === "Moon" ? "the " : ""}${day}, hour of ${hour}`)
    this.set("moon", moonLine(now))
    this.set("card", `Card of the day: ${card.numeral}, ${card.name} (${card.meaning})`)
    this.set("who", user)
    this.set(
      "figures",
      [[total, "entities"], [total - dead, "awake"], [dead, "silent"], [automations, "automations"]]
        .map(([n, label]) => `<div><strong>${n}</strong><span>${label}</span></div>`)
        .join(""),
      true,
    )
  }
}

window.customCards = window.customCards ?? []
if (!window.customCards.some((c) => c.type === "athanor-hero-card")) {
  window.customCards.push({ type: "athanor-hero-card", name: "Athanor Hero", description: "Plate, sigil, almanac and prompt, as in the portfolio." })
}

// ----- Mount. Home Assistant swaps window.customElements for a scoped registry while it boots, and an
// element defined before the swap is unknown to the dashboards. So nothing is defined until the app is up.
function mount() {
  if (!getHass()) return setTimeout(mount, 100)
  if (!customElements.get("athanor-status")) customElements.define("athanor-status", AthanorStatus)
  if (!customElements.get("athanor-hero-card")) customElements.define("athanor-hero-card", AthanorHeroCard)
  if (!document.querySelector("athanor-status")) document.body.appendChild(document.createElement("athanor-status"))
}
mount()

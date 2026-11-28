#!/usr/bin/env python3
"""
Static documentation generator for kido.sh.

Reads Apple Metal Feature Set specifications from data/gpu/features.json
and per-board hardware records from data/gpu/boards/*.json, validates every
record, and generates completely self-contained static HTML pages.

Usage:
    python3 scripts/build-docs.py
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_GPU_DIR = ROOT / "data" / "gpu"
FEATURES_PATH = DATA_GPU_DIR / "features.json"
BOARDS_DIR = DATA_GPU_DIR / "boards"
DOCS_DIR = ROOT / "docs"

VALID_STATUSES = {"native", "software", "hw_ready", "emulatable", "hw_limit"}

BRAND_MARK_SVG = (
    '<svg class="brand-mark" viewBox="5.2 5.2 53.6 53.6" aria-hidden="true">'
    '<path class="bm-c" d="M32 13.6C35.5 13.6 38.0 12.8 40.2 10.9C42.6 8.9 44.8 6.6 46.7 6.9'
    'C48.4 7.2 49.4 9.2 49.7 13.0C50.1 16.5 50.2 20.0 51.0 23.8C51.8 27.4 51.5 31.4 50.2 34.8'
    'L13.8 34.8C12.5 31.4 12.2 27.4 13.0 23.8C13.8 20.0 13.9 16.5 14.3 13.0C14.6 9.2 15.6 7.2'
    ' 17.3 6.9C19.2 6.6 21.4 8.9 23.8 10.9C26.0 12.8 28.5 13.6 32 13.6Z"/>'
    '<ellipse class="bm-e" cx="23.8" cy="23.4" rx="3.55" ry="4.25"/>'
    '<ellipse class="bm-e" cx="40.2" cy="23.4" rx="3.55" ry="4.25"/>'
    '<circle class="bm-s" cx="22.4" cy="21.7" r="1.15"/>'
    '<circle class="bm-s" cx="38.8" cy="21.7" r="1.15"/>'
    '<path class="bm-n" d="M30.0 28.3C30.0 27.5 34.0 27.5 34.0 28.3C34.0 29.3 32.7 30.3 32.0 30.3'
    'C31.3 30.3 30.0 29.3 30.0 28.3Z"/>'
    '<path class="bm-b" d="M11.2 33.4L52.8 33.4C55.2 33.4 56.8 35.0 56.8 37.4L56.8 49.4'
    'C56.8 54.2 53.0 57.6 48.2 57.6L15.8 57.6C11.0 57.6 7.2 54.2 7.2 49.4L7.2 37.4'
    'C7.2 35.0 8.8 33.4 11.2 33.4Z"/>'
    '<rect class="bm-i" x="16.0" y="33.4" width="32.0" height="2.4" rx="1.2"/>'
    '<rect class="bm-r" x="11.6" y="34.8" width="40.8" height="2.0" rx="1.0"/>'
    '<rect class="bm-h" x="25.6" y="45.6" width="12.8" height="3.7" rx="1.85"/>'
    '<path class="bm-cr" d="M11.6 35.8A6.8 5.8 0 0 0 25.2 35.8Z"/>'
    '<path class="bm-cr" d="M38.8 35.8A6.8 5.8 0 0 0 52.4 35.8Z"/>'
    '<ellipse class="bm-p" cx="18.4" cy="35.3" rx="5.5" ry="4.3"/>'
    '<ellipse class="bm-p" cx="45.6" cy="35.3" rx="5.5" ry="4.3"/>'
    '<path class="bm-t" d="M16.7 36.1L16.7 38.9M20.1 36.1L20.1 38.9'
    'M43.9 36.1L43.9 38.9M47.3 36.1L47.3 38.9"/>'
    "</svg>"
)

THEME_INIT_SCRIPT = (
    '<script>!function(){try{var t=localStorage.getItem("kido-theme");'
    'if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}}()</script>'
)

THEME_TOGGLE_SCRIPT = """<script>(function(){
var b=document.getElementById("theme-toggle");if(!b)return;
var mq=window.matchMedia("(prefers-color-scheme: dark)");
function cur(){var d=document.documentElement.dataset.theme;return d==="light"||d==="dark"?d:(mq.matches?"dark":"light")}
function sync(){var isD=cur()==="dark";b.setAttribute("aria-pressed",String(isD));b.setAttribute("aria-label",isD?"Switch to light theme":"Switch to dark theme");b.title=isD?"Switch to light theme":"Switch to dark theme"}
b.addEventListener("click",function(){var next=cur()==="dark"?"light":"dark";document.documentElement.dataset.theme=next;try{localStorage.setItem("kido-theme",next)}catch(e){}sync()});
if(mq.addEventListener)mq.addEventListener("change",sync);
sync();
})();</script>"""

DOCS_CSS = """
:root{
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  --bg:#f8f6f2;--fg:#1c1917;--m:#68625b;--m2:#8a837a;--l:#e6e1d8;--ls:#d6cfc4;
  --c:#fff;--cs:#f5f2ec;--cb:#efeae2;
  --a:#d4941a;
  --ok:#1b7340;--sw:#9e6600;--hr:#2f5aa8;--em:#9a6b2f;--hl:#b23a29;
}
:root[data-theme=dark]{
  --bg:#090909;--fg:#ededeb;--m:#96928b;--m2:#6d6963;--l:#1f1f1d;--ls:#2c2c29;
  --c:#10100f;--cs:#141413;--cb:#191917;
  --a:#f8c446;
  --ok:#5ad28b;--sw:#f0b93c;--hr:#7ca7f5;--em:#d8a85a;--hl:#e86f5d;
}
@media(prefers-color-scheme:dark){
  :root:not([data-theme=light]){
    --bg:#090909;--fg:#ededeb;--m:#96928b;--m2:#6d6963;--l:#1f1f1d;--ls:#2c2c29;
    --c:#10100f;--cs:#141413;--cb:#191917;
    --a:#f8c446;
    --ok:#5ad28b;--sw:#f0b93c;--hr:#7ca7f5;--em:#d8a85a;--hl:#e86f5d;
  }
}
*,*::before,*::after{box-sizing:border-box}
html{background:var(--bg);overflow-x:clip}
body{
  margin:0;background:var(--bg);color:var(--fg);
  font-family:var(--sans);font-size:15px;line-height:1.6;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
}
a{color:var(--fg);text-decoration:underline;text-decoration-color:var(--ls);text-decoration-thickness:1px;text-underline-offset:3px;transition:color .15s,text-decoration-color .15s}
a:hover{text-decoration-color:var(--fg)}
header a,.docs-nav a,.breadcrumb a,.hw-row{text-decoration:none}
a:focus-visible,button:focus-visible{outline:1.5px solid var(--a);outline-offset:2px}
code,pre{font-family:var(--mono);font-size:12.5px}
.wrap{max-width:1240px;margin:0 auto;padding:0 24px}

/* Header */
header{padding:20px 0;display:flex;align-items:center;justify-content:space-between;gap:16px;border-bottom:1px solid var(--l)}
.brand{display:inline-flex;align-items:center;gap:10px;font-weight:650;font-size:19px;letter-spacing:-.025em;color:var(--fg)}
.brand-word em{font-style:normal;color:var(--fg)}
:root[data-theme=dark] .brand-word em{color:var(--a)}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]) .brand-word em{color:var(--a)}}
.brand-mark{width:30px;height:30px;display:block;flex-shrink:0}
.bm-c{fill:#23201e}.bm-e{fill:#f5b82e}.bm-s{fill:#fffcf2;opacity:.95}.bm-n{fill:#f0dec4}
.bm-b{fill:#d48c46}.bm-i{fill:#8e551e}.bm-r{fill:#fff8ef;opacity:.94}.bm-h{fill:#8a521d}
.bm-cr{fill:#fff8ef}.bm-p{fill:#23201e}.bm-t{fill:none;stroke:#f5e9d8;stroke-width:1.4;stroke-linecap:round}
:root[data-theme=dark] .brand-mark .bm-c{fill:#312c29;stroke:#8f8377;stroke-width:1.25;stroke-linejoin:round}
:root[data-theme=dark] .brand-mark .bm-e{fill:#f8c446}
:root[data-theme=dark] .brand-mark .bm-s{fill:#fffdf5}
:root[data-theme=dark] .brand-mark .bm-n{fill:#f3e3cb}
:root[data-theme=dark] .brand-mark .bm-b{fill:#e29a52}
:root[data-theme=dark] .brand-mark .bm-i{fill:#915720}
:root[data-theme=dark] .brand-mark .bm-h{fill:#8a521c}
:root[data-theme=dark] .brand-mark .bm-p{fill:#312c29}
:root[data-theme=dark] .brand-mark .bm-t{stroke:#f7ecdc}
@media(prefers-color-scheme:dark){
  :root:not([data-theme=light]) .brand-mark .bm-c{fill:#312c29;stroke:#8f8377;stroke-width:1.25;stroke-linejoin:round}
  :root:not([data-theme=light]) .brand-mark .bm-e{fill:#f8c446}
  :root:not([data-theme=light]) .brand-mark .bm-s{fill:#fffdf5}
  :root:not([data-theme=light]) .brand-mark .bm-n{fill:#f3e3cb}
  :root:not([data-theme=light]) .brand-mark .bm-b{fill:#e29a52}
  :root:not([data-theme=light]) .brand-mark .bm-i{fill:#915720}
  :root:not([data-theme=light]) .brand-mark .bm-h{fill:#8a521c}
  :root:not([data-theme=light]) .brand-mark .bm-p{fill:#312c29}
  :root:not([data-theme=light]) .brand-mark .bm-t{stroke:#f7ecdc}
}
nav{display:flex;align-items:center;gap:22px}
nav a{color:var(--m);font-size:14px;font-weight:450;transition:color .15s}
nav a:hover,nav a[aria-current=page]{color:var(--fg)}
nav a[aria-current=page]{font-weight:550}
.theme-btn{appearance:none;width:34px;height:34px;padding:0;border-radius:8px;background:transparent;border:1px solid var(--l);color:var(--m);display:inline-grid;place-items:center;cursor:pointer;transition:color .15s,border-color .15s,background-color .15s}
.theme-btn:hover{color:var(--fg);border-color:var(--ls);background:var(--cs)}
.theme-btn svg{grid-area:1/1;transition:opacity .15s,transform .2s}
.theme-btn .ic-sun{opacity:0;transform:scale(.85)}
.theme-btn .ic-moon{opacity:1;transform:scale(1)}
:root[data-theme=dark] .theme-btn .ic-sun{opacity:1;transform:scale(1);color:var(--fg)}
:root[data-theme=dark] .theme-btn .ic-moon{opacity:0;transform:scale(.85)}
@media(prefers-color-scheme:dark){
  :root:not([data-theme=light]) .theme-btn .ic-sun{opacity:1;transform:scale(1);color:var(--fg)}
  :root:not([data-theme=light]) .theme-btn .ic-moon{opacity:0;transform:scale(.85)}
}

/* Docs Layout */
.docs-layout{display:grid;grid-template-columns:212px minmax(0,1fr);gap:48px;padding:36px 0 72px;align-items:start}
.docs-sidebar{position:sticky;top:28px}
.docs-nav-label{font-size:11px;font-weight:550;text-transform:uppercase;letter-spacing:.07em;color:var(--m2);margin:0 0 10px 8px}
.docs-nav{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px}
.docs-nav a{display:block;padding:6px 8px;border-radius:6px;color:var(--m);font-size:13.5px;font-weight:450;transition:color .15s,background-color .15s}
.docs-nav a:hover{color:var(--fg);background:var(--cs)}
.docs-nav a.is-active{color:var(--fg);font-weight:550;background:var(--cs)}
.docs-nav-sub{padding-left:10px;margin:2px 0 0 10px;border-left:1px solid var(--l)}

.docs-main{min-width:0}
.breadcrumb{display:flex;align-items:center;flex-wrap:wrap;gap:6px;font-size:12.5px;color:var(--m2);margin-bottom:14px}
.breadcrumb a{color:var(--m)}
.breadcrumb a:hover{color:var(--fg)}
.breadcrumb .sep{opacity:.5}

h1{font-size:clamp(24px,2.8vw,32px);line-height:1.18;letter-spacing:-.03em;font-weight:600;margin:0 0 12px}
h2{font-size:17px;line-height:1.3;letter-spacing:-.015em;font-weight:550;margin:0 0 10px;color:var(--fg)}
.doc-lede{margin:0 0 24px;color:var(--m);font-size:15px;line-height:1.65;max-width:none;text-wrap:pretty;font-weight:400}
.inline-code{background:var(--cs);border:1px solid var(--l);border-radius:4px;padding:1px 5px;font-size:12.5px;color:var(--fg);white-space:nowrap}

/* Restrained inline legend strip */
.legend-strip{padding:12px 0;border-top:1px solid var(--l);border-bottom:1px solid var(--l);margin-bottom:18px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px 20px}
.legend-items{display:flex;align-items:center;flex-wrap:wrap;gap:8px 18px}
.legend-item{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--m);cursor:default}
.legend-ref{font-size:12px;color:var(--m2)}
.legend-ref a{color:var(--m)}

/* 5-state restrained status indicator */
.st{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:500;line-height:1.3;white-space:nowrap}
.st-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.st-native{color:var(--ok)}.st-native .st-dot{background:var(--ok)}
.st-software{color:var(--sw)}.st-software .st-dot{background:var(--sw)}
.st-hw_ready{color:var(--hr)}.st-hw_ready .st-dot{background:var(--hr)}
.st-emulatable{color:var(--em)}.st-emulatable .st-dot{background:transparent;border:1.4px solid var(--em)}
.st-hw_limit{color:var(--hl)}.st-hw_limit .st-dot{background:var(--hl)}

/* Flat target selector & board controls */
.toolbar{display:flex;flex-direction:column;gap:10px;margin-bottom:18px}
.toolbar-row{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px 16px}
.toolbar-group{display:flex;align-items:center;flex-wrap:wrap;gap:5px}
.toolbar-label{font-size:12px;color:var(--m2);margin-right:4px;white-space:nowrap;min-width:78px}

.chip-btn{appearance:none;display:inline-flex;align-items:center;gap:6px;padding:4px 9px;border-radius:6px;background:transparent;border:1px solid var(--l);color:var(--m);font-family:inherit;font-size:12px;font-weight:450;line-height:1.35;cursor:pointer;transition:color .15s,border-color .15s,background-color .15s}
.chip-btn:hover:not(:disabled){color:var(--fg);border-color:var(--ls);background:var(--cs)}
.chip-btn:disabled{opacity:.32;cursor:not-allowed}
.chip-btn.is-active{color:var(--fg);border-color:var(--fg);background:var(--cs);font-weight:550}
.chip-btn.is-board-on{color:var(--fg);border-color:var(--ls);background:var(--cs)}
.chip-btn.is-board-off{color:var(--m2);border-color:var(--l);background:transparent;opacity:.55;text-decoration:line-through}
.chip-dot{width:6px;height:6px;border-radius:50%;background:var(--ok);flex-shrink:0}
.chip-btn.is-board-off .chip-dot{background:var(--m2)}

.tool-action{appearance:none;display:inline-flex;align-items:center;padding:4px 10px;border-radius:6px;background:transparent;border:1px solid var(--l);color:var(--m);font-family:inherit;font-size:12px;font-weight:450;cursor:pointer;transition:color .15s,border-color .15s,background-color .15s}
.tool-action:hover{color:var(--fg);border-color:var(--ls);background:var(--cs)}
.tool-action.is-active{color:var(--fg);border-color:var(--fg);background:var(--cs);font-weight:550}

.target-note{font-size:12px;color:var(--m2);margin:0}

/* Hairline matrix table */
.matrix-shell{border:1px solid var(--l);border-radius:10px;background:var(--c);overflow:hidden;margin-bottom:32px}
.matrix-scroll{overflow:auto;max-height:min(78vh,860px);-webkit-overflow-scrolling:touch}
table.matrix{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;min-width:720px}
table.matrix col.col-feature{width:290px}
table.matrix col.col-board{width:285px}
table.matrix thead th{position:sticky;top:0;z-index:5;background:var(--cs);border-bottom:1px solid var(--ls);padding:13px 16px;text-align:left;vertical-align:middle}
table.matrix th.col-sticky,table.matrix td.col-sticky{position:sticky;left:0;z-index:4;background:var(--c);border-right:1px solid var(--l)}
table.matrix thead th.col-sticky{z-index:7;background:var(--cs);border-right:1px solid var(--ls)}

/* Minimal draggable board column header */
th.board-col{cursor:grab;user-select:none;transition:background-color .15s,box-shadow .15s,opacity .15s}
th.board-col:hover{background:var(--cb)}
th.board-col:active{cursor:grabbing}
th.board-col.is-dragging{opacity:.42}
th.board-col.drop-before{box-shadow:inset 2.5px 0 0 var(--fg)}
th.board-col.drop-after{box-shadow:inset -2.5px 0 0 var(--fg)}
th.board-col.is-hidden,td.is-hidden,col.is-hidden{display:none}

.bh-row{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.bh-id{display:flex;align-items:flex-start;gap:8px;min-width:0}
.bh-grip{color:var(--m2);margin-top:3px;flex-shrink:0;opacity:.55;transition:opacity .15s}
th.board-col:hover .bh-grip{opacity:1}
.bh-name{font-size:14.5px;font-weight:550;letter-spacing:-.015em;color:var(--fg);line-height:1.3;margin:0}
.bh-sub{font-family:var(--mono);font-size:11.5px;color:var(--m);margin-top:2px;font-weight:400}
.bh-moves{display:inline-flex;align-items:center;gap:3px;flex-shrink:0;opacity:.55;transition:opacity .15s}
th.board-col:hover .bh-moves,th.board-col:focus-within .bh-moves{opacity:1}
.col-move{appearance:none;width:22px;height:22px;padding:0;border-radius:5px;background:transparent;border:1px solid transparent;color:var(--m);display:inline-grid;place-items:center;cursor:pointer;transition:color .15s,border-color .15s,background-color .15s}
.col-move:hover:not(:disabled){color:var(--fg);border-color:var(--ls);background:var(--c)}
.col-move:disabled{opacity:.25;cursor:default}

.fh-title{font-size:12.5px;font-weight:550;color:var(--m);letter-spacing:.01em;margin:0}

/* Section banner rows */
tr.sec-row td{background:var(--cs);border-top:1px solid var(--l);border-bottom:1px solid var(--l);padding:8px 16px;font-size:11.5px;font-weight:550;color:var(--m);text-transform:uppercase;letter-spacing:.06em}
tr.sec-row:first-child td{border-top:0}
tr.sec-row.is-hidden,tr.feat-row.is-hidden{display:none}

/* Feature & value cells */
tr.feat-row td{padding:11px 16px;border-bottom:1px solid var(--l);vertical-align:top;transition:background-color .1s}
tr.feat-row:last-child td{border-bottom:0}
tr.feat-row:hover td,tr.feat-row:hover td.col-sticky{background:var(--cs)}
.f-name{font-size:13.5px;font-weight:500;color:var(--fg);line-height:1.35}
.f-ref{display:block;margin-top:2px;font-family:var(--mono);font-size:11px;color:var(--m2)}
.cell-top{display:flex;align-items:baseline;flex-wrap:wrap;gap:4px 10px;margin-bottom:3px}
.cell-val{font-family:var(--mono);font-size:12.5px;font-weight:500;color:var(--fg);line-height:1.35}
.cell-detail{font-size:12px;line-height:1.45;color:var(--m)}
.sum-grid{display:flex;flex-wrap:wrap;gap:5px 12px;font-size:12px;line-height:1.45}
.sum-sub{font-size:11.5px;color:var(--m);margin-top:4px}
.empty-diff{padding:28px 20px;text-align:center;color:var(--m);font-size:13.5px;display:none}
.empty-diff.is-visible{display:block}

/* Hardware hub list */
.hw-list{border-top:1px solid var(--l);margin:24px 0 40px}
.hw-row{display:flex;align-items:baseline;justify-content:space-between;gap:24px;padding:20px 4px;border-bottom:1px solid var(--l);color:var(--fg);transition:background-color .12s}
.hw-row:hover{background:var(--cs)}
.hw-row-title{font-size:16px;font-weight:550;letter-spacing:-.015em;margin:0 0 4px}
.hw-row-desc{margin:0;color:var(--m);font-size:14px;line-height:1.55;text-wrap:pretty}
.hw-row-arrow{font-size:14px;color:var(--m2);flex-shrink:0;transition:color .12s,transform .12s}
.hw-row:hover .hw-row-arrow{color:var(--fg);transform:translateX(2px)}

/* CPU page flat prose + hairline table */
.prose-block{padding:20px 0;border-top:1px solid var(--l);margin-bottom:24px;max-width:740px}
.prose-block p{margin:0 0 12px;color:var(--m);font-size:14.5px;line-height:1.65}
.prose-block p:last-child{margin-bottom:0}
table.simple{width:100%;border-collapse:collapse;font-size:13.5px}
table.simple th,table.simple td{text-align:left;padding:11px 16px;border-bottom:1px solid var(--l);vertical-align:top}
table.simple th{background:var(--cs);font-size:11.5px;font-weight:550;color:var(--m);text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--ls)}
table.simple tr:last-child td{border-bottom:0}
.tbl-title{font-weight:500;color:var(--fg)}
.tbl-sub{display:block;font-size:12px;color:var(--m2);margin-top:1px}

/* Footer & Legal Trademark Block */
footer{padding:24px 0 48px;border-top:1px solid var(--l);color:var(--m);font-size:13px;line-height:1.65}
footer p{margin:5px 0}
.trademarks{margin-top:14px;padding-top:14px;border-top:1px solid var(--l);font-size:11.5px;line-height:1.6;color:var(--m2)}
.trademarks p{margin:4px 0}

@media(max-width:960px){
  .docs-layout{grid-template-columns:minmax(0,1fr);gap:24px;padding:24px 0 56px}
  .docs-sidebar{position:static;padding-bottom:16px;border-bottom:1px solid var(--l)}
  .docs-nav{flex-direction:row;flex-wrap:wrap;gap:6px}
  .docs-nav-sub{display:flex;flex-wrap:wrap;gap:6px;border-left:0;margin:0;padding:0}
  .docs-nav-label{margin:0 0 8px 0}
  table.matrix col.col-feature{width:220px}
  table.matrix col.col-board{width:255px}
}
@media(max-width:640px){
  .wrap{padding:0 16px}
  header{padding:16px 0}
  nav{gap:14px}
  .toolbar-label{min-width:auto}
  .hw-row{flex-direction:column;gap:8px;padding:16px 2px}
  table.matrix col.col-feature{width:195px}
  table.matrix col.col-board{width:240px}
}
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none !important;transition:none !important;scroll-behavior:auto !important}
}
""".strip()


MATRIX_JS = """<script>(function(){
var tbl=document.getElementById("gpu-matrix");
if(!tbl)return;
var colgroup=tbl.querySelector("colgroup");
var headRow=tbl.querySelector("thead tr");
var tbody=tbl.querySelector("tbody");
var apiChipsWrap=document.getElementById("api-chips");
var famChipsWrap=document.getElementById("family-chips");
var boardChipsWrap=document.getElementById("board-chips");
var gapsBtn=document.getElementById("toggle-gaps");
var diffBtn=document.getElementById("toggle-diff");
var resetBtn=document.getElementById("reset-matrix");
var emptyDiff=document.getElementById("empty-diff");
var targetNote=document.getElementById("target-note");

var STATUS_LABEL={
  native:"Native",
  software:"Software",
  hw_ready:"HW Ready",
  emulatable:"Emulatable",
  hw_limit:"HW Limit"
};

var initialOrder=Array.from(headRow.querySelectorAll("th.board-col")).map(function(th){return th.dataset.boardId});
var order=initialOrder.slice();
var hidden=new Set();
var activeApi="all";
var activeFamily=0;
var gapsOnly=false;
var diffOnly=false;
var dragId=null;

function applyColumnOrder(){
  var cols=Array.from(colgroup.querySelectorAll("col.col-board"));
  var ths=Array.from(headRow.querySelectorAll("th.board-col"));
  var colById={},thById={};
  cols.forEach(function(c){colById[c.dataset.boardId]=c});
  ths.forEach(function(t){thById[t.dataset.boardId]=t});
  order.forEach(function(id){
    if(colById[id])colgroup.appendChild(colById[id]);
    if(thById[id])headRow.appendChild(thById[id]);
  });
  tbody.querySelectorAll("tr.feat-row").forEach(function(tr){
    var tdById={};
    tr.querySelectorAll("td.board-cell").forEach(function(td){tdById[td.dataset.boardId]=td});
    order.forEach(function(id){if(tdById[id])tr.appendChild(tdById[id])});
  });
  if(boardChipsWrap){
    var chipById={};
    boardChipsWrap.querySelectorAll("button[data-board-id]").forEach(function(b){chipById[b.dataset.boardId]=b});
    order.forEach(function(id){if(chipById[id])boardChipsWrap.appendChild(chipById[id])});
  }
  syncAll();
}

function setCellStatus(td,statusKey){
  td.dataset.effStatus=statusKey;
  var stEl=td.querySelector(".st");
  if(!stEl)return;
  stEl.className="st st-"+statusKey;
  var txt=stEl.querySelector(".st-txt");
  if(txt)txt.textContent=STATUS_LABEL[statusKey]||statusKey;
}

function syncFamilyButtons(){
  if(!famChipsWrap)return;
  famChipsWrap.querySelectorAll("button[data-family]").forEach(function(btn){
    var f=parseInt(btn.dataset.family,10);
    var dis=(activeApi==="metal4" && f>0 && f<7);
    btn.disabled=dis;
    var on=(f===activeFamily);
    btn.classList.toggle("is-active",on);
    btn.setAttribute("aria-pressed",String(on));
  });
  if(apiChipsWrap){
    apiChipsWrap.querySelectorAll("button[data-api]").forEach(function(btn){
      var on=(btn.dataset.api===activeApi);
      btn.classList.toggle("is-active",on);
      btn.setAttribute("aria-pressed",String(on));
    });
  }
  if(targetNote){
    if(activeApi==="all" && activeFamily===0){
      targetNote.textContent="Showing all Apple Metal 3 and Metal 4 requirements across Apple2 to Apple11.";
    }else{
      var apiTxt=(activeApi==="metal4")?"Metal 4":(activeApi==="metal3")?"Metal 3":"Metal 3 and Metal 4";
      var famTxt=(activeFamily>0)?("Apple"+activeFamily+" (cumulative from Apple2)"):"all Apple families";
      targetNote.textContent="Target filter: "+apiTxt+" on "+famTxt+".";
    }
  }
}

function syncAll(){
  syncFamilyButtons();
  var visibleOrder=order.filter(function(id){return !hidden.has(id)});
  var visCount=visibleOrder.length;

  colgroup.querySelectorAll("col.col-board").forEach(function(c){
    c.classList.toggle("is-hidden",hidden.has(c.dataset.boardId));
  });
  headRow.querySelectorAll("th.board-col").forEach(function(th){
    var id=th.dataset.boardId;
    var isHid=hidden.has(id);
    th.classList.toggle("is-hidden",isHid);
    var pos=visibleOrder.indexOf(id);
    var leftBtn=th.querySelector(".col-move-left");
    var rightBtn=th.querySelector(".col-move-right");
    if(leftBtn)leftBtn.disabled=(pos<=0);
    if(rightBtn)rightBtn.disabled=(pos<0||pos>=visCount-1);
  });
  tbody.querySelectorAll("td.board-cell").forEach(function(td){
    td.classList.toggle("is-hidden",hidden.has(td.dataset.boardId));
  });
  tbody.querySelectorAll("tr.sec-row td").forEach(function(td){
    td.colSpan=1+Math.max(1,visCount);
  });
  if(boardChipsWrap){
    boardChipsWrap.querySelectorAll("button[data-board-id]").forEach(function(b){
      var isOff=hidden.has(b.dataset.boardId);
      b.classList.toggle("is-board-on",!isOff);
      b.classList.toggle("is-board-off",isOff);
      b.setAttribute("aria-pressed",String(!isOff));
    });
  }

  /* Dynamic evaluation of threshold limits and Apple target matching */
  var evalFamily=(activeFamily>0)?activeFamily:0;
  var counts={};
  order.forEach(function(id){
    counts[id]={native:0,software:0,hw_ready:0,emulatable:0,hw_limit:0,total:0};
  });

  var shownRows=0;
  var secVisibleCounts={};
  var allRows=Array.from(tbody.querySelectorAll("tr.feat-row"));

  /* Pass 1: evaluate Apple spec rows and accumulate per-board target readiness counts */
  allRows.forEach(function(tr){
    var sec=tr.dataset.section;
    var kind=tr.dataset.kind||"spec";
    if(kind!=="spec")return;

    var minA=parseInt(tr.dataset.minApple||"2",10);
    var models=(tr.dataset.models||"").split(",");
    var apiMatch=(activeApi==="all")||(models.indexOf(activeApi)>=0);
    var famMatch=(activeFamily===0)||(minA<=activeFamily);
    var inTarget=apiMatch && famMatch;

    if(tr.dataset.thresholds){
      var thMap=JSON.parse(tr.dataset.thresholds);
      var unit=tr.dataset.unit||"";
      var refEl=tr.querySelector(".f-ref");
      var reqVal=(evalFamily>0)?thMap[String(evalFamily)]:null;
      if(refEl){
        refEl.textContent=(reqVal!==null && reqVal!==undefined)
          ?("Required at Apple"+evalFamily+": "+reqVal.toLocaleString("en-US")+unit)
          :(tr.dataset.defaultRef||"");
      }
      tr.querySelectorAll("td.board-cell").forEach(function(td){
        var baseSt=td.dataset.status;
        if(reqVal!==null && reqVal!==undefined && td.dataset.numeric!==""){
          var num=parseFloat(td.dataset.numeric);
          var eff=(num>=reqVal)?(td.dataset.passStatus||baseSt):(td.dataset.failStatus||"hw_limit");
          setCellStatus(td,eff);
        }else{
          setCellStatus(td,baseSt);
        }
      });
    }

    if(inTarget){
      tr.querySelectorAll("td.board-cell").forEach(function(td){
        var bid=td.dataset.boardId;
        var st=td.dataset.effStatus||td.dataset.status;
        if(counts[bid] && counts[bid][st]!==undefined){
          counts[bid][st]++;
          counts[bid].total++;
        }
      });
    }

    var hasGap=false;
    var vals=[];
    visibleOrder.forEach(function(id){
      var td=tr.querySelector('td.board-cell[data-board-id="'+id+'"]');
      if(td){
        var st=td.dataset.effStatus||td.dataset.status;
        if(st!=="native" && st!=="software")hasGap=true;
        vals.push(st+"|"+(td.dataset.value||""));
      }
    });
    var differs=vals.length>1 && vals.some(function(v){return v!==vals[0]});
    var show=inTarget && (!gapsOnly||hasGap) && (!diffOnly||differs);
    tr.classList.toggle("is-hidden",!show);
    if(show){
      shownRows++;
      secVisibleCounts[sec]=(secVisibleCounts[sec]||0)+1;
    }
  });

  /* Pass 2: render Target Match summary and filter Status / Runtime rows */
  allRows.forEach(function(tr){
    var sec=tr.dataset.section;
    var kind=tr.dataset.kind||"spec";
    if(kind==="spec")return;

    if(kind==="computed_summary"){
      var refS=tr.querySelector(".f-ref");
      if(refS){
        var aLbl=(activeApi==="metal4")?"Metal 4":(activeApi==="metal3")?"Metal 3":"All Metal APIs";
        var fLbl=(activeFamily>0)?("Apple"+activeFamily):"Apple2 to Apple11";
        refS.textContent=aLbl+", "+fLbl;
      }
      tr.querySelectorAll("td.board-cell").forEach(function(td){
        var bid=td.dataset.boardId;
        var c=counts[bid];
        var box=td.querySelector(".sum-grid");
        var sub=td.querySelector(".sum-sub");
        if(box && c){
          box.textContent="";
          var items=[
            ["native",(c.native+c.software)+" working"],
            ["hw_ready",c.hw_ready+" HW ready"],
            ["emulatable",c.emulatable+" emulatable"],
            ["hw_limit",c.hw_limit+" HW limit"]
          ];
          items.forEach(function(pair){
            var sp=document.createElement("span");
            sp.className="st st-"+pair[0];
            var dot=document.createElement("span");
            dot.className="st-dot";
            dot.setAttribute("aria-hidden","true");
            sp.appendChild(dot);
            sp.appendChild(document.createTextNode(pair[1]));
            box.appendChild(sp);
          });
          if(sub){
            var doable=c.native+c.software+c.hw_ready+c.emulatable;
            sub.textContent=doable+" of "+c.total+" target requirements achievable ("+c.native+" native, "+c.software+" software today)";
          }
        }
      });
      tr.classList.remove("is-hidden");
      shownRows++;
      secVisibleCounts[sec]=(secVisibleCounts[sec]||0)+1;
      return;
    }

    var vals2=[];
    visibleOrder.forEach(function(id){
      var td=tr.querySelector('td.board-cell[data-board-id="'+id+'"]');
      if(td)vals2.push((td.dataset.status||"")+"|"+(td.dataset.value||""));
    });
    var differs2=vals2.length>1 && vals2.some(function(v){return v!==vals2[0]});
    var showMeta=(kind==="meta")
      ?(!diffOnly||differs2)
      :(!gapsOnly && (!diffOnly||differs2));
    tr.classList.toggle("is-hidden",!showMeta);
    if(showMeta){
      shownRows++;
      secVisibleCounts[sec]=(secVisibleCounts[sec]||0)+1;
    }
  });

  tbody.querySelectorAll("tr.sec-row").forEach(function(tr){
    var sec=tr.dataset.section;
    tr.classList.toggle("is-hidden",!secVisibleCounts[sec]);
  });
  if(emptyDiff)emptyDiff.classList.toggle("is-visible",shownRows===0);
}

function moveVisibleBoard(id,delta){
  var vis=order.filter(function(x){return !hidden.has(x)});
  var vi=vis.indexOf(id);
  var targetVi=vi+delta;
  if(vi<0||targetVi<0||targetVi>=vis.length)return;
  var swapId=vis[targetVi];
  var ai=order.indexOf(id),bi=order.indexOf(swapId);
  var tmp=order[ai];order[ai]=order[bi];order[bi]=tmp;
  applyColumnOrder();
}

function clearDropHints(){
  headRow.querySelectorAll("th.board-col").forEach(function(th){
    th.classList.remove("is-dragging","drop-before","drop-after");
  });
}

headRow.querySelectorAll("th.board-col").forEach(function(th){
  var id=th.dataset.boardId;
  var l=th.querySelector(".col-move-left");
  var r=th.querySelector(".col-move-right");
  if(l)l.addEventListener("click",function(e){e.stopPropagation();moveVisibleBoard(id,-1)});
  if(r)r.addEventListener("click",function(e){e.stopPropagation();moveVisibleBoard(id,1)});

  th.addEventListener("dragstart",function(e){
    dragId=id;
    th.classList.add("is-dragging");
    e.dataTransfer.effectAllowed="move";
    try{e.dataTransfer.setData("text/plain",id)}catch(err){}
  });
  th.addEventListener("dragend",function(){dragId=null;clearDropHints()});
  th.addEventListener("dragover",function(e){
    if(!dragId||dragId===id)return;
    e.preventDefault();
    e.dataTransfer.dropEffect="move";
    var rect=th.getBoundingClientRect();
    var after=(e.clientX-rect.left)>rect.width/2;
    clearDropHints();
    var src=headRow.querySelector('th.board-col[data-board-id="'+dragId+'"]');
    if(src)src.classList.add("is-dragging");
    th.classList.add(after?"drop-after":"drop-before");
  });
  th.addEventListener("dragleave",function(){th.classList.remove("drop-before","drop-after")});
  th.addEventListener("drop",function(e){
    if(!dragId||dragId===id)return;
    e.preventDefault();
    var rect=th.getBoundingClientRect();
    var after=(e.clientX-rect.left)>rect.width/2;
    var fromIdx=order.indexOf(dragId);
    if(fromIdx<0){clearDropHints();return}
    order.splice(fromIdx,1);
    var toIdx=order.indexOf(id);
    if(after)toIdx++;
    order.splice(toIdx,0,dragId);
    dragId=null;
    clearDropHints();
    applyColumnOrder();
  });
});

if(apiChipsWrap){
  apiChipsWrap.querySelectorAll("button[data-api]").forEach(function(btn){
    btn.addEventListener("click",function(){
      activeApi=btn.dataset.api;
      if(activeApi==="metal4" && activeFamily>0 && activeFamily<7){
        activeFamily=7;
      }
      syncAll();
    });
  });
}

if(famChipsWrap){
  famChipsWrap.querySelectorAll("button[data-family]").forEach(function(btn){
    btn.addEventListener("click",function(){
      if(btn.disabled)return;
      activeFamily=parseInt(btn.dataset.family,10);
      syncAll();
    });
  });
}

if(boardChipsWrap){
  boardChipsWrap.querySelectorAll("button[data-board-id]").forEach(function(btn){
    btn.addEventListener("click",function(){
      var id=btn.dataset.boardId;
      if(hidden.has(id)){
        hidden.delete(id);
      }else{
        var visibleCount=order.filter(function(x){return !hidden.has(x)}).length;
        if(visibleCount<=1)return;
        hidden.add(id);
      }
      syncAll();
    });
  });
}

if(gapsBtn){
  gapsBtn.addEventListener("click",function(){
    gapsOnly=!gapsOnly;
    gapsBtn.classList.toggle("is-active",gapsOnly);
    gapsBtn.setAttribute("aria-pressed",String(gapsOnly));
    syncAll();
  });
}

if(diffBtn){
  diffBtn.addEventListener("click",function(){
    diffOnly=!diffOnly;
    diffBtn.classList.toggle("is-active",diffOnly);
    diffBtn.setAttribute("aria-pressed",String(diffOnly));
    syncAll();
  });
}

if(resetBtn){
  resetBtn.addEventListener("click",function(){
    order=initialOrder.slice();
    hidden.clear();
    activeApi="all";
    activeFamily=0;
    gapsOnly=false;
    diffOnly=false;
    if(gapsBtn){gapsBtn.classList.remove("is-active");gapsBtn.setAttribute("aria-pressed","false")}
    if(diffBtn){diffBtn.classList.remove("is-active");diffBtn.setAttribute("aria-pressed","false")}
    applyColumnOrder();
  });
}

syncAll();
})();</script>"""


def esc(val: Any) -> str:
    return html.escape(str(val), quote=True)


def load_and_validate() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not FEATURES_PATH.is_file():
        sys.exit(f"error: missing {FEATURES_PATH}")
    features = json.loads(FEATURES_PATH.read_text(encoding="utf-8"))

    row_ids: set[str] = set()
    computed_ids: set[str] = set()
    for sec in features.get("sections", []):
        for row in sec.get("rows", []):
            rid = row["id"]
            if rid in row_ids or rid in computed_ids:
                sys.exit(f"error: duplicate feature row id '{rid}' in features.json")
            if row.get("kind") == "computed_summary":
                computed_ids.add(rid)
            else:
                row_ids.add(rid)

    board_paths = sorted(BOARDS_DIR.glob("*.json"))
    if not board_paths:
        sys.exit(f"error: no board JSON files found in {BOARDS_DIR}")

    boards: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    required_board_fields = [
        "id",
        "name",
        "subtitle",
        "gpu",
        "cpu",
        "arch",
        "driver",
        "kernel",
        "verification",
        "capabilities",
    ]
    for path in board_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in required_board_fields:
            if field not in data:
                sys.exit(f"error: {path.name} missing required field '{field}'")
        bid = data["id"]
        if bid in seen_ids:
            sys.exit(f"error: duplicate board id '{bid}' in {path.name}")
        seen_ids.add(bid)

        caps = data["capabilities"]
        for rid in row_ids:
            if rid not in caps:
                sys.exit(f"error: {path.name} missing capability '{rid}'")
            entry = caps[rid]
            st = entry.get("status")
            if st not in VALID_STATUSES:
                sys.exit(
                    f"error: {path.name} capability '{rid}' has invalid status '{st}'"
                )
            if not entry.get("value"):
                sys.exit(f"error: {path.name} capability '{rid}' missing 'value'")
            for k in ("pass_status", "fail_status"):
                if k in entry and entry[k] not in VALID_STATUSES:
                    sys.exit(
                        f"error: {path.name} capability '{rid}' has invalid {k} '{entry[k]}'"
                    )
        for extra_id in caps:
            if extra_id not in row_ids:
                sys.exit(
                    f"error: {path.name} contains unknown capability '{extra_id}' not in features.json"
                )
        data["_filename"] = path.name
        boards.append(data)

    boards.sort(key=lambda b: (b.get("order", 999), b["name"].lower()))
    return features, boards


def collect_trademarks(
    features: dict[str, Any], boards: list[dict[str, Any]]
) -> list[str]:
    notices: list[str] = []
    seen: set[str] = set()
    for line in features.get("core_trademarks", []):
        if line not in seen:
            seen.add(line)
            notices.append(line)
    for b in boards:
        for line in b.get("trademarks", []):
            if line not in seen:
                seen.add(line)
                notices.append(line)
    return notices


def render_shell(
    *,
    title: str,
    description: str,
    canonical_path: str,
    active_nav: str,
    main_html: str,
    trademarks: list[str],
    extra_scripts: str = "",
) -> str:
    sidebar_html = f"""<aside class="docs-sidebar" aria-label="Documentation">
<p class="docs-nav-label">Documentation</p>
<ul class="docs-nav">
<li>
<a href="/docs/linux-hardware/" class="{'is-active' if active_nav == 'linux-hardware' else ''}">Supported Linux Hardware</a>
<ul class="docs-nav docs-nav-sub">
<li><a href="/docs/linux-hardware/cpu/" class="{'is-active' if active_nav == 'cpu' else ''}">CPU</a></li>
<li><a href="/docs/linux-hardware/gpu/" class="{'is-active' if active_nav == 'gpu' else ''}">GPU</a></li>
</ul>
</li>
</ul>
</aside>"""

    tm_joined = " ".join(esc(t) for t in trademarks)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://kido.sh{esc(canonical_path)}">
<meta property="og:site_name" content="kido">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="https://kido.sh{esc(canonical_path)}">
<meta property="og:type" content="website">
<meta property="og:image" content="https://kido.sh/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="https://kido.sh/og-image.png">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f8f6f2" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#090909" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
{THEME_INIT_SCRIPT}
<style>{DOCS_CSS}</style>
</head>
<body>
<div class="wrap">
<header>
<a class="brand" href="/">
{BRAND_MARK_SVG}
<span class="brand-word">ki<em>do</em></span>
</a>
<nav aria-label="Primary">
<a href="/">Home</a>
<a href="/docs/linux-hardware/" aria-current="page">Docs</a>
<a href="https://github.com/kido-sh/kido">GitHub</a>
<button type="button" class="theme-btn" id="theme-toggle" aria-label="Switch color theme" title="Switch light / dark theme"><svg class="ic-moon" width="15" height="15" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M16.2 12.6A6.8 6.8 0 0 1 7.4 3.8a6.8 6.8 0 1 0 8.8 8.8Z" stroke="currentColor" stroke-width="1.65" stroke-linejoin="round"/></svg><svg class="ic-sun" width="15" height="15" viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="10" cy="10" r="3.4" stroke="currentColor" stroke-width="1.65"/><path d="M10 2.4v2M10 15.6v2M2.4 10h2M15.6 10h2M4.6 4.6l1.4 1.4M14 14l1.4 1.4M15.4 4.6 14 6M6 14l-1.4 1.4" stroke="currentColor" stroke-width="1.65" stroke-linecap="round"/></svg></button>
</nav>
</header>
<div class="docs-layout">
{sidebar_html}
<main class="docs-main">
{main_html}
</main>
</div>
<footer>
<p>kido is open source under the Apache License 2.0.</p>
<div class="trademarks">
<p>Trademark notices: {tm_joined} All other trademarks, product names, and trade names are the property of their respective owners.</p>
<p>Hardware, silicon, and driver names appear strictly for technical identification and interoperability documentation. kido is an independent open-source project and is not affiliated with, endorsed by, or sponsored by any of the above entities.</p>
</div>
</footer>
</div>
{extra_scripts}
{THEME_TOGGLE_SCRIPT}
</body>
</html>
"""


def compute_static_counts(
    features: dict[str, Any], board: dict[str, Any]
) -> dict[str, int]:
    c = {"native": 0, "software": 0, "hw_ready": 0, "emulatable": 0, "hw_limit": 0, "total": 0}
    caps = board["capabilities"]
    for sec in features["sections"]:
        for row in sec["rows"]:
            if row.get("kind") in ("meta", "computed_summary", "runtime"):
                continue
            st = caps[row["id"]]["status"]
            c[st] += 1
            c["total"] += 1
    return c


def render_gpu_page(
    features: dict[str, Any], boards: list[dict[str, Any]], trademarks: list[str]
) -> str:
    ref = features["apple_reference"]
    statuses = features["statuses"]
    families = features.get("apple_families", [2, 3, 4, 5, 6, 7, 8, 9, 10, 11])

    legend_items: list[str] = []
    for key in ["native", "software", "hw_ready", "emulatable", "hw_limit"]:
        st = statuses[key]
        legend_items.append(
            f'<span class="legend-item" title="{esc(st["description"])}">'
            f'<span class="st st-{key}"><span class="st-dot" aria-hidden="true"></span>{esc(st["label"])}</span>'
            "</span>"
        )

    api_chips = (
        '<button type="button" class="chip-btn is-active" data-api="all" aria-pressed="true">All</button>'
        '<button type="button" class="chip-btn" data-api="metal3" aria-pressed="false">Metal 3</button>'
        '<button type="button" class="chip-btn" data-api="metal4" aria-pressed="false">Metal 4</button>'
    )

    fam_chips_list = [
        '<button type="button" class="chip-btn is-active" data-family="0" aria-pressed="true">All</button>'
    ]
    for fam in families:
        fam_chips_list.append(
            f'<button type="button" class="chip-btn" data-family="{fam}" aria-pressed="false">Apple{fam}</button>'
        )
    fam_chips = "".join(fam_chips_list)

    board_chips = "".join(
        f'<button type="button" class="chip-btn is-board-on" data-board-id="{esc(b["id"])}" '
        f'aria-pressed="true"><span class="chip-dot" aria-hidden="true"></span>'
        f'{esc(b["name"])}</button>'
        for b in boards
    )

    cols_html = ['<col class="col-feature">']
    for b in boards:
        cols_html.append(f'<col class="col-board" data-board-id="{esc(b["id"])}">')

    th_cells = [
        '<th scope="col" class="col-sticky"><p class="fh-title">Apple Specification</p></th>'
    ]
    for b in boards:
        bid = esc(b["id"])
        th_cells.append(
            f'<th scope="col" class="board-col" data-board-id="{bid}" draggable="true">'
            '<div class="bh-row">'
            '<div class="bh-id">'
            '<span class="bh-grip" aria-hidden="true">'
            '<svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor">'
            '<circle cx="3" cy="2.5" r="1"/><circle cx="7" cy="2.5" r="1"/>'
            '<circle cx="3" cy="6" r="1"/><circle cx="7" cy="6" r="1"/>'
            '<circle cx="3" cy="9.5" r="1"/><circle cx="7" cy="9.5" r="1"/>'
            "</svg></span>"
            "<div>"
            f'<p class="bh-name">{esc(b["name"])}</p>'
            f'<div class="bh-sub">{esc(b["subtitle"])}</div>'
            "</div>"
            "</div>"
            '<span class="bh-moves">'
            f'<button type="button" class="col-move col-move-left" aria-label="Move {esc(b["name"])} column left" title="Move left">'
            '<svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M8.5 3.2 4.7 7l3.8 3.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            "</button>"
            f'<button type="button" class="col-move col-move-right" aria-label="Move {esc(b["name"])} column right" title="Move right">'
            '<svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M5.5 3.2 9.3 7l-3.8 3.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            "</button>"
            "</span>"
            "</div>"
            "</th>"
        )

    static_counts = {b["id"]: compute_static_counts(features, b) for b in boards}

    body_rows: list[str] = []
    total_cols = 1 + len(boards)
    for sec in features["sections"]:
        sid = esc(sec["id"])
        body_rows.append(
            f'<tr class="sec-row" data-section="{sid}">'
            f'<td colspan="{total_cols}">{esc(sec["title"])}</td>'
            "</tr>"
        )
        for row in sec["rows"]:
            rid = row["id"]
            kind = row.get("kind", "spec")
            row_attrs = [
                f'class="feat-row"',
                f'data-section="{sid}"',
                f'data-row-id="{esc(rid)}"',
                f'data-kind="{esc(kind)}"',
            ]
            if kind == "spec":
                row_attrs.append(f'data-min-apple="{int(row["min_apple"])}"')
                row_attrs.append(
                    f'data-models="{esc(",".join(row.get("metal_models", [])))}"'
                )
                if "thresholds" in row:
                    row_attrs.append(
                        f'data-thresholds="{esc(json.dumps(row["thresholds"]))}"'
                    )
                    row_attrs.append(f'data-unit="{esc(row.get("unit", ""))}"')
                    row_attrs.append(f'data-default-ref="{esc(row["apple_ref"])}"')

            tds = [
                f'<td class="col-sticky">'
                f'<div class="f-name">{esc(row["name"])}</div>'
                f'<span class="f-ref">{esc(row["apple_ref"])}</span>'
                f"</td>"
            ]

            if kind == "computed_summary":
                for b in boards:
                    c = static_counts[b["id"]]
                    doable = c["native"] + c["software"] + c["hw_ready"] + c["emulatable"]
                    tds.append(
                        f'<td class="board-cell" data-board-id="{esc(b["id"])}">'
                        '<div class="sum-grid">'
                        f'<span class="st st-native"><span class="st-dot" aria-hidden="true"></span>{c["native"] + c["software"]} working</span>'
                        f'<span class="st st-hw_ready"><span class="st-dot" aria-hidden="true"></span>{c["hw_ready"]} HW ready</span>'
                        f'<span class="st st-emulatable"><span class="st-dot" aria-hidden="true"></span>{c["emulatable"]} emulatable</span>'
                        f'<span class="st st-hw_limit"><span class="st-dot" aria-hidden="true"></span>{c["hw_limit"]} HW limit</span>'
                        "</div>"
                        f'<div class="sum-sub">{doable} of {c["total"]} target requirements achievable ({c["native"]} native, {c["software"]} software today)</div>'
                        "</td>"
                    )
            else:
                for b in boards:
                    cap = b["capabilities"][rid]
                    st_key = cap["status"]
                    st_label = statuses[st_key]["label"]
                    detail_html = (
                        f'<div class="cell-detail">{esc(cap["detail"])}</div>'
                        if cap.get("detail")
                        else ""
                    )
                    if rid == "verification_status":
                        top_html = (
                            '<div class="cell-top">'
                            f'<span class="st st-{st_key}"><span class="st-dot" aria-hidden="true"></span>'
                            f'<span class="st-txt">{esc(cap["value"])}</span></span>'
                            "</div>"
                        )
                    elif kind == "meta":
                        top_html = (
                            '<div class="cell-top">'
                            f'<span class="cell-val">{esc(cap["value"])}</span>'
                            "</div>"
                        )
                    else:
                        top_html = (
                            '<div class="cell-top">'
                            f'<span class="st st-{st_key}"><span class="st-dot" aria-hidden="true"></span>'
                            f'<span class="st-txt">{esc(st_label)}</span></span>'
                            f'<span class="cell-val">{esc(cap["value"])}</span>'
                            "</div>"
                        )

                    td_attrs = [
                        'class="board-cell"',
                        f'data-board-id="{esc(b["id"])}"',
                        f'data-status="{esc(st_key)}"',
                        f'data-eff-status="{esc(st_key)}"',
                        f'data-value="{esc(cap["value"])}"',
                        f'data-numeric="{esc(cap["numeric"]) if "numeric" in cap else ""}"',
                    ]
                    if "pass_status" in cap:
                        td_attrs.append(f'data-pass-status="{esc(cap["pass_status"])}"')
                    if "fail_status" in cap:
                        td_attrs.append(f'data-fail-status="{esc(cap["fail_status"])}"')

                    tds.append(f"<td {' '.join(td_attrs)}>{top_html}{detail_html}</td>")

            body_rows.append(f"<tr {' '.join(row_attrs)}>" + "".join(tds) + "</tr>")

    main_html = f"""<nav class="breadcrumb" aria-label="Breadcrumb">
<a href="/docs/linux-hardware/">Documentation</a>
<span class="sep" aria-hidden="true">/</span>
<a href="/docs/linux-hardware/">Supported Linux Hardware</a>
<span class="sep" aria-hidden="true">/</span>
<span>GPU</span>
</nav>
<h1>GPU</h1>
<p class="doc-lede">Evaluate ARM64 Linux GPUs against Apple's Metal API levels and GPU families inside KidoDarwin micro-VMs over <code class="inline-code">virtio-metal</code> and host Vulkan. Select a target API level and Apple GPU family below to inspect what works today, what the silicon can support later, what can be software-emulated, and where hardware limits apply.</p>

<div class="legend-strip" aria-label="Support legend">
<div class="legend-items">{"".join(legend_items)}</div>
<span class="legend-ref">Reference: <a href="{esc(ref["url"])}" rel="noopener">{esc(ref["title"])}</a></span>
</div>

<div class="toolbar" aria-label="Target specification and board controls">
<div class="toolbar-row">
<div class="toolbar-group" id="api-chips" role="group" aria-label="Target Metal API level">
<span class="toolbar-label">Metal API</span>
{api_chips}
</div>
<div class="toolbar-group">
<button type="button" class="tool-action" id="toggle-gaps" aria-pressed="false">Gaps only</button>
<button type="button" class="tool-action" id="toggle-diff" aria-pressed="false">Differences only</button>
<button type="button" class="tool-action" id="reset-matrix">Reset</button>
</div>
</div>
<div class="toolbar-row">
<div class="toolbar-group" id="family-chips" role="group" aria-label="Target Apple GPU family">
<span class="toolbar-label">Apple Family</span>
{fam_chips}
</div>
</div>
<div class="toolbar-row">
<div class="toolbar-group" id="board-chips" role="group" aria-label="Hardware columns">
<span class="toolbar-label">Boards</span>
{board_chips}
</div>
<p class="target-note" id="target-note">Showing all Apple Metal 3 and Metal 4 requirements across Apple2 to Apple11.</p>
</div>
</div>

<div class="matrix-shell">
<div class="matrix-scroll">
<table class="matrix" id="gpu-matrix">
<colgroup>{"".join(cols_html)}</colgroup>
<thead>
<tr>{"".join(th_cells)}</tr>
</thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
</div>
<div class="empty-diff" id="empty-diff">No rows match the current filter.</div>
</div>"""

    return render_shell(
        title="GPU: Supported Linux Hardware | kido",
        description="Evaluate ARM64 Linux GPUs against Apple Metal API levels and Apple GPU families in kido Darwin micro-VMs.",
        canonical_path="/docs/linux-hardware/gpu/",
        active_nav="gpu",
        main_html=main_html,
        trademarks=trademarks,
        extra_scripts=MATRIX_JS,
    )


def render_cpu_page(
    boards: list[dict[str, Any]], trademarks: list[str]
) -> str:
    rows_html = []
    for b in boards:
        ver_status = b["verification"]["status"]
        ver_cls = "st-native" if ver_status.lower() == "verified" else "st-hw_ready"
        rows_html.append(
            "<tr>"
            f'<td><span class="tbl-title">{esc(b["name"])}</span><span class="tbl-sub">{esc(b["vendor"])}</span></td>'
            f'<td><code>{esc(b["cpu"])}</code></td>'
            f'<td><code>{esc(b["arch"])}</code></td>'
            f'<td>{esc(b["kernel"])}</td>'
            f'<td><span class="st {ver_cls}"><span class="st-dot" aria-hidden="true"></span>{esc(ver_status)}</span></td>'
            "</tr>"
        )

    main_html = f"""<nav class="breadcrumb" aria-label="Breadcrumb">
<a href="/docs/linux-hardware/">Documentation</a>
<span class="sep" aria-hidden="true">/</span>
<a href="/docs/linux-hardware/">Supported Linux Hardware</a>
<span class="sep" aria-hidden="true">/</span>
<span>CPU</span>
</nav>
<h1>CPU</h1>
<p class="doc-lede">CPU-only KidoDarwin micro-VMs on ARM64 Linux require hardware virtualization (<code class="inline-code">/dev/kvm</code>) and do not require a supported GPU. For Metal acceleration, see <a href="/docs/linux-hardware/gpu/">GPU</a>.</p>

<div class="prose-block">
<h2>Requirements</h2>
<p>kido boots Darwin guests on ARM64 Linux through its Rust KVM VMM (<code class="inline-code">kido-vmm</code>). Hosts must expose <code class="inline-code">/dev/kvm</code> at EL2 with GICv2 or GICv3 interrupt controller support.</p>
<p>On hybrid big.LITTLE SoCs such as RK3588, <code class="inline-code">kido-vmm</code> automatically pins guest vCPUs to a homogeneous performance cluster so XNU observes uniform MIDR and cache geometry across cores.</p>
</div>

<div class="matrix-shell">
<div class="matrix-scroll">
<table class="simple">
<thead>
<tr>
<th>Board / SoC</th>
<th>CPU Topology</th>
<th>Architecture</th>
<th>Kernel</th>
<th>Status</th>
</tr>
</thead>
<tbody>
{"".join(rows_html)}
</tbody>
</table>
</div>
</div>"""

    return render_shell(
        title="CPU: Supported Linux Hardware | kido",
        description="Verified ARM64 Linux CPU and KVM platforms for kido Darwin micro-VMs.",
        canonical_path="/docs/linux-hardware/cpu/",
        active_nav="cpu",
        main_html=main_html,
        trademarks=trademarks,
    )


def render_hardware_hub(trademarks: list[str]) -> str:
    main_html = """<nav class="breadcrumb" aria-label="Breadcrumb">
<span>Documentation</span>
<span class="sep" aria-hidden="true">/</span>
<span>Supported Linux Hardware</span>
</nav>
<h1>Supported Linux Hardware</h1>
<p class="doc-lede">Verified ARM64 Linux hosts for running KidoDarwin micro-VMs via KVM and optional host Vulkan GPU acceleration.</p>

<div class="hw-list">
<a class="hw-row" href="/docs/linux-hardware/cpu/">
<div>
<p class="hw-row-title">CPU</p>
<p class="hw-row-desc">KVM, ARMv8/ARMv9, GICv2/GICv3, and hybrid big.LITTLE support for Darwin micro-VMs.</p>
</div>
<span class="hw-row-arrow" aria-hidden="true">&rarr;</span>
</a>
<a class="hw-row" href="/docs/linux-hardware/gpu/">
<div>
<p class="hw-row-title">GPU</p>
<p class="hw-row-desc">Apple Metal API level and GPU family capability matrix for ARM64 Linux GPUs.</p>
</div>
<span class="hw-row-arrow" aria-hidden="true">&rarr;</span>
</a>
</div>"""

    return render_shell(
        title="Supported Linux Hardware | kido",
        description="Verified ARM64 Linux CPU and GPU support for kido Darwin micro-VMs.",
        canonical_path="/docs/linux-hardware/",
        active_nav="linux-hardware",
        main_html=main_html,
        trademarks=trademarks,
    )


def render_docs_redirect() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=/docs/linux-hardware/">
<link rel="canonical" href="https://kido.sh/docs/linux-hardware/">
<title>kido Documentation</title>
</head>
<body>
<p>Redirecting to <a href="/docs/linux-hardware/">Supported Linux Hardware</a>...</p>
</body>
</html>
"""


def write_page(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    features, boards = load_and_validate()
    trademarks = collect_trademarks(features, boards)

    write_page(DOCS_DIR / "index.html", render_docs_redirect())
    write_page(
        DOCS_DIR / "linux-hardware" / "index.html",
        render_hardware_hub(trademarks),
    )
    write_page(
        DOCS_DIR / "linux-hardware" / "cpu" / "index.html",
        render_cpu_page(boards, trademarks),
    )
    write_page(
        DOCS_DIR / "linux-hardware" / "gpu" / "index.html",
        render_gpu_page(features, boards, trademarks),
    )

    print(
        f"build-docs: validated {len(boards)} boards "
        f"({', '.join(b['id'] for b in boards)}) and generated static docs under docs/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Proof pictures of the map's chrome on the simulated client: each scenario drives the sim (tools/tests/wowsim.lua)
to a state and renders its frames to SVG and PNG with wowproof (wow-ui-testing's renderer: fetched by
scripts/fetch-wut.sh at the commit .wut-version pins into the gitignored .wut/, never committed or shipped here, as it's
PolyForm Noncommercial and MagicMap GPLv3), then a contact sheet of them all.

    .venv/bin/python tools/proof.py                  # every scenario: .proof/<name>.svg, .png, .proof/index.html
    .venv/bin/python tools/proof.py questlog         # scenarios whose name holds the text
    WUT_DIR=~/src/wow-ui-testing .venv/bin/python tools/proof.py     # a local checkout of the library instead of .wut/

Blizzard's art renders for real: Interface\\ paths come from Gethe/wow-ui-textures (the ref clientdata/forever.json
pins), client FileDataIDs (the minimap tiles, the atlas sheets) from wago.tools' CASC at the pinned build, decoded with
ImageMagick, and atlases through tools/proof/atlases.lua (the names this addon uses, pinned to the build). Downloads
cache in the gitignored .proof-art/ (never commit it). What's still a dashed box is a name or file those can't resolve.

    MM_PROOF_GROUND=0     leave the ground (the minimap tiles) out: fast, and the layout alone
    MM_PROOF_ART=DIR      the art cache (default .proof-art/)
    MM_PROOF_ART_FETCH=0  offline: only what's cached (GH_TOKEN/GITHUB_TOKEN, when set, spare GitHub's rate limit)
    .venv/bin/python tools/proof.py --atlases    # regenerates tools/proof/atlases.lua (see tools/proof_atlases.py)

PNGs need rsvg-convert. Exits 1 if a scenario failed or the library couldn't be fetched (2).
"""
import os
import re
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(TOOLS, "tests"))
sys.path.insert(0, TOOLS)

import wut  # noqa: E402
from test_questdetails import DETAILS  # noqa: E402
from test_questlog import row  # noqa: E402
from test_quests import CANDLES, FRONTIER, GOLD, LOVERS, client  # noqa: E402

ROOT = os.path.dirname(TOOLS)
OUT = os.path.join(ROOT, ".proof")
ART = os.environ.get("MM_PROOF_ART") or os.path.join(ROOT, ".proof-art")
ATLASES = os.path.join(TOOLS, "proof", "atlases.lua")

ART_SCRIPT = """
package.path = arg[1] .. "/?.lua;" .. arg[1] .. "/?/init.lua;" .. package.path
local fetch = arg[4] == "1"
local art = require("wowproof.sources.wow_ui_textures")({ ref = arg[2], dir = arg[3], fetch = fetch,
	token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") })
local files = require("wowproof.sources.wago_casc")({ build = arg[5], dir = arg[3], fetch = fetch })
local file = tonumber(arg[6]) or arg[6]
io.write(art(file) or files(file) or "")
"""


def art_ref(lib):
    with open(os.path.join(lib, "clientdata", "forever.json"), encoding="utf-8") as f:
        return re.search(r'"art"\s*:\s*{\s*"ref"\s*:\s*"(\w+)"', f.read()).group(1)


def blizzard_art(lib, fetch):
    """Interface\\ path or FileDataID -> PNG path or None, by the library's wow_ui_textures then wago_casc. They shell
    out (curl, ImageMagick) and wago_casc decodes BLPs with LuaJIT's ffi: neither works in the sim's Lua 5.1 (lupa), so
    each is resolved by the library itself in a luajit process (cached on disk: a download only once)."""
    luajit = shutil.which("luajit")
    ref, build, cache = art_ref(lib), atlas_build(), {}

    def resolve(file):
        if not luajit or not isinstance(file, (int, float, str)):
            return None
        key = str(int(file)) if isinstance(file, (int, float)) else file
        if key not in cache:
            run = subprocess.run([luajit, "-", lib, ref, ART, "1" if fetch else "0", build, key], input=ART_SCRIPT,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            cache[key] = run.stdout.strip() or None if run.returncode == 0 else None
        return cache[key]

    return resolve


def atlas_build():
    with open(ATLASES, encoding="utf-8") as f:
        return re.search(r'build = "([\d.]+)"', f.read()).group(1)


PROOF = """
local Sim, ns, wowproofDir, adapterPath, outDir, atlasPath, ground, art = ...
package.path = wowproofDir .. "/?.lua;" .. wowproofDir .. "/?/init.lua;" .. package.path
local Proof = require("wowproof")
local atlases = dofile(atlasPath)
local skipped = {}
if not ground then
	for _, layer in ipairs(ns.UI.Engine.layers) do
		if layer.zoom == "scale" then
			for _, c in ipairs({ layer.front, layer.back }) do if c then skipped[c] = true end end
		end
	end
end
local function Skip(r) return skipped[r] == true end
return Proof.New({ adapter = dofile(adapterPath)(Sim, { skip = Skip }), outDir = outDir, title = "MagicMap proof",
	assets = { fonts = { default = "DejaVu Sans" },
		textures = art,
		atlases = require("wowproof.sources.atlas_table")(atlases.atlases) } })
"""

QUESTS = [FRONTIER, CANDLES, GOLD, LOVERS]


def setup():
    """A client on the quest test's log, two zones of it, one followed and one tracked."""
    L, sim, ns, G = client(QUESTS, followed=60)
    L.execute("""local Sim = ...
        Sim.quests[106].header = "Westfall"
        Sim.quests[840] = { title = "Conscript of the Horde", level = 10, map = 1411, x = 0.5, y = 0.5, complete = false,
            header = "Durotar", objectives = { { text = "Speak to Kargal", type = "event", finished = false } } }
        Sim.watches[47] = true
        RAID_CLASS_COLORS.WARRIOR = { r = 0.78, g = 0.61, b = 0.43 }
        RAID_CLASS_COLORS.PRIEST = { r = 1, g = 1, b = 1 }
        RAID_CLASS_COLORS.SHAMAN = { r = 0, g = 0.44, b = 0.87 }
        local p = Sim.player
        Sim.units.party1 = { name = "Brannock", class = "WARRIOR", level = 9, guid = "Player-1-00000002", col = p.col + 0.16, row = p.row + 0.1 }
        Sim.units.party2 = { name = "Elandra", class = "PRIEST", level = 8, guid = "Player-1-00000003", col = p.col - 0.18, row = p.row + 0.06 }
        Sim.units.party3 = { name = "Thrall", class = "SHAMAN", level = 10, guid = "Player-1-00000004", col = p.col + 0.1, row = p.row - 0.15 }
        Sim.group = { "party1", "party2", "party3" }""", sim)
    L.execute(DETAILS, sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    return L, sim, ns


def grow(sim):
    sim.Press("M")
    sim.Run(1)


def scenarios(L, sim, ns):
    """(name, how to get there, what to render, options): in order, each from where the last left the sim."""
    UI = ns.UI
    f, panel = UI.Window.frame, UI.QuestLog.panel

    def ping():
        r = L.eval("function() return C_Minimap.GetViewRadius() end")()
        per_yard = (L.eval("function() return Minimap:GetWidth() end")() / 2) / r if r and r > 0 else 1
        sim.FireEvent("MINIMAP_PING", "party3", 30 * per_yard, 20 * per_yard)
        sim.Run(0.4)

    def details():
        sim.Click(row(ns, "[7] Kobold Candles"))
        sim.Run(0.5)

    def back():
        sim.Click(UI.QuestDetails.back)
        sim.Run(0.3)

    def pin():
        sim.Click(UI.MapPin.button)
        sim.Run(0.2)

    def kalimdor():
        drop = UI.MapPicker.drop
        sim.FireScript(drop, "OnMouseDown", "LeftButton")
        sim.Pick(next(e for e in sim.menu["items"].values() if e.text == "Kalimdor"))
        sim.Run(1)

    def fold():
        UI.Feel.Set("questlog.sidebar", True)
        sim.Run(0.2)
        header = next(r for r in UI.QuestLog.rows.values() if r.IsShown(r) and r.text.GetText(r.text) == "Elwynn Forest")
        sim.Click(header)

    def off():
        UI.Feel.Set("questlog.sidebar", False)
        sim.Run(0.2)

    return [
        ("small map", lambda: None, f, {"pad": 30}),
        ("small map: a party member's ping", ping, f, {"pad": 30}),
        ("big map with the quest log", lambda: grow(sim), f, {"pad": 30}),
        ("quest log panel", lambda: None, panel, {"pad": 8}),
        ("quest details: Kobold Candles", details, panel, {"pad": 8}),
        ("big map: quest details, Map Pin armed", pin, f, {"pad": 30}),
        ("quest log: back from the details", lambda: (pin(), back()), panel, {"pad": 8}),
        ("big map: Kalimdor from the Maps dropdown", kalimdor, f, {"pad": 30}),
        ("quest log: Elwynn folded", fold, panel, {"pad": 8}),
        ("big map, quest log off", off, f, {"pad": 30}),
    ]


def main(filters):
    if filters == ["--atlases"]:
        import proof_atlases
        return proof_atlases.generate(os.path.join(ART, "atlas-exports"))
    lib = wut.library("wowproof/init.lua")
    if not lib:
        print("wowproof not found: scripts/fetch-wut.sh couldn't fetch wow-ui-testing (or WUT_DIR has no wowproof/)")
        return 2
    L, sim, ns = setup()
    fetch = os.environ.get("MM_PROOF_ART_FETCH") != "0"
    proof = L.execute(PROOF, sim, ns, lib, os.path.join(TOOLS, "proof", "wowsim.lua"), OUT, ATLASES,
                      os.environ.get("MM_PROOF_GROUND") != "0", blizzard_art(lib, fetch))
    failed = 0
    for name, go, region, options in scenarios(L, sim, ns):
        go()
        if filters and not any(f in name for f in filters):
            continue
        try:
            entry = proof.Snapshot(proof, region, name, L.table_from(options))
            print(f"  ok   {name:<45} {entry.png or entry.svg}")
        except Exception as e:  # noqa: BLE001 (a failed render is listed, the rest still run)
            failed += 1
            proof.Fail(proof, name, str(e))
            print(f"  FAIL {name}\n    {e}")
    print(f"{failed} failed: {proof.Sheet(proof)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

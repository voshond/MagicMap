"""Proof pictures of the map's chrome on the simulated client: each scenario drives the sim (tools/tests/wowsim.lua)
to a state and renders its frames to SVG and PNG with wowproof (wow-ui-testing's renderer: fetched by
scripts/fetch-wut.sh at the commit .wut-version pins into the gitignored .wut/, never committed or shipped here, as it's
PolyForm Noncommercial and MagicMap GPLv3), then a contact sheet of them all.

    .venv/bin/python tools/proof.py                  # every scenario: .proof/<name>.svg, .png, .proof/index.html
    .venv/bin/python tools/proof.py questlog         # scenarios whose name holds the text
    WUT_DIR=~/src/wow-ui-testing .venv/bin/python tools/proof.py     # a local checkout of the library instead of .wut/

The ground (the minimap tiles: the client's own art) and Blizzard's atlases aren't in a render's reach: the tiles are
left out, an atlas is a dashed box named after it. What the pictures prove is the layout: what shows where, its
text and its colours. PNGs need rsvg-convert. Exits 1 if a scenario failed or the library couldn't be fetched (2).
"""
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(TOOLS, "tests"))
sys.path.insert(0, TOOLS)

from test_quests import CANDLES, FRONTIER, GOLD, LOVERS, client  # noqa: E402

ROOT = os.path.dirname(TOOLS)
OUT = os.path.join(ROOT, ".proof")
FETCH = os.path.join(ROOT, "scripts", "fetch-wut.sh")

PROOF = """
local Sim, ns, wowproofDir, adapterPath, outDir = ...
package.path = wowproofDir .. "/?.lua;" .. wowproofDir .. "/?/init.lua;" .. package.path
local Proof = require("wowproof")
-- The ground left out: the tiles (FileDataIDs of the client's), the base picture and the sea under them.
local ground = {}
for _, layer in ipairs(ns.UI.Engine.layers) do
	if layer.zoom == "scale" then
		for _, c in ipairs({ layer.front, layer.back }) do if c then ground[c] = true end end
	end
end
local function Skip(r) return ground[r] == true end
return Proof.New({ adapter = dofile(adapterPath)(Sim, { skip = Skip }), outDir = outDir, title = "MagicMap proof",
	assets = { fonts = { default = "DejaVu Sans" } } })
"""

QUESTS = [FRONTIER, CANDLES, GOLD, LOVERS]


def setup():
    """A client on the quest test's log, two zones of it, one followed and one tracked."""
    L, sim, ns, G = client(QUESTS, followed=60)
    L.execute("""local Sim = ...
        Sim.quests[106].header = "Westfall"
        Sim.quests[840] = { title = "Conscript of the Horde", level = 10, map = 1411, x = 0.5, y = 0.5, complete = false,
            header = "Durotar", objectives = { { text = "Speak to Kargal", type = "event", finished = false } } }
        Sim.watches[47] = true""", sim)
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
        ("big map with the quest log", lambda: grow(sim), f, {"pad": 30}),
        ("quest log panel", lambda: None, panel, {"pad": 8}),
        ("big map: Kalimdor from the Maps dropdown", kalimdor, f, {"pad": 30}),
        ("quest log: Elwynn folded", fold, panel, {"pad": 8}),
        ("big map, quest log off", off, f, {"pad": 30}),
    ]


def library():
    """wow-ui-testing's folder: .wut/ at the pinned commit (fetched when it isn't there yet), or WUT_DIR's."""
    run = subprocess.run(["bash", FETCH, ROOT], stdout=subprocess.PIPE, text=True)
    lib = run.stdout.strip().splitlines()[-1] if run.returncode == 0 and run.stdout.strip() else None
    return lib if lib and os.path.exists(os.path.join(lib, "wowproof", "init.lua")) else None


def main(filters):
    lib = library()
    if not lib:
        print("wowproof not found: scripts/fetch-wut.sh couldn't fetch wow-ui-testing (or WUT_DIR has no wowproof/)")
        return 2
    L, sim, ns = setup()
    proof = L.execute(PROOF, sim, ns, lib, os.path.join(TOOLS, "proof", "wowsim.lua"), OUT)
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

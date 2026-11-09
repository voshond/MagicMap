"""The big map's quest log (ui/QuestLog.lua, game/parts/QuestLog.lua, model/QuestLog.lua, the questwatch, questshare and
questabandon Commands) on the simulated client, as Forever's world map lists your quests beside its map:

  test_questlog_observation: Game reads the whole log only while the big map is up: its headers, and under each its
    quests (hidden ones left out) with level, done, failed, watched, followed, zone map and what each still needs
    (done: the completion line); a read that finds nothing new hands the same table on, a quest unchanged keeps its row.
  test_questlog_panel: hidden on the small map; on the big map once grown, down its right side, the map narrowed to
    leave it; a header and its quests in their difficulty's colour, their lines under them, the count; the box tracks
    and untracks; a header folds (kept in UI.saved) and unfolds; turned off in Settings, or a window too narrow, it's
    gone and the map whole again; hidden with the window.
  test_questlog_clicks: a click follows the quest (Blizzard's super-tracked quest) and flies to its pin, else to its
    zone whole on its own map; the right-click menu tracks, follows, shares and asks to abandon.
"""
from test_addon import errors
from test_quests import CANDLES, FRONTIER, LOVERS, client


def rows(ns):
    """What the panel shows, top down: (kind, text, [lines]) of each shown row."""
    out = []
    ql = ns.UI.QuestLog
    for r in ql.rows.values():
        if not r.IsShown(r):
            continue
        lines = [fs.GetText(fs) for fs in r.lines.values() if fs.IsShown(fs)]
        out.append(("header" if r.data.header else "quest", r.text.GetText(r.text), lines))
    return out


def seq(t):
    """A Lua list's items in order (its other fields left out)."""
    return [v for k, v in sorted((k, v) for k, v in t.items() if isinstance(k, int))]


def same(L, a, b):
    """The same Lua table (lupa's wrappers don't compare by identity)."""
    return L.eval("function(a, b) return rawequal(a, b) end")(a, b)


def row(ns, text):
    return next(r for r in ns.UI.QuestLog.rows.values() if r.IsShown(r) and r.text.GetText(r.text) == text)


def big(sim):
    sim.Press("M")
    sim.Run(0.6)


def test_questlog_observation():
    L, sim, ns, G = client([CANDLES, FRONTIER, LOVERS], followed=52)
    L.execute("local Sim = ...; Sim.quests[106].header = 'Westfall'; Sim.quests[52].failed = true", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    assert ns.Game.obs.questlog is None  # small: not read
    big(sim)
    log = ns.Game.obs.questlog
    shape = [(r.header and "header" or "quest", r.title) for r in seq(log)]
    assert shape == [("header", "Elwynn Forest"), ("quest", "Protect the Frontier"), ("quest", "Kobold Candles"),
                     ("header", "Westfall"), ("quest", "Young Lovers")]
    assert log.quests == 3 and log.max == 40
    frontier, candles, lovers = log[2], log[3], log[5]
    assert frontier.followed and frontier.failed and frontier.level == 11 and frontier.map == 1429
    assert [o.text for o in candles.objectives.values()] == ["Large Candle: 3/8"] and not candles.complete
    assert lovers.complete and [o.text for o in lovers.objectives.values()] == ["Ready for turn-in"]
    # Nothing new: the same table; a count changed: that quest's row new, the others kept.
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    assert same(L, ns.Game.obs.questlog, log)
    L.execute("local Sim = ...; Sim.quests[60].objectives[1].text = 'Large Candle: 4/8'", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    now = ns.Game.obs.questlog
    assert not same(L, now, log) and not same(L, now[3], candles) and same(L, now[2], frontier) and same(L, now[5], lovers)
    # Hidden quests aren't listed; nor is a header with none left.
    L.execute("local Sim = ...; Sim.quests[106].hidden = true", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    assert [r.title for r in seq(ns.Game.obs.questlog)] == ["Elwynn Forest", "Protect the Frontier", "Kobold Candles"]
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_questlog_panel():
    L, sim, ns, G = client([CANDLES, FRONTIER, LOVERS])
    UI = ns.UI
    ql, panel, view, f = UI.QuestLog, UI.QuestLog.panel, UI.Window.view, UI.Window.frame
    L.execute("local Sim = ...; Sim.quests[106].header = 'Westfall'", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    assert not panel.IsShown(panel) and UI.Chrome.side == 0
    sim.Press("M")
    sim.Step()
    assert UI.BigMap.big and not panel.IsShown(panel)  # (growing: it waits)
    sim.Run(0.6)
    assert panel.IsShown(panel) and UI.Chrome.side == 300
    # Down the map's right, inside the border; the map stops where it starts.
    assert abs(panel.GetRight(panel) - view.GetRight(view) - 300) < 1e-6 and abs(panel.GetWidth(panel) - 300) < 1e-6
    assert panel.GetRight(panel) < f.GetRight(f) and abs(panel.GetTop(panel) - view.GetTop(view)) < 1e-6
    assert rows(ns) == [("header", "Elwynn Forest", []),
                        ("quest", "[11] Protect the Frontier", ["- Prowler slain: 2/8"]),
                        ("quest", "[7] Kobold Candles", ["- Large Candle: 3/8"]),
                        ("header", "Westfall", []),
                        ("quest", "[6] Young Lovers", ["- Ready for turn-in"])]
    assert ql.count.GetText(ql.count) == "3/40"
    frontier, candles = row(ns, "[11] Protect the Frontier"), row(ns, "[7] Kobold Candles")
    assert tuple(frontier.text.GetTextColor(frontier.text))[:3] == (1, 0.5, 0.25)  # 3 over you (8): orange
    assert tuple(candles.text.GetTextColor(candles.text))[:3] == (1, 0.82, 0)  # yellow
    assert candles.GetTop(candles) < frontier.GetTop(frontier)
    # Each row as tall as it's set, its lines under its name (a RIGHT anchor would size it from the list's middle).
    for r in ql.rows.values():
        if r.IsShown(r):
            assert abs(sim.Rect(r)[3] - sim.state[r].height) < 1e-6, r.text.GetText(r.text)
    obj = next(fs for fs in candles.lines.values() if fs.IsShown(fs))
    points = [obj.GetPoint(obj, i)[0] for i in range(1, obj.GetNumPoints(obj) + 1)]
    assert sorted(points) == ["TOPLEFT", "TOPRIGHT"] and obj.GetPoint(obj, 1)[4] <= -18

    # The box: out of Blizzard's tracker (a quest taken is in it), and in again.
    assert candles.check.mark.IsShown(candles.check.mark)
    sim.Click(candles.check)
    sim.Run(0.1)
    assert sim.watches[60] is False and not row(ns, "[7] Kobold Candles").check.mark.IsShown(row(ns, "[7] Kobold Candles").check.mark)
    sim.Click(row(ns, "[7] Kobold Candles").check)
    sim.Run(0.1)
    assert sim.watches[60]

    # A header folds its quests away (kept by name), and back.
    sim.Click(row(ns, "Elwynn Forest"))
    assert [r[1] for r in rows(ns)] == ["Elwynn Forest", "Westfall", "[6] Young Lovers"]
    assert UI.saved.questCollapsed["Elwynn Forest"]
    sim.Click(row(ns, "Elwynn Forest"))
    assert len(rows(ns)) == 5 and not UI.saved.questCollapsed["Elwynn Forest"]

    # A header's fold button at its atlas's own size: the minus a bar, the plus a cross (not squashed square).
    elwynn = row(ns, "Elwynn Forest")
    assert elwynn.icon.GetAtlas(elwynn.icon) == "common-button-list-minus" and sim.state[elwynn.icon].height == 5
    sim.Click(elwynn)
    elwynn = row(ns, "Elwynn Forest")
    assert elwynn.icon.GetAtlas(elwynn.icon) == "common-button-list-plus" and sim.state[elwynn.icon].height == 15
    sim.Click(elwynn)
    candles = row(ns, "[7] Kobold Candles")
    assert sim.state[candles.icon].width == 16 and sim.state[candles.icon].height == 16

    # The chevron at the map's top right: ">" puts it away (the setting with it), "<" brings it back.
    toggle = ql.toggle

    def chevron():
        return sim.state[sim.state[toggle].normal].texture
    assert toggle.IsShown(toggle) and "NextPage-Up" in chevron()
    zoom = (ns.UI.Controls.zoomIn, ns.UI.Controls.zoomOut, ns.UI.Controls.zoomReset)

    def centre_x(f):
        return f.GetLeft(f) + f.GetWidth(f) / 2

    assert abs(centre_x(toggle) - (view.GetRight(view) - ns.UI.Controls.COLUMN)) < 1e-6  # (on the zoom buttons' line)
    assert all(abs(centre_x(b) - 1 - centre_x(toggle)) < 1e-6 for b in zoom)  # (their glyphs a px left of centre)
    sim.Click(toggle)
    sim.Run(0.1)
    assert not panel.IsShown(panel) and UI.Chrome.side == 0 and UI.Feel.Get("questlog.sidebar") is False
    assert toggle.IsShown(toggle) and "PrevPage-Up" in chevron()
    assert all(abs(centre_x(b) - 1 - centre_x(toggle)) < 1e-6 for b in zoom)  # (the line moved with the map)
    sim.Click(toggle)
    sim.Run(0.1)
    assert panel.IsShown(panel) and UI.Chrome.side == 300 and "NextPage-Up" in chevron()

    # Off in Settings: gone, the map whole; on again: back.
    UI.Feel.Set("questlog.sidebar", False)
    sim.Run(0.1)
    assert not panel.IsShown(panel) and UI.Chrome.side == 0
    UI.Feel.Set("questlog.sidebar", True)
    sim.Run(0.1)
    assert panel.IsShown(panel) and UI.Chrome.side == 300
    # Hidden with the window (back small), not shown again with it.
    f.Hide(f)
    assert not panel.IsShown(panel) and UI.Chrome.side == 0
    f.Show(f)
    sim.Run(0.2)
    assert not UI.BigMap.big and not panel.IsShown(panel) and not ql.toggle.IsShown(ql.toggle)
    # A big window too narrow for it: none.
    assert ql.Room(650) == 0 and ql.Room(800) == 300
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_questlog_clicks():
    L, sim, ns, G = client([CANDLES, FRONTIER])
    UI = ns.UI
    # One in Durotar: no pin on the maps read (yours, the one shown), its zone's map alone.
    L.execute("""local Sim = ...
        Sim.quests[840] = { title = "Conscript of the Horde", level = 10, map = 1411, x = 0.5, y = 0.5, complete = false,
            header = "Durotar", objectives = { { text = "Speak to Kargal", type = "event", finished = false } } }""", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    big(sim)
    candles = row(ns, "[7] Kobold Candles")
    sim.Click(candles)
    sim.Run(1)
    pin = next(e for e in ns.Model.Known("quests")[0].values() if e.quest == 60)
    c = UI.Camera.cam
    assert sim.superTracked == 60 and not UI.Camera.follow
    assert abs(c.cx - pin.pos.col) < 1e-6 and abs(c.cy - pin.pos.row) < 1e-6
    sim.Run(1)
    assert row(ns, "[7] Kobold Candles").glow.IsShown(row(ns, "[7] Kobold Candles").glow)  # followed: its glow

    sim.Click(row(ns, "[10] Conscript of the Horde"))
    sim.Run(1)
    r = ns.Atlas.MapRect(1411)
    assert sim.superTracked == 840 and UI.Camera.inst == r.inst == 1 and UI.Camera.zone == "Durotar"
    assert r.col0 < c.cx < r.col1 and r.row0 < c.cy < r.row1

    # The right-click menu.
    sim.FireScript(row(ns, "[11] Protect the Frontier"), "OnClick", "RightButton", False)
    items = [(e.kind, e.text) for e in sim.menu["items"].values()]
    assert items == [("title", "Protect the Frontier"), ("button", "Untrack"), ("button", "Follow"), ("button", "Share"),
                     ("button", "Abandon"), ("divider", None), ("button", "Open in quest log")]

    def pick(text):
        sim.FireScript(row(ns, "[11] Protect the Frontier"), "OnClick", "RightButton", False)
        sim.Pick(next(e for e in sim.menu["items"].values() if e.text == text))
        sim.Run(0.1)

    pick("Untrack")
    assert sim.watches[52] is False
    sim.Run(1.5)
    pick("Track")
    assert sim.watches[52]
    pick("Follow")
    assert sim.superTracked == 52
    pick("Share")
    assert sim.pushed == L.globals().C_QuestLog.GetLogIndexForQuestID(52)
    pick("Abandon")
    assert sim.abandonAsked == 52
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_questlog_untracked_off_the_map():
    """Only tracked quests on the map (on by default): unticking a quest's box in the quest log takes its pin and its
    area off the map; followed, it's back (and tracked again, as Blizzard's super-track does); the setting off, every
    quest shows."""
    L, sim, ns, G = client([CANDLES, FRONTIER])
    UI = ns.UI
    L.execute("local Sim = ...; Sim.watches[60] = true; Sim.watches[52] = true", sim)
    sim.FireEvent("QUEST_WATCH_LIST_CHANGED")
    sim.Run(1)
    big(sim)
    UI.Motion.SetFollow(False)
    UI.Motion.SetZoom(200)
    sim.Run(1)

    def pins():
        return sorted(L.eval("""function(layer)
            local out, p = {}, layer.front and layer.front.pools.pin
            for i = 1, p and p.n or 0 do out[#out + 1] = p.keys[i] end
            return out
        end""")(UI.Quests).values())

    def areas():
        return sorted(k for k in L.eval("""function(ns)
            local out = {}
            for _, e in ipairs(ns.Model.Known("quests")) do
                if ns.UI.QuestOnMap(e) and e.areaMap then out[#out + 1] = e.quest end
            end
            return out
        end""")(ns).values())

    assert pins() == ["quest:52", "quest:60"]
    sim.Click(row(ns, "[7] Kobold Candles").check)
    sim.Run(1)
    assert not sim.watches[60] and pins() == ["quest:52"] and 60 not in areas()
    sim.Click(row(ns, "[7] Kobold Candles"))  # followed: back, untracked or not
    sim.Run(1)
    assert sim.superTracked == 60 and "quest:60" in pins()
    assert sim.watches[60]  # (following tracks it too, as Blizzard's super-track does)
    L.execute("local Sim = ...; Sim.superTracked = 0", sim)
    sim.FireEvent("SUPER_TRACKING_CHANGED")
    sim.Click(row(ns, "[7] Kobold Candles").check)
    sim.Run(1)
    assert pins() == ["quest:52"]
    UI.Feel.Set("questlog.trackedOnly", False)
    sim.Run(0.5)
    assert pins() == ["quest:52", "quest:60"]
    assert UI.View().trackedOnly is False
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))

"""Other addons' HereBeDragons pins on our map, on the sim (docs/v1-plan.md M4.2, game/AddonPins.lua):
world pins past 48 px a tile only those flagged for continents, none drawn for the library's own map
alone (-1) or bigger than 128 px, nor an untracked quest's (but one to pick up, or the followed); Questie's turn-ins too (ours are Blizzard's blips: our quests layer draws none); minimap pins on a
host of Game's on the minimap socket, centred on you at the Minimap's view, each where the library
puts it, so on its spot on our map, out of sight under Rotate Minimap, off your map and for a renamed
copy whose world pins we host, back on the Minimap at release.
Game reads UI's View: its sockets (ui/Sockets.lua) and layers. The world pins' round trip and Questie's scale: replays/R-G6.lua, R-G6b.lua; the hidden host
while there's no minimap socket: R-G6c.lua."""
from test_addon import boot, errors

# Questie's world pins in Elwynn: (Type, Id, flag, size px).
PINS = {"world": ("available", 70, 3, 16), "continent": ("available", 71, 2, 16), "parent": ("available", 72, 1, 16),
        "zone": ("available", 73, 0, 16), "own": ("available", 74, -1, 16), "big": ("available", 75, 3, 129),
        "128": ("available", 76, 3, 128), "turnIn": ("complete", 62, 3, 16), "notDone": ("complete", 60, 3, 16),
        "offer": ("available", 62, 3, 16)}


def world_pins(L, sim, q):
    icons = {}
    for i, (name, (kind, qid, flag, px)) in enumerate(PINS.items()):
        icon = sim.QuestieIcon(L.table_from({"Type": kind, "Id": qid}))
        icon.SetSize(icon, px, px)
        q.AddWorldMapIconMap(q, L.globals().Questie, icon, 1429, 0.3 + 0.02 * i, 0.5, flag)
        icons[name] = icon
    return icons


def hosted(L, icons, canvas):
    same = L.eval("rawequal")
    return sorted(n for n, icon in icons.items() if same(icon.GetParent(icon).GetParent(icon.GetParent(icon)), canvas))


def test_world_pins():
    """The show rules: at 96 px a tile all but the library's own map's and the frame bigger than a pin (a
    turn-in too, with our quests layer on: it draws none); zoomed out past 48, the continent's alone; past
    about two zones across the view, none; the quests layer off, Questie's turn-in still."""
    L, sim, ns = boot()
    sim.Slash("/mm toggle")
    ns.UI.Window.frame.SetSize(ns.UI.Window.frame, 300, 300)  # (8 tiles across at 40: within two zones)
    sim.Run(3)
    q = sim.LoadQuestie()
    sim.FireEvent("ADDON_LOADED", "Questie")
    sim.watches[60], sim.watches[62] = True, True  # (in Blizzard's tracker, as the client puts a quest taken)
    view = ns.UI.View()
    icons = world_pins(L, sim, q)
    canvas = view.sockets.world.frame
    sim.Run(0.5)
    assert ns.Game.obs.quests[2].id == 62 and ns.Game.obs.quests[2].complete
    assert hosted(L, icons, canvas) == ["128", "continent", "notDone", "offer", "parent", "turnIn", "world", "zone"]
    # Each within its parent's rect, and that within the socket's (the client takes no mouse for a pin far outside its
    # parent: Questie's tooltips died past the minimap socket around you).

    def inside(f, p):
        fl, fb, fw, fh = sim.Rect(f)
        pl, pb, pw, ph = sim.Rect(p)
        return pl - 1e-6 <= fl and fl + fw <= pl + pw + 1e-6 and pb - 1e-6 <= fb and fb + fh <= pb + ph + 1e-6

    for name in ("world", "zone", "turnIn"):
        icon = icons[name]
        holder = icon.GetParent(icon)
        assert inside(icon, holder) and inside(holder, canvas), name

    ns.UI.Motion.SetZoom(40)  # a continent's
    sim.Step()
    sim.Step()
    assert view.sockets.world.zoom == 40
    sim.Run(0.5)
    assert hosted(L, icons, canvas) == ["128", "continent", "notDone", "offer", "turnIn", "world"]
    ns.UI.Motion.SetZoom(48)
    sim.Run(0.5)
    assert hosted(L, icons, canvas) == ["128", "continent", "notDone", "offer", "parent", "turnIn", "world", "zone"]
    # Wider than about two zones across (13 tiles: 300 px at 20 is 15): no world socket, every pin given back.
    ns.UI.Motion.SetZoom(20)
    sim.Run(0.5)
    assert view.sockets.world is None and hosted(L, icons, canvas) == []
    ns.UI.Motion.SetZoom(48)
    sim.Run(0.5)
    assert len(hosted(L, icons, canvas)) == 8

    # Nothing of ours over the map takes the mouse from them: the controls' and pills' frames (spanning the map, a level
    # over the socket) stay see-through, whatever turned their mouse on.
    c = ns.UI.Chrome
    for f in (c.controls, c.overlay):
        assert not f.IsMouseEnabled(f) and not f.IsMouseMotionEnabled(f)
        f.EnableMouse(f, True)
        f.SetMouseMotionEnabled(f, True)
    sim.Step()
    for f in (c.controls, c.overlay):
        assert not f.IsMouseEnabled(f) and not f.IsMouseMotionEnabled(f)

    ns.UI.Engine.SetLayer("quests", False)  # ours off: Questie's turn-in still shown, by the next regular pass
    sim.Run(1.1)
    assert "turnIn" in hosted(L, icons, canvas)

    # Only tracked quests on the map: 60 untracked, its icon goes (62's to pick up stays: Questie's rule); followed, it's
    # back; the setting off, every one.
    C = L.globals().C_QuestLog
    C.RemoveQuestWatch(60)
    sim.Run(0.5)
    assert "notDone" not in hosted(L, icons, canvas) and "offer" in hosted(L, icons, canvas)
    sim.superTracked = 60
    sim.FireEvent("SUPER_TRACKING_CHANGED")
    ns.UI.Engine.SetLayer("quests", True)
    sim.Run(1.1)
    assert "notDone" in hosted(L, icons, canvas)
    sim.superTracked = 0
    C.RemoveQuestWatch(62)
    sim.Run(0.5)
    assert "notDone" not in hosted(L, icons, canvas) and "turnIn" not in hosted(L, icons, canvas)
    ns.UI.Feel.Set("questlog.trackedOnly", False)
    sim.Run(0.5)
    assert "notDone" in hosted(L, icons, canvas) and "turnIn" in hosted(L, icons, canvas)
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_minimap_pins():
    """GatherMate's herb (the shared copy) and Questie's (renamed) minimap pins through every host."""
    L, sim, ns = boot()
    sim.Slash("/mm toggle")
    sim.Run(3)
    q = sim.LoadQuestie()
    sim.FireEvent("ADDON_LOADED", "Questie")
    socket = ns.UI.View().sockets.minimap
    G, same = L.globals(), L.eval("rawequal")
    quest = sim.QuestieIcon(L.table_from({"Type": "available", "Id": 70}))
    q.AddMinimapIconMap(q, G.Questie, quest, 1429, 0.29, 0.56)
    world = sim.QuestieIcon(L.table_from({"Type": "available", "Id": 70}))  # its world pin: we host it
    q.AddWorldMapIconMap(q, G.Questie, world, 1429, 0.29, 0.56, 3)
    herb, frame, Atlas = sim.gatherPin, socket.frame, ns.Atlas
    sim.Run(0.5)
    host = herb.GetParent(herb)

    def spot(pin):  # its centre in the socket frame's units, from its TOPLEFT
        x, y = pin.GetCenter(pin)
        return x - frame.GetLeft(frame), y - frame.GetTop(frame)

    # Around you on the socket at the Minimap's view, the herb where our map has its spot.
    you = ns.Model.you
    z = socket.zoom
    hx, hy = spot(host)
    assert same(host.GetParent(host), frame) and herb.IsVisible(herb)
    assert abs(hx - you.col * z) < 1e-6 and abs(hy + you.row * z) < 1e-6
    assert host.GetWidth(host) == int(2 * G.C_Minimap.GetViewRadius() / Atlas.TILE_YARDS * z + 0.5)
    m = sim.maps[1429]  # the sim's Elwynn, where it put the herb
    col, row = m[5] + (m[7] - m[5]) * 0.297, m[6] + (m[8] - m[6]) * 0.546
    x, y = spot(herb)
    print(f"the herb {x - col * z:.2f}, {y + row * z:.2f} px off its spot at {z} px a tile")
    assert abs(x - col * z) < 0.6 and abs(y + row * z) < 0.6
    assert host.GetZoom(host) == G.Minimap.GetZoom(G.Minimap) and herb.GetFrameLevel(herb) > host.GetFrameLevel(host)

    # Questie's: its world pins hosted, they'd repeat them; its layer off, none of its pins (the switch hides them all).
    assert not same(quest.GetParent(quest), host) and not quest.IsVisible(quest)
    ns.UI.Engine.SetLayer("addon:Questie", False)
    sim.Step()
    assert not quest.IsVisible(quest)
    # GatherMate's herb (minimap pins alone: no row to turn it off) stays; Questie back on, still none (hosted).
    assert herb.IsVisible(herb)
    ns.UI.Engine.SetLayer("addon:Questie", True)
    sim.Step()
    assert same(herb.GetParent(herb), host) and herb.IsVisible(herb) and not quest.IsVisible(quest)

    # Rotate Minimap: the library turns them with your facing, our map doesn't: out of sight.
    sim.cvars.rotateMinimap = "1"
    sim.Step()
    assert not herb.IsVisible(herb)
    sim.cvars.rotateMinimap = "0"
    sim.Step()
    assert same(herb.GetParent(herb), host) and herb.IsVisible(herb)

    # The map shown isn't yours: they're around you, not on it.
    sim.Slash("/mm map 36")
    sim.Run(0.5)
    assert socket.inst == 36 and same(herb.GetParent(herb), host) and not herb.IsVisible(herb)
    sim.Slash("/mm follow")
    sim.Run(0.5)
    assert socket.inst == 0 and herb.IsVisible(herb)

    mm = G.Minimap

    sim.Slash("/mm toggle")  # released: back on the Minimap (at its home), placed there again
    sim.Step()
    assert not ns.Game.minimap.engaged and same(q.Minimap, mm) and same(sim.hbdPins.Minimap, mm)
    assert same(herb.GetParent(herb), mm) and herb.IsVisible(herb) and not host.IsShown(host)
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_questie_tooltips_far_from_you():
    """Questie's tooltip lists the icons near the hovered one among the pins on Blizzard's world map (your zone): for
    one we host elsewhere that was none, no tooltip. Hovering ours, Game asks it again with the icons we host near it
    (the same area, within 1% of its map), the hovered among them; none from another area or further off."""
    L, sim, ns = boot()
    sim.Slash("/mm toggle")
    ns.UI.Window.frame.SetSize(ns.UI.Window.frame, 300, 300)
    sim.Run(3)
    q = sim.LoadQuestie()
    sim.FireEvent("ADDON_LOADED", "Questie")
    L.execute("""local Sim = ...
        Sim.tipCalls = {}
        QuestieLoader = { ImportModule = function(_, name)
            if name ~= "MapIconTooltip" then return nil end
            return { ShowOnTooltip = function(self, tooltip, owner, icons)
                Sim.tipCalls[#Sim.tipCalls + 1] = { self = self, tooltip = tooltip, owner = owner, icons = icons }
            end }
        end }""", sim)
    # (x, y in its map's percent, AreaID): a, b near each other; c the same area further off; d another area.
    spots = {"a": (30.0, 50.0, 12), "b": (30.5, 50.4, 12), "c": (34.0, 50.0, 12), "d": (30.2, 50.1, 40)}
    icons = {}
    for name, (x, y, area) in spots.items():
        icon = sim.QuestieIcon(L.table_from({"Type": "available", "Id": 80 + len(icons)}))
        icon.x, icon.y, icon.AreaID = x, y, area
        q.AddWorldMapIconMap(q, L.globals().Questie, icon, 1429, x / 100, y / 100, 3)
        icons[name] = icon
    sim.Run(0.5)
    same = L.eval("rawequal")
    sim.FireScript(icons["a"], "OnEnter")
    call = sim.tipCalls[1]
    listed = [n for n, icon in icons.items() if any(same(icon, i) for i in call.icons.values())]
    assert same(call.self, icons["a"]) and same(call.owner, icons["a"]) and same(call.tooltip, L.globals().GameTooltip)
    assert sorted(listed) == ["a", "b"]
    # Given back (the window hidden), its hover is Questie's own again.
    ns.UI.Window.frame.Hide(ns.UI.Window.frame)
    sim.Run(0.5)
    sim.FireScript(icons["a"], "OnEnter")
    assert len(sim.tipCalls) == 1
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))

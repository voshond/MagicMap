"""The Minimap ping and the Map Pin button on the simulated client (game/commands/ping.lua, game/parts/Ping.lua,
ui/Ping.lua, ui/ZoneInfo.lua's Tap, ui/MapPin.lua, ui/Window.lua's press): the small map sits over Blizzard's Minimap,
which it takes over with the mouse off, so a click never pings by itself.

  test_ping_send: a click on your small map no pin or quest area took pings the Minimap at that spot, in its units:
    10 yd east of you is x = 10 * (width / 2) / view radius, y = 0; north is up; where it rotates, turned by your
    facing; none on the big map, off your own map, after a drag, on a pin, or outside its radius.
  test_ping_draw: a MINIMAP_PING (a group member's) reads back to the tile it points at (the same scale), and draws
    rings there on the map shown with the pinger's name in their class's colour, for PING_SECS; none on another map,
    nor while Blizzard's own Minimap is seen over the small map.
  test_map_pin: the Map Pin button shows on the big map alone; armed, a left press on the map puts the waypoint at
    the cursor (the waypoint Command, as Ctrl-click), taken on the press (no pan), and disarms; a right press, the
    map shrinking or the button again disarms; off the zones' maps it stays armed and the press is the map's.
"""
import math

from test_addon import boot, errors
from test_quests import FRONTIER, client

TILE_YARDS = 1600 / 3
RADIUS = 40  # yd, a small one: 100 yd out is outside it


def setup(quests=()):
    L, sim, ns, G = client(list(quests))
    sim.Run(0.5)
    return L, sim, ns, G


def minimap(L):
    """(Minimap's width, its view radius) as the client says them now."""
    return L.eval("function() return Minimap:GetWidth(), C_Minimap.GetViewRadius() end")()


def stub_radius(L, r=RADIUS):
    """The view radius held (it is 0 while a zoom applies)."""
    L.execute(f"C_Minimap.GetViewRadius = function() return {r} end")


def click_at(sim, G, ns, col, row, button="LeftButton"):
    G.Over(col, row)
    sim.Click(ns.UI.Window.view, button, sim.cursorX, sim.cursorY, "screen")
    sim.Run(0.1)


def pings(sim):
    return [(p.x, p.y) for p in sim.pings.values()]


def yards(sim, east=0.0, north=0.0):
    """The tile `east` and `north` yards from you."""
    return sim.player.col + east / TILE_YARDS, sim.player.row - north / TILE_YARDS


def test_ping_send():
    L, sim, ns, G = setup([FRONTIER])
    stub_radius(L)
    UI = ns.UI
    w, _ = minimap(L)
    per_yard = (w / 2) / RADIUS
    assert not UI.BigMap.big and UI.Camera.inst == ns.Model.you.inst

    click_at(sim, G, ns, *yards(sim, east=10))
    assert len(pings(sim)) == 1
    x, y = pings(sim)[0]
    assert abs(x - 10 * per_yard) < 1e-6 and abs(y) < 1e-6
    click_at(sim, G, ns, *yards(sim, north=15))
    x, y = pings(sim)[1]
    assert abs(x) < 1e-6 and abs(y - 15 * per_yard) < 1e-6
    click_at(sim, G, ns, *yards(sim, east=-10, north=-10))
    x, y = pings(sim)[2]
    assert abs(x + 10 * per_yard) < 1e-6 and abs(y + 10 * per_yard) < 1e-6

    # Rotating (Rotate Minimap on, the takeover not holding it off): up is where you face, west here, so north is right.
    sim.player.facing = math.pi / 2
    L.execute("Sim = ...; Sim.cvars.rotateMinimap = '1'; C_Minimap.IsRotateMinimapIgnored = function() return false end", sim)
    sim.Step()
    click_at(sim, G, ns, *yards(sim, north=10))
    x, y = pings(sim)[3]
    assert abs(x - 10 * per_yard) < 1e-6 and abs(y) < 1e-6
    L.execute("Sim = ...; Sim.cvars.rotateMinimap = '0'", sim)
    sim.player.facing = 0

    # Outside its radius, none.
    before = len(pings(sim))
    click_at(sim, G, ns, *yards(sim, east=100))
    assert len(pings(sim)) == before

    # A drag pans the map and pings nothing.
    sim.Drag(UI.Window.view, 30, 0)
    assert len(pings(sim)) == before

    # A pin takes the click (its popup): no ping.
    G.Over(FRONTIER["col"], FRONTIER["row"])
    sim.FireScript(UI.Window.view, "OnEnter", False)
    sim.Run(0.3)
    sim.Click(UI.Window.view, "LeftButton", sim.cursorX, sim.cursorY, "screen")
    assert UI.Popup.IsOpen() and len(pings(sim)) == before
    UI.Popup.frame.Hide(UI.Popup.frame)

    # The big map: none.
    sim.Press("M")
    sim.Run(0.6)
    assert UI.BigMap.big
    click_at(sim, G, ns, *yards(sim, east=10))
    assert len(pings(sim)) == before
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_ping_off_your_map():
    L, sim, ns, G = setup()
    stub_radius(L)
    ns.UI.Camera.inst = 1  # another map shown: its click is the zone's, not a ping
    ns.UI.Camera.follow = False
    sim.Run(0.3)
    cursor = ns.UI.ZoneInfo.CursorTile()
    ns.UI.ZoneInfo.Tap()
    sim.Run(0.1)
    assert cursor is not None and pings(sim) == []
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def ring_state(ns, sim):
    """(ring shown, its centre from the view's top left, the name's text and colour)."""
    UI, S = ns.UI, sim.state
    ring, name = UI.Ping.ring, UI.Ping.name
    shown = UI.Ping.frame.IsShown(UI.Ping.frame) and S[ring].shown is not False
    view = UI.Window.view
    cx, cy = ring.GetCenter(ring)
    return (shown, (cx - view.GetLeft(view), view.GetTop(view) - cy), name.GetText(name),
            list(name.GetTextColor(name)))


def test_ping_draw():
    L, sim, ns, G = setup()
    stub_radius(L)
    UI = ns.UI
    L.execute("""local Sim = ...
        Sim.units.party1 = { name = "Thrall", class = "SHAMAN" }
        RAID_CLASS_COLORS.SHAMAN = { r = 0, g = 0.44, b = 0.87 }""", sim)
    w, _ = minimap(L)
    per_yard = (w / 2) / RADIUS
    assert not UI.Ping.frame.IsShown(UI.Ping.frame)

    # 20 yd east and 10 north of you, from the Minimap's centre: x = 20, y = 10 yards of its units.
    sim.FireEvent("MINIMAP_PING", "party1", 20 * per_yard, 10 * per_yard)
    sim.Run(0.5)
    ping = ns.Model.ping
    assert ping.name == "Thrall" and ping["class"] == "SHAMAN"
    assert abs(ping.pos.col - (sim.player.col + 20 / TILE_YARDS)) < 1e-6
    assert abs(ping.pos.row - (sim.player.row - 10 / TILE_YARDS)) < 1e-6 and ping.pos.inst == sim.player.inst
    shown, (x, y), text, color = ring_state(ns, sim)
    w_view, h_view = UI.Window.Size()
    ex, ey = ns.Atlas.Camera.TileToScreen(UI.Camera.cam, w_view, h_view, ping.pos.col, ping.pos.row)
    assert shown and abs(x - ex) < 1e-3 and abs(y - ey) < 1e-3
    assert text == "Thrall" and [round(c, 2) for c in color[:3]] == [0, 0.44, 0.87]
    # The ring spreads and fades.
    size0 = UI.Ping.ring.GetWidth(UI.Ping.ring)
    sim.Run(0.3)
    assert UI.Ping.ring.GetWidth(UI.Ping.ring) > size0

    # Gone after PING_SECS.
    sim.Run(3.0)
    assert not UI.Ping.frame.IsShown(UI.Ping.frame)

    # Another map shown: none. Blizzard's Minimap seen over the small map: none.
    sim.FireEvent("MINIMAP_PING", "party1", 0, 0)
    sim.Run(0.3)
    assert UI.Ping.frame.IsShown(UI.Ping.frame)
    L.execute("local ns = ...; ns.Game.minimap.overlaid = true", ns)
    sim.Step()
    assert not UI.Ping.frame.IsShown(UI.Ping.frame)
    L.execute("local ns = ...; ns.Game.minimap.overlaid = false", ns)
    sim.Step()
    assert UI.Ping.frame.IsShown(UI.Ping.frame)
    UI.Camera.inst, UI.Camera.follow = 1, False
    sim.Step()
    assert not UI.Ping.frame.IsShown(UI.Ping.frame)

    # No scale known (a zoom applying: radius 0): no ping read.
    UI.Camera.inst, UI.Camera.follow = sim.player.inst, True
    stub_radius(L, 0)
    before = ns.Model.ping
    sim.FireEvent("MINIMAP_PING", "party1", 5, 5)
    sim.Run(0.3)
    assert L.eval("function(a, b) return rawequal(a, b) end")(ns.Model.ping, before)
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_ping_without_the_event():
    """A client without MINIMAP_PING (Forever's): nothing is registered (no error at load), and your own ping, as
    sent, is the one read and drawn."""
    L, sim, ns = boot(unknown=["MINIMAP_PING"])
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))
    sim.Slash("/mm toggle")
    sim.Run(1.5)
    stub_radius(L)
    w, _ = minimap(L)
    per_yard = (w / 2) / RADIUS
    col, row = yards(sim, east=10)
    ns.Game.Command(L.table(kind="ping", pos=L.table(inst=sim.player.inst, col=col, row=row)))
    sim.Run(0.5)
    assert len(pings(sim)) == 1 and abs(pings(sim)[0][0] - 10 * per_yard) < 1e-6
    ping = ns.Model.ping
    assert ping and ping.name == sim.units.player.name
    assert abs(ping.pos.col - col) < 1e-6 and abs(ping.pos.row - row) < 1e-6
    assert ns.UI.Ping.frame.IsShown(ns.UI.Ping.frame)
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_map_pin():
    L, sim, ns, G = setup()
    UI, S = ns.UI, sim.state
    pin = UI.MapPin
    button, view = pin.button, UI.Window.view
    assert not button.IsShown(button) and not pin.armed

    sim.Press("M")
    sim.Run(0.6)
    assert UI.BigMap.big and button.IsShown(button)
    toggle = UI.QuestLog.toggle
    # Left of the quest log's chevron, on its line.
    assert button.GetRight(button) < toggle.GetLeft(toggle) and abs(
        (button.GetTop(button) + button.GetBottom(button)) / 2 - (toggle.GetTop(toggle) + toggle.GetBottom(toggle)) / 2) < 1e-6

    # Armed by its click, lit; again: disarmed.
    sim.Click(button)
    assert pin.armed and S[button].lit
    sim.Click(button)
    assert not pin.armed and not S[button].lit

    # Armed: a left press puts the waypoint at the cursor, no pan, disarmed.
    sim.Click(button)
    cam = UI.Camera.cam
    cx, cy, zoom = cam.cx, cam.cy, cam.zoom
    G.Over(32.5, 49.6)
    sim.Click(view, "LeftButton", sim.cursorX, sim.cursorY, "screen")
    sim.Run(0.2)
    w = ns.Game.obs.waypoint
    assert sim.waypoint.uiMapID == 1429 and abs(w.col - 32.5) < 1e-3 and abs(w.row - 49.6) < 1e-3
    assert not pin.armed and (cam.cx, cam.cy, cam.zoom) == (cx, cy, zoom)
    # Not armed any more: a plain click places nothing new.
    ns.Game.Command(L.table_from({"kind": "waypoint", "pos": False}))
    sim.Run(0.1)
    assert sim.waypoint is None
    click_at(sim, G, ns, 31.0, 50.2)
    assert sim.waypoint is None

    # A right press disarms (its menu is the map's).
    sim.Click(button)
    assert pin.armed
    G.Over(32.5, 49.6)
    sim.FireScript(view, "OnMouseDown", "RightButton")
    sim.FireScript(view, "OnMouseUp", "RightButton")
    sim.Run(0.1)
    assert not pin.armed and sim.waypoint is None

    # Off the zones' maps: stays armed, nothing placed.
    sim.Click(button)
    UI.Motion.SetZoom(30)
    sim.Run(0.5)
    sea = L.eval("""function(ns)
        local cam, w, h = ns.UI.Camera.cam, ns.UI.Window.Size()
        for x = 10, w - 10, 10 do
            for y = 10, h - 10, 10 do
                local col, row = ns.Atlas.Camera.ScreenToTile(cam, w, h, x, y)
                if not ns.Atlas.ZoneMapAt(ns.UI.Camera.inst, col, row) then return col, row end
            end
        end
    end""")(ns)
    G.Over(*sea)
    sim.FireScript(view, "OnMouseDown", "LeftButton")
    sim.FireScript(view, "OnMouseUp", "LeftButton")
    sim.Run(0.1)
    assert pin.armed and sim.waypoint is None

    # The map shrinking disarms.
    sim.Press("M")
    sim.Run(0.6)
    assert not UI.BigMap.big and not pin.armed and not button.IsShown(button)
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))

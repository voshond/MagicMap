-- obs.ping (types/observation.lua MM.ObsPing), on change: the latest MINIMAP_PING (a click on the Minimap
-- pings there, ours included: game/commands/ping.lua sends ours), as a tile spot, its pinger's name and class. The
-- event gives the spot in the Minimap's own units from its centre, up the way it faces (rotated, when it rotates):
-- Game.PingScale is how many of them make a yard, and the turn; the same for what we send and what we read. Read
-- against where you are as the frame has it (where you stood a moment ago is near enough for a ping's three seconds).

local _, ns = ...
local Atlas, Game, Runtime = ns.Atlas, ns.Game, ns.Runtime

local TILE_YARDS = Atlas.TILE_YARDS

-- The Minimap's units a yard, and the angle its up is turned from north (GetPlayerFacing's, radians counter-clockwise;
-- 0: it doesn't rotate); nil: not known now (a view radius 0 while it zooms, no facing).
function Game.PingScale()
	local r, w = C_Minimap.GetViewRadius(), Minimap:GetWidth()
	if issecretvalue(r) or r <= 0 or w <= 0 then return nil end
	local turn = 0
	if GetCVar("rotateMinimap") == "1" and not C_Minimap.IsRotateMinimapIgnored() then
		turn = GetPlayerFacing()
		if not turn then return nil end
	end
	return (w / 2) / r, turn -- /: never 0 (r > 0)
end

local pending -- the last event's: { unit, x, y }, read next observe
Runtime.On("MINIMAP_PING", "game.ping", function(_, unit, x, y)
	if issecretvalue(x) or issecretvalue(y) then return end
	pending = { unit = unit, x = x, y = y }
end)

local ping -- the last handed over
Game.Part("ping", function(obs)
	local p = pending
	if not p then return ping end
	pending = nil
	local you = obs.you
	local perYard, turn = Game.PingScale()
	if not (perYard and you and you.col) then return ping end
	local x, y = p.x / perYard, p.y / perYard -- /: never 0 (PingScale's perYard > 0)
	local east, north = x * math.cos(turn) - y * math.sin(turn), x * math.sin(turn) + y * math.cos(turn)
	local _, class = UnitClass(p.unit)
	ping = { pos = { inst = you.inst, col = you.col + east / TILE_YARDS, row = you.row - north / TILE_YARDS },
		name = UnitName(p.unit), class = class, t = obs.t }
	return ping
end)

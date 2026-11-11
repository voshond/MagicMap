-- ping (types/view.lua MM.CmdPing): a ping on the Minimap at pos, which the small map sits over: where Forever's own
-- Minimap would ping on a click (MinimapMixin:OnClick: its units from its centre, up the way it faces, only inside
-- its radius). The yards from you, east and north, turned by your facing when the Minimap rotates, as many units
-- a yard as its view radius makes (Game.PingScale: game/parts/Ping.lua, which reads a ping back the same way).

local _, ns = ...
local Atlas, Game = ns.Atlas, ns.Game

local TILE_YARDS = Atlas.TILE_YARDS

Game.Handle("ping", function(c)
	local p, you = c.pos, Game.obs.you
	if not (you and you.col and you.inst == p.inst) then return end
	local perYard, turn = Game.PingScale()
	if not perYard then return end
	local east, north = (p.col - you.col) * TILE_YARDS, (you.row - p.row) * TILE_YARDS -- (columns run east, rows south)
	local sin, cos = math.sin(turn), math.cos(turn)
	local x, y = (east * cos + north * sin) * perYard, (north * cos - east * sin) * perYard
	local reach = Minimap:GetWidth() / 2
	if x * x + y * y >= reach * reach then return end
	Minimap:PingLocation(x, y)
end)

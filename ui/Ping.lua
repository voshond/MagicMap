-- A ping on the Minimap (obs.ping: yours, which a click on the small map sends, ui/ZoneInfo.lua's Tap, or a group
-- member's): for PING_SECS, rings spreading and fading from its spot on the map shown when it's on that map (big or
-- small), the pinger's name under it in their class's colour. Forever's WorldQuest ring, else the party dots'
-- old file's ring. None while Blizzard's own Minimap is seen over the small map (Model.minimap.overlaid): the client
-- draws its ping there.

local _, ns = ...
local UI, Model, Runtime = ns.UI, ns.Model, ns.Runtime
local Camera, Window = UI.Camera, UI.Window
local Maths = ns.Atlas.Camera

local LEVEL = 17 -- over the quests (15)
local PING_SECS = 3 -- how long it shows
local PULSE_SECS = 1 -- a ring's spread, from MIN to MAX px; the next starts as it ends
local MIN, MAX = 12, 64 -- px across
local RING = "worldquest-tracker-ring" -- Forever's: a thin round ring
local OLD_RING = "Interface\\Minimap\\PartyRaidBlipsV2" -- its right half: a ring (Layers.lua:667)
local NAME_GAP = 3 -- px under the ring's full size

local Ping = {}
UI.Ping = Ping

local frame = CreateFrame("Frame", nil, Window.view)
frame:SetAllPoints()
frame:SetFrameLevel(Window.view:GetFrameLevel() + LEVEL)
frame:Hide()
Ping.frame = frame

local ring = frame:CreateTexture(nil, "ARTWORK")
if C_Texture.GetAtlasInfo(RING) then
	ring:SetAtlas(RING)
else
	ring:SetTexture(OLD_RING)
	ring:SetTexCoord(0.5, 1, 0, 1)
end
ring:SetSnapToPixelGrid(false)
ring:SetTexelSnappingBias(0)
Ping.ring = ring

local name = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmallOutline")
Ping.name = name

local function Hide()
	if frame:IsShown() then frame:Hide() end
end

Runtime.Step("ui", "map: ping", function()
	local p, mm = Model.ping, Model.minimap
	local age = p and GetTime() - p.t
	if not p or age >= PING_SECS or age < 0 or p.pos.inst ~= Camera.inst or mm and mm.overlaid then return Hide() end
	local cam, w, h = Camera.cam, Window.Size()
	local x, y = Maths.TileToScreen(cam, w, h, p.pos.col, p.pos.row)
	local phase = (age % PULSE_SECS) / PULSE_SECS
	local size = MIN + (MAX - MIN) * phase
	ring:SetSize(size, size)
	ring:SetPoint("CENTER", frame, "TOPLEFT", x, -y)
	ring:SetAlpha((1 - phase) * (1 - age / PING_SECS)) -- (fading with each ring, and over the whole)
	if name.text ~= p.name then
		name.text = p.name
		name:SetText(p.name or "")
	end
	if name.class ~= p.class then
		name.class = p.class
		local c = p.class and RAID_CLASS_COLORS[p.class]
		if c then name:SetTextColor(c.r, c.g, c.b, 1) else name:SetTextColor(1, 1, 1, 1) end
	end
	name:SetPoint("TOP", frame, "TOPLEFT", x, -(y + MAX / 2 + NAME_GAP))
	if not frame:IsShown() then frame:Show() end
end, { shownOnly = Window.frame })
Window.frame:HookScript("OnHide", Runtime.Wrap("map: ping hidden", Hide))

-- The Map Pin button on the big map, as Forever's world map has (WaypointLocationDataProvider.lua: toggleActive):
-- a toggle at the map's top right, left of the quest log's chevron (ui/QuestLog.lua), on the zoom buttons' line.
-- Armed (lit), a left press on the map puts the waypoint at the cursor, as Ctrl-click does (ui/ZoneInfo.lua's
-- Waypoint), taken on the press (no pan), and disarms; a right press, the map shrinking or the window hiding, or the
-- button again, disarms. Not where no zone's map is (Atlas.ZoneMapAt): the press stays the map's, still armed.

local _, ns = ...
local UI, Runtime = ns.UI, ns.Runtime
local Window, Chrome = UI.Window, UI.Chrome

local SIZE = 24 -- px
local GAP = 4 -- px between it and the chevron
local CHEVRON = 26 -- ui/QuestLog.lua's TOGGLE
local ARTS = { "Waypoint-MapPin-ButtonToggle", "Waypoint-MapPin-Untracked" } -- Forever's, the first it has
local PLAIN = "Interface\\Icons\\INV_Misc_Map_01"
local LIT = { 1, 0.86, 0.25 } -- armed: the zoom buttons' gold
local TIP = "Map Pin"
local TIP_HELP = "Click the map to place a waypoint (or Ctrl-click any time)"

local MapPin = { armed = false }
UI.MapPin = MapPin

local button = CreateFrame("Button", nil, Chrome.overlay)
button:SetSize(SIZE, SIZE)
button:SetPoint("CENTER", Chrome.overlay, "TOPRIGHT", -(UI.Controls.COLUMN + (CHEVRON + SIZE) / 2 + GAP), -2 - CHEVRON / 2) -- (the chevron's line)
button:Hide()
MapPin.button = button

local art
for _, name in ipairs(ARTS) do
	if not art and C_Texture.GetAtlasInfo(name) then art = name end
end
if art then button:SetNormalAtlas(art) else button:SetNormalTexture(PLAIN) end
button:SetHighlightTexture("Interface\\Buttons\\UI-Common-MouseHilight", "ADD")

local function Look()
	local c = MapPin.armed and LIT or { 1, 1, 1 }
	button:GetNormalTexture():SetVertexColor(c[1], c[2], c[3], 1)
	if MapPin.armed then button:LockHighlight() else button:UnlockHighlight() end
end
Look()

local function Arm(on)
	if MapPin.armed == on then return end
	MapPin.armed = on
	Look()
end

button:SetScript("OnClick", Runtime.Wrap("map: map pin toggle", function() Arm(not MapPin.armed) end, Runtime.FRAME_MS))
UI.Controls.Tip(button, function() return TIP, TIP_HELP end)

-- A press on the map (ui/Window.lua): true if taken.
function MapPin.Press(mouseButton)
	if not MapPin.armed then return false end
	if mouseButton ~= "LeftButton" then
		Arm(false)
		return false
	end
	if not UI.ZoneInfo.Waypoint() then return false end
	Arm(false)
	return true
end

Runtime.Step("ui", "map: map pin", function()
	local big = UI.BigMap.big == true
	if button:IsShown() ~= big then button:SetShown(big) end
	if not big then Arm(false) end
end, { shownOnly = Window.frame })
Window.frame:HookScript("OnHide", Runtime.Wrap("map: map pin hidden", function()
	button:Hide()
	Arm(false)
end))

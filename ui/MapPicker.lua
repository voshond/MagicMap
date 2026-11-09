-- The big map's map dropdown: the client's own (WowStyle1DropdownTemplate), at the map's top left as Blizzard's world
-- map has its nav bar (Blizzard_WorldMap's WorldMapNavBar), naming the map shown and opening the picker's rows
-- (ui/Menus.lua's PickerRows: continents, other maps, instances), the title's click made plain to see. Shown on the
-- big map alone; its text follows the map shown (a pick, the map you walk onto while following).

local _, ns = ...
local UI, Runtime = ns.UI, ns.Runtime
local Chrome, Menus, Camera = UI.Chrome, UI.Menus, UI.Camera

local PAD = 8 -- px in from the view's corner
local WIDTH, HEIGHT = 180, 25

local MapPicker = {}
UI.MapPicker = MapPicker

local drop = CreateFrame("DropdownButton", nil, Chrome.overlay, "WowStyle1DropdownTemplate")
drop:SetPoint("TOPLEFT", PAD, -PAD)
drop:SetSize(WIDTH, HEIGHT)
drop:SetDefaultText("Maps")
drop:SetupMenu(function(_, root) Menus.PickerRows(root) end)
drop:Hide()
MapPicker.drop = drop

local shownInst -- the map its text names
Runtime.Step("ui", "map: picker dropdown", function()
	local big = UI.BigMap.big == true
	if drop:IsShown() ~= big then drop:SetShown(big) end
	if not big or Camera.inst == shownInst or drop:IsMenuOpen() then return end
	shownInst = Camera.inst
	drop:GenerateMenu()
end, { shownOnly = UI.Window.frame })

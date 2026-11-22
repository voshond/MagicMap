-- The window's chrome: the template's frame (whose top is a header bar) gives way to its
-- metal border on all four sides from the client's frame atlases; the view fills it, inset by
-- the border's thickness clamped 2..6 (Forever's edge atlases report far more than their visible
-- metal). Above it: the band (title, gear, mode: ui/Title.lua, ui/Controls.lua), the map's
-- controls and the resize grip. Everything else of the template is hidden. Settings > General > Map
-- window > Border swaps the metal for Blizzard's tooltip edge (Chrome.SetBorder): the view and what
-- Chrome.OnInsets places follow the shown one's insets.

local _, ns = ...
local UI = ns.UI
local Runtime = ns.Runtime
local Window = UI.Window
local frame, view = Window.frame, Window.view

local MAX_INSET = 6 -- px a side, at most
local LEVEL_BORDER, LEVEL_BAND, LEVEL_CONTROLS, LEVEL_GRIP = 505, 515, 518, 520 -- over the frame's

local Chrome = { CIRCLE = "Interface\\CharacterFrame\\TempPortraitAlphaMask" }
UI.Chrome = Chrome

-- An atlas piece with an optional vertical flip: file + texcoords set here (not SetAtlas)
-- so the bottom corners and edge mirror for the top.
local function Piece(parent, atlas, flipV)
	local info = C_Texture.GetAtlasInfo(atlas)
	local t = parent:CreateTexture(nil, "OVERLAY")
	t:SetTexture(info.file)
	local l, r, top, bottom = info.leftTexCoord, info.rightTexCoord, info.topTexCoord, info.bottomTexCoord
	if flipV then top, bottom = bottom, top end
	t:SetTexCoord(l, r, top, bottom)
	t:SetSize(info.width, info.height)
	return t
end

-- ref: the template's NineSlice, whose corners say where the art sits. b.insets = { left,
-- top, right, bottom }: how far in the border reaches, so the view stops there.
local function Border(level, ref)
	local b = CreateFrame("Frame", nil, frame)
	b:SetAllPoints()
	b:SetFrameLevel(level)
	-- Only the thin bottom corners and edges; the top ones carry a header bar.
	local bl = Piece(b, "UI-Frame-Metal-CornerBottomLeft")
	local br = Piece(b, "UI-Frame-Metal-CornerBottomRight")
	local tl = Piece(b, "UI-Frame-Metal-CornerBottomLeft", true)
	local tr = Piece(b, "UI-Frame-Metal-CornerBottomRight", true)
	local bottom = Piece(b, "_UI-Frame-Metal-EdgeBottom")
	local top = Piece(b, "_UI-Frame-Metal-EdgeBottom", true)
	local left = Piece(b, "!UI-Frame-Metal-EdgeLeft")
	local right = Piece(b, "!UI-Frame-Metal-EdgeRight")
	-- The corner art carries padding; the template knows where it sits.
	local lx, y, rx = -3, -3, 3
	if ref and ref.BottomLeftCorner and ref.BottomRightCorner then
		local _, _, _, x1, y1 = ref.BottomLeftCorner:GetPoint(1)
		local _, _, _, x2 = ref.BottomRightCorner:GetPoint(1)
		if x1 and y1 and x2 then lx, y, rx = x1, y1, x2 end
	end
	bl:SetPoint("BOTTOMLEFT", lx, y)
	br:SetPoint("BOTTOMRIGHT", rx, y)
	tl:SetPoint("TOPLEFT", lx, -y)
	tr:SetPoint("TOPRIGHT", rx, -y)
	-- Edges are uniform strips: stretched, they look tiled.
	bottom:SetPoint("BOTTOMLEFT", bl, "BOTTOMRIGHT")
	bottom:SetPoint("BOTTOMRIGHT", br, "BOTTOMLEFT")
	top:SetPoint("TOPLEFT", tl, "TOPRIGHT")
	top:SetPoint("TOPRIGHT", tr, "TOPLEFT")
	left:SetPoint("TOPLEFT", tl, "BOTTOMLEFT")
	left:SetPoint("BOTTOMLEFT", bl, "TOPLEFT")
	right:SetPoint("TOPRIGHT", tr, "BOTTOMRIGHT")
	right:SetPoint("BOTTOMRIGHT", br, "TOPRIGHT")
	-- Each edge starts |lx| (|y|) outside the frame; a pixel of overlap so nothing shows
	-- between the art and what it frames; capped (L2).
	local function In(thickness, outside)
		return math.max(2, math.min(MAX_INSET, math.floor((thickness or 0) - outside - 1)))
	end
	b.insets = { In(left:GetWidth(), -lx), In(top:GetHeight(), -y), In(right:GetWidth(), rx), In(bottom:GetHeight(), -y) }
	return b
end

-- Settings > General > Map window > Border's other look: Blizzard's chamfered tooltip edge, as unit-frames draws its
-- frames (Backdrop.lua, Theme.lua: "Blizzard Tooltip", 12, grey 0.5). Edge only: its background would cover the
-- view under it, so the dark behind the corners is the frame's own (TOOLTIP_BACKING, below).
local TOOLTIP_EDGE, TOOLTIP_BG = "Interface\\Tooltips\\UI-Tooltip-Border", "Interface\\Tooltips\\UI-Tooltip-Background"
local TOOLTIP_SIZE, TOOLTIP_INSET, TOOLTIP_GREY = 12, 3, 0.5
local TOOLTIP_BACKING = { 0, 0, 0, 0.85 }
local function Tooltip(level)
	local b = CreateFrame("Frame", nil, frame, "BackdropTemplate")
	b:SetAllPoints()
	b:SetFrameLevel(level)
	b:SetBackdrop({ edgeFile = TOOLTIP_EDGE, edgeSize = TOOLTIP_SIZE })
	b:SetBackdropBorderColor(TOOLTIP_GREY, TOOLTIP_GREY, TOOLTIP_GREY, 1)
	b.insets = { TOOLTIP_INSET, TOOLTIP_INSET, TOOLTIP_INSET, TOOLTIP_INSET }
	return b
end

local base = frame:GetFrameLevel()

local borders = { metal = Border(base + LEVEL_BORDER, frame.NineSlice), tooltip = Tooltip(base + LEVEL_BORDER) }
Chrome.borders = borders
Chrome.border = borders.metal -- the one shown (Chrome.SetBorder)

-- The band: above the border, holding the zone line and its buttons. No mouse of its own.
local band = CreateFrame("Frame", nil, frame)
band:SetFrameLevel(base + LEVEL_BAND)
band:SetAllPoints()
Chrome.band = band

-- On the view's corner, as far from it as the metal border puts it (4 px in from the frame's): it moves with the view.
local metal = borders.metal.insets
local grip = CreateFrame("Button", nil, frame)
grip:SetSize(14, 14)
grip:SetPoint("BOTTOMRIGHT", view, "BOTTOMRIGHT", metal[3] - 4, 4 - metal[4])
grip:SetFrameLevel(base + LEVEL_GRIP)
grip:SetAlpha(0.8)
grip:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
grip:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
grip:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
grip:SetScript("OnMouseDown", Runtime.Wrap("map: resize", function() if not UI.Window.locked then frame:StartSizing("BOTTOMRIGHT") end end))
grip:SetScript("OnMouseUp", Runtime.Wrap("map: resized", function()
	frame:StopMovingOrSizing()
	Window.Moved()
end))
Chrome.grip = grip

-- Inside the map, shown while you hover: the zoom buttons and reset (ui/Controls.lua).
local controls = CreateFrame("Frame", nil, frame)
controls:SetAllPoints(view)
controls:SetFrameLevel(base + LEVEL_CONTROLS) -- under the grip
Chrome.controls = controls

-- The pills' frame (ui/Controls.lua: the quest and tracking pills): at the controls' level, but not under them, so a pill
-- can stay shown at full alpha when they fade.
local overlay = CreateFrame("Frame", nil, frame)
overlay:SetAllPoints(view)
overlay:SetFrameLevel(base + LEVEL_CONTROLS)
Chrome.overlay = overlay

-- Both span the map over everything on it, other addons' pins too (Questie's, ui/Sockets.lua's world socket): they take
-- no mouse themselves, only their buttons and pills do. One taking it in the client hid the borrowed pins' tooltips
-- under it (all but those near you, on the minimap socket's higher level); Chrome.Unblock keeps them see-through.
local function Unblock(f)
	f:EnableMouse(false)
	f:EnableMouseWheel(false)
end
function Chrome.Unblock()
	Unblock(controls)
	Unblock(overlay)
end
Chrome.Unblock()

-- Where Blizzard's mail and crafting-order indicators (MinimapCluster.IndicatorFrame) hang while the takeover hides
-- their cluster (#23: View.chrome.indicators, game/Chrome.lua): the map's top right, as on Blizzard's minimap; on the
-- pills' frame, so at full alpha whatever Buttons at rest.
local indicators = CreateFrame("Frame", nil, overlay)
indicators:SetSize(1, 1)
indicators:SetPoint("TOPRIGHT", view, "TOPRIGHT", -3, -3)
Chrome.indicators = indicators

-- Everything of the template but its border's art goes; the map stops where that art begins.
local KEEP = { [view] = true, [band] = true, [grip] = true, [borders.metal] = true, [borders.tooltip] = true,
	[controls] = true, [overlay] = true }
for _, r in ipairs({ frame:GetRegions() }) do r:Hide() end
for _, c in ipairs({ frame:GetChildren() }) do
	if not KEEP[c] then c:Hide() end
end

-- The tooltip border's dark: on the frame, under the view, showing round its edge and behind the chamfered corners.
local backing = frame:CreateTexture(nil, "BACKGROUND")
backing:SetTexture(TOOLTIP_BG)
backing:SetVertexColor(unpack(TOOLTIP_BACKING))
backing:SetPoint("TOPLEFT", TOOLTIP_INSET, -TOOLTIP_INSET)
backing:SetPoint("BOTTOMRIGHT", -TOOLTIP_INSET, TOOLTIP_INSET)
Chrome.backing = backing

-- Who places by the border's insets (ui/Controls.lua: the zoom buttons, the quest pill): fn(insets), now and on each change.
local placed = {}
function Chrome.OnInsets(fn)
	placed[#placed + 1] = fn
	fn(Chrome.border.insets)
end

-- The view inside the border shown, short of the side's room on its right (Chrome.SetSide); under Blizzard's
-- minimap (Chrome.SetUnder, ui/Under.lua) no border is shown and the view is the whole window.
Chrome.side, Chrome.under = 0, false
local function PlaceView()
	view:ClearAllPoints()
	if Chrome.under then
		view:SetAllPoints()
		return
	end
	local insets = Chrome.border.insets
	view:SetPoint("TOPLEFT", insets[1], -insets[2])
	view:SetPoint("BOTTOMRIGHT", -insets[3] - Chrome.side, insets[4])
end

-- Settings > General > Map window > Border: "metal" (the client's frame) or "tooltip"; the view and all placed by it follow.
function Chrome.SetBorder(style)
	local shown = borders[style] or borders.metal
	for _, b in pairs(borders) do b:SetShown(b == shown and not Chrome.under) end
	backing:SetShown(shown == borders.tooltip and not Chrome.under)
	Chrome.border = shown
	PlaceView()
	for _, fn in ipairs(placed) do fn(shown.insets) end
end

-- Under Blizzard's minimap (ui/Under.lua): the border hidden, the view the whole window; off, as Border has it.
function Chrome.SetUnder(on)
	Chrome.under = on
	Chrome.border:SetShown(not on)
	backing:SetShown(not on and Chrome.border == borders.tooltip)
	PlaceView()
end

-- px kept on the view's right, inside the border, for a panel there (the big map's quest log: ui/QuestLog.lua); 0: none.
-- The map (and the controls and pills placed on it) narrows to leave it.
function Chrome.SetSide(px)
	if px == Chrome.side then return end
	Chrome.side = px
	PlaceView()
end
Chrome.SetBorder("metal")

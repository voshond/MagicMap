-- The big map's quest log: a panel down the map's right side, inside the border (the map narrows to leave it:
-- Chrome.SetSide), as Forever's world map lists your quests beside its map (QuestMapFrame's QuestScrollFrame:
-- Blizzard_UIPanels_Game/Mainline/QuestMapFrame.lua, Camelot's: no tabs, the count beside the title). Model.questlog
-- (game/parts/QuestLog.lua: Game reads it only while the big map is up), laid out again only when its rev changes
-- or a header is folded:
--   * a title band, "Quest Log" and how many quests of how many the log holds (red when over)
--   * a header a zone, its quests under it; a click folds or unfolds it (UI.saved.questCollapsed: by its name)
--   * a quest: its level and name in its difficulty's colour (the pins'), its icon (in progress, or ready to turn in),
--     the glow on the one you follow, a box ticked while it's in Blizzard's tracker (a click: the questwatch
--     Command), under it what it still needs (done: the log's completion line), and under that its rewards in a
--     line: small icons of what you choose from and what you get (hovered: the item's tooltip, the tooltip Command,
--     as the details'), the experience and the money
-- Hovering a quest lights its area on the map and shows its pin's tooltip (ui/QuestTooltip.lua), where it has a pin.
-- A click follows it (the follow Command: Blizzard's super-tracked quest) and flies the map there: to its pin, else
-- its zone whole, and opens its details in the panel (ui/QuestDetails.lua), in the list's place. A right-click:
-- Details, Track or Untrack, Follow or Stop following, Share, Abandon, Open in quest log.
-- The wheel scrolls it. The chevron at the map's top right puts it away and brings it back, as Settings > Tracking >
-- Quest log > Quest log on the big map does.

local _, ns = ...
local UI, Model, Atlas, Runtime = ns.UI, ns.Model, ns.Atlas, ns.Runtime
local Window, Chrome, Camera, Motion, Menus = UI.Window, UI.Chrome, UI.Camera, UI.Motion, UI.Menus
local Command = ns.Game.Command

local WIDTH = 300
local MIN_MAP = 400 -- px of map it leaves at least: a narrower big window has no quest log
local LEVEL = 500 -- over the frame's: under the border's (ui/Chrome.lua's 505), over the map's
local HEAD = 30 -- the title band
local HEADER_H, TITLE_H, LINE_H = 24, 18, 14
local PAD = 10
local TEXT_X = 26 -- a quest's name, past its icon
local LINE_X = 34 -- its objectives', past the dash
local CHECK = 14
local ICON = 16
local REWARD, REWARD_GAP, REWARD_H = 16, 3, 20 -- a reward's icon, between them, its line
local WHEEL = 3 * TITLE_H -- px a notch
local GOLD, WHITE, RED = { 1, 0.82, 0 }, { 1, 1, 1 }, { 1, 0.13, 0.13 }
local XP_COLOR = { 0.6, 0.6, 1 }
local LINE_GREY = 0.8
-- Blizzard's own art (QuestMapFrame.xml, ListTemplates.lua), each drawn only where the client has it.
local BACKGROUND, DIVIDER = "QuestLog-main-background", "QuestLog-frame-devider"
local CHECK_BOX, CHECK_MARK, GLOW = "questlog-icon-ticksquare", "questlog-icon-checkmark-yellow", "questlog-quest-glow-yellow"
local PLUS, MINUS = "common-button-list-plus", "common-button-list-minus"
local ACTIVE, TURN_IN = "Quest-In-Progress-Icon-yellow", "questturnin"

local QuestLog = { on = true }
UI.QuestLog = QuestLog

local function Has(atlas) return C_Texture.GetAtlasInfo(atlas) ~= nil end
local function Art(t, atlas)
	if Has(atlas) then t:SetAtlas(atlas) end
	return t
end

local frame = Window.frame
local panel = CreateFrame("Frame", nil, frame)
panel:SetFrameLevel(frame:GetFrameLevel() + LEVEL)
panel:SetWidth(WIDTH)
panel:EnableMouse(true) -- (the map under it takes no press)
panel:Hide()
QuestLog.panel = panel
Chrome.OnInsets(function(insets)
	panel:ClearAllPoints()
	panel:SetPoint("TOPRIGHT", -insets[3], -insets[2])
	panel:SetPoint("BOTTOMRIGHT", -insets[3], insets[4])
end)

local dark = panel:CreateTexture(nil, "BACKGROUND", nil, -2)
dark:SetAllPoints()
dark:SetColorTexture(0.06, 0.05, 0.04, 0.97)
Art(panel:CreateTexture(nil, "BACKGROUND", nil, -1), BACKGROUND):SetAllPoints()
local edge = panel:CreateTexture(nil, "BORDER")
edge:SetPoint("TOPLEFT")
edge:SetPoint("BOTTOMLEFT")
edge:SetWidth(2)
edge:SetColorTexture(0, 0, 0, 1)

local title = panel:CreateFontString(nil, "OVERLAY")
title:SetFontObject(GameFontNormal)
title:SetPoint("TOPLEFT", PAD, -9)
title:SetText("Quest Log")
local count = panel:CreateFontString(nil, "OVERLAY")
count:SetFontObject(GameFontNormalSmall)
count:SetPoint("TOPRIGHT", -PAD, -10)
QuestLog.title, QuestLog.count = title, count
QuestLog.WIDTH, QuestLog.HEAD, QuestLog.PAD, QuestLog.Art, QuestLog.Has = WIDTH, HEAD, PAD, Art, Has
local rule = Art(panel:CreateTexture(nil, "ARTWORK"), DIVIDER)
rule:SetPoint("TOPLEFT", 4, -HEAD + 6)
rule:SetPoint("TOPRIGHT", -4, -HEAD + 6)
rule:SetHeight(8)

local scroll = CreateFrame("ScrollFrame", nil, panel)
QuestLog.rule = rule
scroll:SetPoint("TOPLEFT", 0, -HEAD)
scroll:SetPoint("BOTTOMRIGHT", 0, 4)
scroll:EnableMouseWheel(true)
local content = CreateFrame("Frame", nil, scroll)
content:SetSize(WIDTH, 1)
scroll:SetScrollChild(content)
QuestLog.scroll, QuestLog.content = scroll, content

local function ScrollTo(y)
	local most = math.max(0, content:GetHeight() - scroll:GetHeight())
	scroll:SetVerticalScroll(math.max(0, math.min(most, y)))
end
scroll:SetScript("OnMouseWheel", Runtime.Wrap("map: quest log wheel", function(_, delta)
	ScrollTo(scroll:GetVerticalScroll() - delta * WHEEL)
end))

---------------------------------------------------------------------------
-- What a row does: fold a header; follow a quest and fly there; its menu; its box
---------------------------------------------------------------------------

local Layout -- (below)

local function Collapsed()
	local s = UI.saved
	s.questCollapsed = s.questCollapsed or {}
	return s.questCollapsed
end

-- Its pin (Known("quests"): the quests on your map's zones and the shown one's), if it has one.
local function Pin(id)
	for _, e in ipairs(Model.Known("quests")) do
		if e.quest == id then return e end
	end
end

-- The map to it: its pin, at the zoom you have, else its zone whole.
local function Fly(q)
	local e = Pin(q.id)
	local p = e and e.pos
	if p and p.col then
		Motion.SetFollow(false)
		Camera.inst = p.inst
		Motion.FlyTo(p.col, p.row, Camera.cam.zoom)
		return
	end
	local r = q.map and Atlas.MapRect(q.map)
	if not r then return end
	local m = Atlas.UiMap(q.map)
	Camera.inst = r.inst
	Motion.FlyToRect(r.col0, r.row0, r.col1, r.row1, m and m.name)
end
QuestLog.Fly = Fly

local Fits -- (below)

-- Quest id's details in this log (a pin's Open in quest log: ui/Track.lua): the map grown, the log brought back
-- if put away. A big window too narrow for it has the client's log instead.
function QuestLog.Open(id)
	local big = UI.BigMap
	if big.big and not big.Tweening() and not Fits(frame:GetWidth()) then
		return Command({ kind = "questlog", quest = id })
	end
	if not QuestLog.on then UI.Feel.Set("questlog.sidebar", true) end
	if not big.big then big.Toggle() end
	UI.QuestDetails.Open(id)
end

local function Watch(q) Command({ kind = "questwatch", quest = q.id, on = not q.watched }) end

local Pick = Runtime.Wrap("map: quest log pick", function(fn) fn() end)
local function Menu(owner, q)
	Menus.Show(owner, function(_, root)
		root:CreateTitle(q.title)
		root:CreateButton("Details", function() Pick(function() UI.QuestDetails.Open(q.id) end) end)
		root:CreateButton(q.watched and "Untrack" or "Track", function() Pick(function() Watch(q) end) end)
		root:CreateButton(q.followed and "Stop following" or "Follow", function()
			Pick(function() Command({ kind = "follow", quest = not q.followed and q.id }) end)
		end)
		root:CreateButton("Share", function() Pick(function() Command({ kind = "questshare", quest = q.id }) end) end)
		root:CreateButton("Abandon", function() Pick(function() Command({ kind = "questabandon", quest = q.id }) end) end)
		root:CreateDivider()
		root:CreateButton("Open in quest log", function() Pick(function() Command({ kind = "questlog", quest = q.id }) end) end)
	end)
end

local function Clicked(row, button)
	local r = row.data
	if not r then return end
	if r.header then
		local c = Collapsed()
		c[r.title] = not c[r.title] or nil
		Layout()
	elseif button == "RightButton" then
		Menu(row, r)
	else
		Command({ kind = "follow", quest = r.id })
		Fly(r)
		UI.QuestDetails.Open(r.id)
	end
end

local function Entered(row)
	local r = row.data
	if not r or r.header then return end
	row.hl:Show()
	local e = Pin(r.id)
	if not e then return end
	UI.Areas.Hover(e)
	GameTooltip:SetOwner(row, "ANCHOR_LEFT")
	UI.QuestTooltip.Fill(GameTooltip, e)
	GameTooltip:Show()
end

local function Left(row)
	row.hl:Hide()
	UI.Areas.Hover(nil)
	if GameTooltip:IsOwned(row) then GameTooltip:Hide() end
end

---------------------------------------------------------------------------
-- Rows: made as needed, reused
---------------------------------------------------------------------------

local rows = {}
QuestLog.rows = rows

-- The list (its title, count, rule and rows) shown, or put away while a quest's details take its place (its scroll kept).
function QuestLog.SetListShown(on)
	if not on then
		for _, row in ipairs(rows) do
			if row.hl:IsShown() then Left(row) end
			for _, b in ipairs(row.rewards) do
				if GameTooltip:IsOwned(b) then Command({ kind = "tooltip", owner = false }) end
			end
		end
	end
	title:SetShown(on)
	count:SetShown(on)
	rule:SetShown(on)
	scroll:SetShown(on)
end

local function NewRow()
	local row = CreateFrame("Button", nil, content)
	row:RegisterForClicks("LeftButtonUp", "RightButtonUp")
	row.hl = row:CreateTexture(nil, "BACKGROUND")
	row.hl:SetAllPoints()
	row.hl:SetColorTexture(1, 1, 1, 0.06)
	row.hl:Hide()
	row.glow = Art(row:CreateTexture(nil, "BACKGROUND", nil, 1), GLOW)
	row.glow:SetPoint("TOPLEFT", 2, 0)
	row.glow:SetPoint("TOPRIGHT", -2, 0)
	row.glow:SetHeight(TITLE_H + 2)
	row.icon = row:CreateTexture(nil, "ARTWORK")
	row.text = row:CreateFontString(nil, "ARTWORK")
	row.text:SetJustifyH("LEFT")
	row.text:SetWordWrap(false)
	local check = CreateFrame("Button", nil, row)
	check:SetSize(CHECK, CHECK)
	check:SetPoint("TOPRIGHT", -PAD, -2)
	Art(check:CreateTexture(nil, "ARTWORK"), CHECK_BOX):SetAllPoints()
	check.mark = Art(check:CreateTexture(nil, "OVERLAY"), CHECK_MARK)
	check.mark:SetAllPoints()
	check:SetScript("OnClick", Runtime.Wrap("map: quest log track", function(self)
		local r = self:GetParent().data
		if r and not r.header then Watch(r) end
	end))
	row.check = check
	row.lines = {}
	row.rewards = {}
	row.xp = row:CreateFontString(nil, "ARTWORK")
	row.xp:SetFontObject(GameFontHighlightSmall)
	row.xp:SetJustifyH("LEFT")
	row.xp:SetTextColor(XP_COLOR[1], XP_COLOR[2], XP_COLOR[3])
	row.money = row:CreateFontString(nil, "ARTWORK")
	row.money:SetFontObject(GameFontHighlightSmall)
	row.money:SetJustifyH("LEFT")
	row:SetScript("OnClick", Runtime.Wrap("map: quest log click", Clicked, Runtime.FRAME_MS))
	row:SetScript("OnEnter", Runtime.Wrap("map: quest log hover", Entered))
	row:SetScript("OnLeave", Runtime.Wrap("map: quest log left", Left))
	return row
end

local function Line(row, k)
	local fs = row.lines[k]
	if not fs then
		fs = row:CreateFontString(nil, "ARTWORK")
		fs:SetFontObject(GameFontHighlightSmall)
		fs:SetJustifyH("LEFT")
		fs:SetWordWrap(false)
		fs:SetPoint("TOPLEFT", LINE_X, -TITLE_H - (k - 1) * LINE_H)
		fs:SetPoint("TOPRIGHT", -PAD, -TITLE_H - (k - 1) * LINE_H) -- (TOPRIGHT, not RIGHT: a RIGHT would set its height too)
		row.lines[k] = fs
	end
	fs:Show()
	return fs
end

local function RewardEntered(self)
	Command({ kind = "tooltip", owner = self, anchor = "ANCHOR_LEFT",
		questItem = { kind = self.kind, index = self.index, quest = self.quest } })
end
local function RewardLeft() Command({ kind = "tooltip", owner = false }) end

local function Reward(row, k)
	local b = row.rewards[k]
	if not b then
		b = CreateFrame("Button", nil, row)
		b:SetSize(REWARD, REWARD)
		b:RegisterForClicks("LeftButtonUp", "RightButtonUp")
		b.icon = b:CreateTexture(nil, "ARTWORK")
		b.icon:SetAllPoints()
		b.count = b:CreateFontString(nil, "OVERLAY")
		b.count:SetFontObject(GameFontHighlightSmall)
		b.count:SetPoint("BOTTOMRIGHT", 2, -1)
		b:SetHighlightTexture("Interface\\Buttons\\UI-Common-MouseHilight", "ADD")
		b:SetScript("OnEnter", Runtime.Wrap("map: quest log reward", RewardEntered))
		b:SetScript("OnLeave", Runtime.Wrap("map: quest log reward left", RewardLeft))
		b:SetScript("OnClick", Runtime.Wrap("map: quest log reward click", function(self, button)
			Clicked(self:GetParent(), button)
		end, Runtime.FRAME_MS))
		row.rewards[k] = b
	end
	return b
end

-- fs showing str (false: hidden) at x on the line through mid; x past it.
local function Fact(fs, str, x, mid)
	fs:SetShown(str and true or false)
	if not str then return x end
	fs:ClearAllPoints()
	fs:SetPoint("LEFT", fs:GetParent(), "TOPLEFT", x, mid)
	fs:SetText(str)
	return x + fs:GetStringWidth() + 8
end

-- Quest r's rewards in a line at y under its name: the choices' and items' icons, its experience, its money; how
-- many icons it used.
local function Rewards(row, r, y)
	local w, n = r.rewards, 0
	local x = LINE_X
	for _, list in ipairs({ { w.choices, "choice" }, { w.items, "reward" } }) do
		for _, item in ipairs(list[1]) do
			n = n + 1
			local b = Reward(row, n)
			b.kind, b.index, b.quest = list[2], item.index, r.id
			b:ClearAllPoints()
			b:SetPoint("TOPLEFT", x, -y)
			b.icon:SetTexture(item.texture)
			b.count:SetText(item.count > 1 and item.count or "")
			b:Show()
			x = x + REWARD + REWARD_GAP
		end
	end
	local mid = -y - REWARD / 2
	if n > 0 then x = x + REWARD_GAP end
	x = Fact(row.xp, w.xp > 0 and (w.xp .. " XP"), x, mid)
	Fact(row.money, w.money > 0 and w.coins, x, mid)
	return n
end

local function HasRewards(w)
	return w and (#w.choices > 0 or #w.items > 0 or w.money > 0 or w.xp > 0)
end

local function Header(row, r)
	local folded = Collapsed()[r.title]
	row:SetHeight(HEADER_H)
	row.icon:ClearAllPoints()
	row.icon:SetPoint("CENTER", row, "LEFT", PAD + (ICON - 2) / 2, 0)
	local atlas = folded and PLUS or MINUS
	if Has(atlas) then row.icon:SetAtlas(atlas, true) end -- (its own size, as CollapseButtonMixin: the minus is a bar)
	row.icon:SetShown(Has(atlas))
	row.text:SetFontObject(GameFontHighlight)
	row.text:ClearAllPoints()
	row.text:SetPoint("LEFT", PAD + ICON + 4, 0)
	row.text:SetPoint("RIGHT", -PAD, 0)
	row.text:SetText(r.title)
	row.text:SetTextColor(WHITE[1], WHITE[2], WHITE[3])
	row.check:Hide()
	row.glow:Hide()
	row.xp:Hide()
	row.money:Hide()
	for _, b in ipairs(row.rewards) do b:Hide() end
	return HEADER_H
end

local function Quest(row, r)
	local c = r.failed and RED or r.color
	local name = r.level and ("[" .. r.level .. "] " .. r.title) or r.title
	if r.failed then name = name .. " (Failed)" end
	row.icon:ClearAllPoints()
	row.icon:SetPoint("TOPLEFT", PAD, -1)
	local atlas = r.complete and TURN_IN or ACTIVE
	Art(row.icon, atlas)
	row.icon:SetSize(ICON, ICON) -- (after SetAtlas: a header's left it at its atlas's size)
	row.icon:SetShown(not r.failed and Has(atlas))
	row.text:SetFontObject(GameFontNormal)
	row.text:ClearAllPoints()
	row.text:SetPoint("TOPLEFT", TEXT_X, -2)
	row.text:SetPoint("TOPRIGHT", row.check, "TOPLEFT", -4, 0)
	row.text:SetText(name)
	row.text:SetTextColor(c[1], c[2], c[3])
	row.check:Show()
	row.check.mark:SetShown(r.watched)
	row.glow:SetShown(r.followed and Has(GLOW))
	for k, o in ipairs(r.objectives) do
		local fs = Line(row, k)
		fs:SetText("- " .. o.text)
		local v = o.finished and 1 or LINE_GREY
		fs:SetTextColor(v, v, v)
	end
	local h = TITLE_H + #r.objectives * LINE_H + 4
	local used = 0
	if HasRewards(r.rewards) then
		used = Rewards(row, r, h - 1)
		h = h + REWARD_H
	else
		row.xp:Hide()
		row.money:Hide()
	end
	for k = used + 1, #row.rewards do row.rewards[k]:Hide() end
	row:SetHeight(h)
	return h
end

local laidRev -- the Model.questlog rev laid out
-- Each row set again only where it shows something else, or the same somewhere else (Model keeps a quest's row while
-- it's the same): a count going up touches its own row, those under it only move.
function Layout()
	local log = Model.questlog
	laidRev = log and log.rev
	local n, y, folded = 0, 0, false
	for _, r in ipairs(log or {}) do
		if r.header then folded = Collapsed()[r.title] == true end
		if r.header or not folded then
			n = n + 1
			local row = rows[n] or NewRow()
			rows[n] = row
			if row.data ~= r or (r.header and row.folded ~= folded) then
				for _, fs in ipairs(row.lines) do fs:Hide() end
				row.data, row.folded = r, r.header and folded
				row.h = r.header and Header(row, r) or Quest(row, r)
			end
			if row.top ~= y then
				row.top = y
				row:ClearAllPoints()
				row:SetPoint("TOPLEFT", content, "TOPLEFT", 0, -y)
				row:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, -y) -- (a RIGHT would centre it on the list: its height from the two)
			end
			y = y + row.h
			row:Show()
		end
	end
	for i = n + 1, #rows do
		rows[i].data, rows[i].top = nil, nil
		rows[i]:Hide()
	end
	content:SetHeight(math.max(1, y))
	ScrollTo(scroll:GetVerticalScroll())
	local quests, max = log and log.quests or 0, log and log.max
	local c = max and quests > max and RED or GOLD
	count:SetText(max and (quests .. "/" .. max) or tostring(quests))
	count:SetTextColor(c[1], c[2], c[3])
end
QuestLog.Layout = Layout

---------------------------------------------------------------------------
-- Shown on the big map once it's grown (and with it the room on the map's right), laid out as the log changes
---------------------------------------------------------------------------

-- px it takes off the map's right in a big window w wide: WIDTH, or 0 (off, or a window too narrow for it).
function Fits(w) return w - WIDTH >= MIN_MAP end
function QuestLog.Room(w)
	return QuestLog.on and Fits(w) and WIDTH or 0
end

-- The toggle: a chevron at the map's top right, on the zoom buttons' centre line, against the panel (Blizzard's spellbook page arrows): right, ">",
-- puts the panel away; left, "<", brings it out. The same setting as Settings' (questlog.sidebar). Shown on the big
-- map once grown, where the window has room for the panel.
local CHEVRON = "Interface\\Buttons\\UI-SpellbookIcon-%sPage-%s"
local TOGGLE = 26
local toggle = CreateFrame("Button", nil, Chrome.overlay)
toggle:SetSize(TOGGLE, TOGGLE)
toggle:SetPoint("CENTER", Chrome.overlay, "TOPRIGHT", -UI.Controls.COLUMN, -2 - TOGGLE / 2) -- (on the zoom buttons' line)
toggle:Hide()
QuestLog.toggle = toggle
local function ToggleLook()
	local way = QuestLog.on and "Next" or "Prev"
	toggle:SetNormalTexture(CHEVRON:format(way, "Up"))
	toggle:SetPushedTexture(CHEVRON:format(way, "Down"))
	toggle:SetHighlightTexture("Interface\\Buttons\\UI-Common-MouseHilight", "ADD")
	toggle.on = QuestLog.on
end
ToggleLook()
toggle:SetScript("OnClick", Runtime.Wrap("map: quest log toggle", function()
	UI.Feel.Set("questlog.sidebar", not QuestLog.on)
end, Runtime.FRAME_MS))
UI.Controls.Tip(toggle, function() return QuestLog.on and "Hide quest log" or "Show quest log" end)

Runtime.Step("ui", "map: quest log", function()
	local big = UI.BigMap
	local grown = big.big == true and (panel:IsShown() or not big.Tweening()) and Fits(frame:GetWidth())
	local want = grown and QuestLog.on
	if toggle:IsShown() ~= grown then toggle:SetShown(grown) end
	if toggle.on ~= QuestLog.on then ToggleLook() end
	if panel:IsShown() ~= want then
		panel:SetShown(want)
		Chrome.SetSide(want and WIDTH or 0)
	end
	if not want then return end
	local log = Model.questlog
	if (log and log.rev) ~= laidRev then Layout() end
end, { shownOnly = frame, budgetMs = Runtime.FRAME_MS }) -- (the first layout makes every row's widgets: the frame's budget)
-- Hidden while big comes back small (ui/BigMap.lua): the panel and its chevron go with it, not shown again with the window.
frame:HookScript("OnHide", Runtime.Wrap("map: quest log hidden", function()
	panel:Hide()
	toggle:Hide()
	Chrome.SetSide(0)
end))

UI.Feel.Add("tracking", "Quest log", {
	{ key = "questlog.sidebar", kind = "toggle", label = "Quest log on the big map", default = true,
		apply = function(v) QuestLog.on = v end,
		tip = "Your quests down the big map's right side, as Blizzard's world map lists them: click one to follow it and fly there, right-click for more." },
})

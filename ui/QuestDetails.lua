-- A quest's details in the big map's quest log, in the list's place inside UI.QuestLog.panel, as Blizzard's
-- QuestMapFrame.DetailsFrame shows them (QuestMapFrame_ShowQuestDetails, QuestInfo.lua): Model.questdetails (game/parts/QuestDetails.lua,
-- read for the quest we name with the questdetails Command), laid out again only when its rev changes:
--   * a band: a Back button (the list again, its scroll kept) and the quest's title
--   * a scroll: the title, "Quest Objectives" (what it asks and each objective, done ones greyed and ticked),
--     "Description", and "Rewards": what you choose one of, what you receive (an icon with its count, its name in its quality's
--     colour, two a row as QuestInfoRewardsFrame), money and experience; hovering a reward shows the item's tooltip (the tooltip Command)
--   * a bar: Abandon, Share (while the quest can be shared: you're in a group), Track or Untrack
-- Opened by a click on a quest in the list (ui/QuestLog.lua), shown once Game has read it; back to the list on Back, when the
-- quest leaves the log, or the panel is put away.

local _, ns = ...
local UI, Model, Runtime = ns.UI, ns.Model, ns.Runtime
local QuestLog, Window = UI.QuestLog, UI.Window
local Command = ns.Game.Command

local panel = QuestLog.panel
local WIDTH, HEAD, PAD, Art, Has = QuestLog.WIDTH, QuestLog.HEAD, QuestLog.PAD, QuestLog.Art, QuestLog.Has
local BAR = 36 -- the buttons' bar
local BUTTON_W, BUTTON_H, BUTTON_GAP, BUTTON_Y = 88, 22, 8, 7
local BACK = 22
local TEXT_W = WIDTH - 2 * PAD
local GAP, PARA = 6, 3 -- px under a text, between a quest's paragraphs
local ICON, CELL_H, COL_W = 36, 42, 140 -- a reward: its icon, its cell, two a row
local WHEEL = 54
local GOLD, BODY, WHITE = { 1, 0.82, 0 }, { 0.93, 0.89, 0.78 }, { 1, 1, 1 }
local DONE_GREY = 0.6
local DIVIDER, BACK_ATLAS = "QuestLog-frame-devider", "common-icon-backarrow"
local BACK_TEXTURE = "Interface\\Buttons\\UI-SpellbookIcon-PrevPage-%s"
local TICK = "|TInterface\\RaidFrame\\ReadyCheck-Ready:12|t "

local QuestDetails = {}
UI.QuestDetails = QuestDetails

local details = CreateFrame("Frame", nil, panel)
details:SetAllPoints()
details:Hide()
QuestDetails.frame = details

local back = CreateFrame("Button", nil, details)
back:SetSize(BACK, BACK)
back:SetPoint("TOPLEFT", PAD - 4, -4)
if Has(BACK_ATLAS) then
	back:SetNormalAtlas(BACK_ATLAS)
else
	back:SetNormalTexture(BACK_TEXTURE:format("Up"))
	back:SetPushedTexture(BACK_TEXTURE:format("Down"))
end
back:SetHighlightTexture("Interface\\Buttons\\UI-Common-MouseHilight", "ADD")
QuestDetails.back = back
UI.Controls.Tip(back, function() return "Back to the quest log" end)

local band = details:CreateFontString(nil, "OVERLAY")
band:SetFontObject(GameFontNormal)
band:SetJustifyH("LEFT")
band:SetWordWrap(false)
band:SetPoint("LEFT", back, "RIGHT", 4, 0)
band:SetPoint("RIGHT", details, "TOPRIGHT", -PAD, 0)
QuestDetails.band = band
local rule = Art(details:CreateTexture(nil, "ARTWORK"), DIVIDER)
rule:SetPoint("TOPLEFT", 4, -HEAD + 6)
rule:SetPoint("TOPRIGHT", -4, -HEAD + 6)
rule:SetHeight(8)

local view = CreateFrame("ScrollFrame", nil, details)
view:SetPoint("TOPLEFT", 0, -HEAD)
view:SetPoint("BOTTOMRIGHT", 0, BAR)
view:EnableMouseWheel(true)
local body = CreateFrame("Frame", nil, view)
body:SetSize(WIDTH, 1)
view:SetScrollChild(body)
QuestDetails.scroll, QuestDetails.body = view, body

local function ScrollTo(y)
	local most = math.max(0, body:GetHeight() - view:GetHeight())
	view:SetVerticalScroll(math.max(0, math.min(most, y)))
end
view:SetScript("OnMouseWheel", Runtime.Wrap("map: quest details wheel", function(_, delta)
	ScrollTo(view:GetVerticalScroll() - delta * WHEEL)
end))

---------------------------------------------------------------------------
-- The bar: what you can do with the quest
---------------------------------------------------------------------------

local function Action(label, slot, fn)
	local b = CreateFrame("Button", nil, details, "UIPanelButtonTemplate")
	b:SetSize(BUTTON_W, BUTTON_H)
	b:SetPoint("BOTTOMLEFT", PAD + slot * (BUTTON_W + BUTTON_GAP), BUTTON_Y)
	b:SetText(label)
	b:SetScript("OnClick", Runtime.Wrap("map: quest details " .. label, function()
		local d = Model.questdetails
		if d then fn(d) end
	end))
	return b
end
local abandon = Action("Abandon", 0, function(d) Command({ kind = "questabandon", quest = d.id }) end)
local share = Action("Share", 1, function(d) Command({ kind = "questshare", quest = d.id }) end)
local track = Action("Track", 2, function(d) Command({ kind = "questwatch", quest = d.id, on = not d.watched }) end)
QuestDetails.abandon, QuestDetails.share, QuestDetails.track = abandon, share, track

---------------------------------------------------------------------------
-- The scroll's contents: texts and rewards, made as needed, reused
---------------------------------------------------------------------------

local texts, items = {}, {}
QuestDetails.texts, QuestDetails.cells = texts, items
local y, textN, itemN = 0, 0, 0 -- the layout's cursor, and how many it has used

-- The next text, str in font and colour c, wrapped to the width left of x.
local function Text(str, font, c, x)
	textN = textN + 1
	local fs = texts[textN]
	if not fs then
		fs = body:CreateFontString(nil, "ARTWORK")
		fs:SetJustifyH("LEFT")
		fs:SetJustifyV("TOP")
		texts[textN] = fs
	end
	x = x or PAD
	fs:SetFontObject(font)
	fs:SetWidth(WIDTH - x - PAD)
	fs:ClearAllPoints()
	fs:SetPoint("TOPLEFT", body, "TOPLEFT", x, -y)
	fs:SetText(str)
	fs:SetTextColor(c[1], c[2], c[3])
	fs:Show()
	y = y + fs:GetStringHeight() + GAP
	return fs
end

local function Heading(str)
	y = y + GAP
	Text(str, GameFontNormalLarge, GOLD)
end

local function Paragraphs(str)
	for paragraph in str:gmatch("[^\n]+") do
		Text(paragraph, GameFontHighlight, BODY)
		y = y + PARA
	end
end

local function Entered(self)
	Command({ kind = "tooltip", owner = self, anchor = "ANCHOR_LEFT",
		questItem = { kind = self.kind, index = self.index, quest = self.quest } })
end
local function Left() Command({ kind = "tooltip", owner = false }) end

local function NewItem()
	local b = CreateFrame("Button", nil, body)
	b:SetSize(COL_W, CELL_H)
	b.icon = b:CreateTexture(nil, "ARTWORK")
	b.icon:SetSize(ICON, ICON)
	b.icon:SetPoint("TOPLEFT", 0, -2)
	b.count = b:CreateFontString(nil, "OVERLAY")
	b.count:SetFontObject(GameFontHighlightSmall)
	b.count:SetPoint("BOTTOMRIGHT", b.icon, "BOTTOMRIGHT", -2, 2)
	b.name = b:CreateFontString(nil, "ARTWORK")
	b.name:SetFontObject(GameFontNormalSmall)
	b.name:SetJustifyH("LEFT")
	b.name:SetWidth(COL_W - ICON - 8)
	b.name:SetPoint("LEFT", b.icon, "RIGHT", 6, 0)
	b:SetHighlightTexture("Interface\\Buttons\\UI-Common-MouseHilight", "ADD")
	b:SetScript("OnEnter", Runtime.Wrap("map: quest details item", Entered))
	b:SetScript("OnLeave", Runtime.Wrap("map: quest details item left", Left))
	return b
end

-- reward r (kind "reward" or "choice" of quest id) at column col of the row at the cursor.
local function Item(r, kind, id, col)
	itemN = itemN + 1
	local b = items[itemN] or NewItem()
	items[itemN] = b
	b.kind, b.index, b.quest = kind, r.index, id
	b:ClearAllPoints()
	b:SetPoint("TOPLEFT", body, "TOPLEFT", PAD + col * COL_W, -y)
	b.icon:SetTexture(r.texture)
	b.count:SetText(r.count > 1 and r.count or "")
	b.name:SetText(r.name)
	b.name:SetTextColor(r.color[1], r.color[2], r.color[3])
	b:Show()
end

-- list as rows of two, the cursor under them.
local function Grid(list, kind, id)
	for k, r in ipairs(list) do
		if k > 1 and k % 2 == 1 then y = y + CELL_H end
		Item(r, kind, id, (k - 1) % 2)
	end
	if #list > 0 then y = y + CELL_H + GAP end
end

local function Rewards(d)
	if #d.choices == 0 and #d.items == 0 and d.money <= 0 and d.xp <= 0 then return end
	Heading("Rewards")
	if #d.choices > 0 then
		Text("You will be able to choose one of these rewards:", GameFontHighlight, BODY)
		Grid(d.choices, "choice", d.id)
	end
	Text("You will receive:", GameFontHighlight, BODY)
	Grid(d.items, "reward", d.id)
	if d.money > 0 then Text("Money: " .. d.coins, GameFontHighlight, WHITE) end
	if d.xp > 0 then Text("Experience: " .. d.xp, GameFontHighlight, WHITE) end
end

local opened, seen -- the quest asked for; Game's read of it came
local laidRev, laidId -- the Model.questdetails rev laid out, and its quest

local function Fill(d)
	laidRev = d.rev
	y, textN, itemN = PAD, 0, 0
	band:SetText(d.title)
	Text(d.title, GameFontNormalLarge, GOLD)
	if d.objectivesText ~= "" or #d.objectives > 0 then
		Heading("Quest Objectives")
		Paragraphs(d.objectivesText)
		for _, o in ipairs(d.objectives) do
			if o.finished then
				Text(TICK .. o.text, GameFontHighlight, { DONE_GREY, DONE_GREY, DONE_GREY })
			else
				Text("- " .. o.text, GameFontHighlight, BODY)
			end
		end
	end
	if d.text ~= "" then
		Heading("Description")
		Paragraphs(d.text)
	end
	Rewards(d)
	for i = textN + 1, #texts do texts[i]:Hide() end
	for i = itemN + 1, #items do items[i]:Hide() end
	body:SetHeight(math.max(1, y + PAD))
	ScrollTo(laidId == d.id and view:GetVerticalScroll() or 0)
	laidId = d.id
	abandon:SetEnabled(d.canAbandon)
	share:SetEnabled(d.canShare)
	track:SetText(d.watched and "Untrack" or "Track")
end

---------------------------------------------------------------------------
-- Open, close
---------------------------------------------------------------------------

-- Back to the list; Game stops reading the quest.
function QuestDetails.Close()
	if not opened then return end
	for _, b in ipairs(items) do
		if GameTooltip:IsOwned(b) then GameTooltip:Hide() end
	end
	opened, seen, laidRev, laidId = nil, false, nil, nil
	details:Hide()
	QuestLog.SetListShown(true)
	Command({ kind = "questdetails", quest = false })
end

-- Ask Game for quest id's details: shown in the list's place once they're read.
function QuestDetails.Open(id)
	if opened == id then return end
	opened, seen, laidRev = id, false, nil
	Command({ kind = "questdetails", quest = id })
end

back:SetScript("OnClick", Runtime.Wrap("map: quest details back", QuestDetails.Close))
panel:HookScript("OnHide", Runtime.Wrap("map: quest details hidden", QuestDetails.Close))

Runtime.Step("ui", "map: quest details", function()
	if not opened then return end
	local d = Model.questdetails
	if not (d and d.id == opened) then
		if seen then QuestDetails.Close() end
		return
	end
	seen = true
	if d.rev ~= laidRev then Fill(d) end
	if not details:IsShown() then
		QuestLog.SetListShown(false)
		details:Show()
	end
end, { shownOnly = Window.frame, budgetMs = Runtime.FRAME_MS })

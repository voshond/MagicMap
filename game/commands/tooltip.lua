-- tooltip (types/view.lua MM.CmdTooltip): GameTooltip's own content for a game thing, on UI's owner.
-- member: a group member's tooltip, its name in its class's colour, then its level and class, dead, small and grey
-- (Game.TooltipFact: ui/Tip.lua's look; Layers.lua:677-688); button: a Minimap button's own (game/MinimapButtons.lua
-- Game.ButtonTooltip: the gear's Minimap buttons rows); questItem: a reward of a quest's details (the big map's quest
-- log: ui/QuestDetails.lua), the item's own tooltip (GameTooltip:SetQuestLogItem, the quest selected for it:
-- Game.WithSelectedQuest); owner false hides it again.

local _, ns = ...
local Game = ns.Game

local DEAD = "Dead"
local shown -- the owner a member's tooltip was shown on

local function Unit(id)
	local raid = IsInRaid()
	for i = 1, GetNumGroupMembers() do
		local unit = (raid and "raid" or "party") .. i
		if UnitGUID(unit) == id then return unit end
	end
end

local function Member(owner, anchor, id)
	local unit = Unit(id)
	if not unit then return end
	Game.Tooltip(owner, anchor or "ANCHOR_CURSOR")
	shown = owner
	local className, class = UnitClass(unit)
	local c, level = RAID_CLASS_COLORS[class], UnitLevel(unit)
	GameTooltip:AddLine(UnitName(unit), c.r, c.g, c.b)
	if level > 0 then Game.TooltipFact(LEVEL .. " " .. level .. " " .. className) end -- (-1: too high to tell)
	if UnitIsDeadOrGhost(unit) then Game.TooltipFact(DEAD) end
	GameTooltip:Show()
end

local function QuestItem(owner, anchor, item)
	Game.Tooltip(owner, anchor or "ANCHOR_RIGHT")
	shown = owner
	Game.WithSelectedQuest(item.quest, function() GameTooltip:SetQuestLogItem(item.kind, item.index) end)
	GameTooltip:Show()
end

Game.Handle("tooltip", function(c)
	if c.owner == false then
		if shown then Game.HideTooltip(shown) end
		Game.ButtonTooltip(false)
	elseif c.member then
		Member(c.owner, c.anchor, c.member)
	elseif c.questItem then
		QuestItem(c.owner, c.anchor, c.questItem)
	elseif c.button then
		Game.ButtonTooltip(c.owner, c.anchor, c.button)
	end
end)

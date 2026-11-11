-- obs.questdetails (types/observation.lua MM.ObsQuestDetails), on change: the details of the quest UI asked for (the
-- questdetails Command: Game.detailsQuest) as Blizzard's quest log shows them (QuestMapFrame_ShowQuestDetails,
-- QuestInfo.lua): its text and objectives, its rewards (what you choose from, what you get, money, experience), and
-- what you may do (abandon, share, track). Read only while the big map is up (Game.bigShown, as game/parts/QuestLog.lua),
-- a quest being asked for, on the frame it's asked and again 1 s after a burst of the log's events (or at once after
-- a watch changed). The client reads a quest's rewards and text through its selection (C_QuestLog.SetSelectedQuest):
-- Game.WithSelectedQuest selects it for a call and puts the one before back. A read that finds nothing new hands the
-- same table on; false: none asked for, or it isn't in the log (any more).

local _, ns = ...
local Game, Runtime = ns.Game, ns.Runtime

local DELAY = 1 -- s: as the list's (QUEST_LOG_UPDATE fires a lot)
local NONE = {}

local last = false -- the last handed over
local readId -- the quest it was
local dirty, pending = true, false
local wasBig

local function Due() pending, dirty = false, true end
local function Soon()
	if pending then return end
	pending = true
	Runtime.After(DELAY, "game.questdetails refresh", Due)
end
for _, event in ipairs({ "QUEST_LOG_UPDATE", "QUEST_REMOVED", "PLAYER_LEVEL_UP" }) do
	Runtime.On(event, "game.questdetails", Soon)
end
for _, event in ipairs({ "QUEST_WATCH_LIST_CHANGED", "GROUP_ROSTER_UPDATE" }) do
	Runtime.On(event, "game.questdetails", Due)
end

-- A watch changed by our own Command (game/commands/questwatch.lua): the list's read as well as this.
local listChanged = Game.QuestLogChanged
function Game.QuestLogChanged()
	if listChanged then listChanged() end
	dirty = true
end

-- fn(...) with quest id selected in the log (the client's rewards and text calls read the selected one), the selection
-- before back after; fn's results.
function Game.WithSelectedQuest(id, fn, ...)
	local get, set = C_QuestLog.GetSelectedQuest, C_QuestLog.SetSelectedQuest
	if not set then return fn(...) end
	local before = get and get()
	set(id)
	local ok, a, b, c = pcall(fn, ...)
	if before and before ~= id then set(before) end
	if not ok then error(a, 0) end
	return a, b, c
end

local WHITE = { 1, 1, 1 }
local COPPER_PER_SILVER, COPPER_PER_GOLD = 100, 10000

-- Reward k of the list n long, from info(k): name, texture, count, quality, usable, itemID; with its quality's colour.
local function Items(n, info)
	local out = {}
	for k = 1, n do
		local name, texture, count, quality, _, itemID = info(k)
		local c = ITEM_QUALITY_COLORS and ITEM_QUALITY_COLORS[quality or 1]
		if name then
			out[#out + 1] = { index = k, name = name, texture = texture, count = count or 1, quality = quality or 1, itemID = itemID,
				color = c and { c.r, c.g, c.b } or WHITE }
		end
	end
	return out
end

-- Money as the client writes it, its coins as icons; plain without it.
local function Coins(money)
	if money <= 0 then return "" end
	if C_CurrencyInfo and C_CurrencyInfo.GetCoinTextureString then return C_CurrencyInfo.GetCoinTextureString(money) end
	return ("%dg %ds %dc"):format(math.floor(money / COPPER_PER_GOLD),
		math.floor(money % COPPER_PER_GOLD / COPPER_PER_SILVER), money % COPPER_PER_SILVER)
end

-- Quest id's rewards (MM.ObsQuestRewards), read with it selected (Game.WithSelectedQuest): the list's rows have them too
-- (game/parts/QuestLog.lua).
function Game.QuestRewards(id)
	local money = GetQuestLogRewardMoney and GetQuestLogRewardMoney() or 0
	return { items = GetNumQuestLogRewards and GetQuestLogRewardInfo and Items(GetNumQuestLogRewards(), GetQuestLogRewardInfo) or {},
		choices = GetNumQuestLogChoices and GetQuestLogChoiceInfo and Items(GetNumQuestLogChoices(id, true), GetQuestLogChoiceInfo) or {},
		money = money, coins = Coins(money), xp = GetQuestLogRewardXP and GetQuestLogRewardXP() or 0 }
end

local function Read(id)
	local index = C_QuestLog.GetLogIndexForQuestID(id)
	if not index or index <= 0 then return false end
	local info = C_QuestLog.GetInfo and C_QuestLog.GetInfo(index)
	local text, objectivesText
	if GetQuestLogQuestText then text, objectivesText = GetQuestLogQuestText() end
	local objectives = {}
	for _, o in ipairs(C_QuestLog.GetQuestObjectives(id) or NONE) do
		objectives[#objectives + 1] = { text = o.text or "", finished = o.finished == true }
	end
	local r = Game.QuestRewards(id)
	return { id = id, title = C_QuestLog.GetTitleForQuestID(id) or info and info.title or "", level = info and info.level or 0,
		text = text or "", objectivesText = objectivesText or "", objectives = objectives, items = r.items, choices = r.choices,
		money = r.money, coins = r.coins, xp = r.xp,
		canAbandon = C_QuestLog.CanAbandonQuest(id) == true,
		canShare = C_QuestLog.IsPushableQuest and C_QuestLog.IsPushableQuest(id) == true and IsInGroup and IsInGroup() == true or false,
		watched = C_QuestLog.GetQuestWatchType(id) ~= nil, complete = C_QuestLog.IsComplete(id) == true }
end

-- Two reads the same: field for field, the lists' rows too.
local function Same(a, b)
	if type(a) ~= "table" or type(b) ~= "table" then return a == b end
	for k, v in pairs(a) do
		if not Same(v, b[k]) then return false end
	end
	for k in pairs(b) do
		if a[k] == nil then return false end
	end
	return true
end
Game.SameRead = Same

Game.Part("questdetails", function()
	local big = Game.bigShown == true
	if big and not wasBig then dirty = true end
	wasBig = big
	if not big then return last end
	local id = Game.detailsQuest
	if not id then
		readId, last = nil, false
		return false
	end
	if id == readId and not dirty then return last end
	readId, dirty = id, false
	local read = Game.WithSelectedQuest(id, Read, id)
	if not Same(read, last) then last = read end
	return last
end)

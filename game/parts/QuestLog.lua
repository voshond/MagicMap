-- obs.questlog (types/observation.lua MM.ObsQuestLog), on change: your whole quest log as Blizzard's world map
-- lists it beside the map (Forever's QuestMapFrame: Blizzard_UIPanels_Game/Mainline/QuestMapFrame.lua,
-- QuestLogQuests_Update): its headers (the zones), and under each its quests, but those it hides (tasks, hidden,
-- bounties not done: QuestLogQuests_ShouldShowQuestButton), each with its level, whether it's trivial, done or
-- failed, watched (Blizzard's tracker) and followed (super-tracked), its zone's map (GetQuestUiMapID) and its
-- objectives' lines (done: the log's completion text, else QUEST_WATCH_QUEST_READY); with how many quests are in
-- the log and how many it holds (QuestLogQuests_ShowQuestCount, Camelot's). Read only while the big map is up
-- (Game.bigShown: the sidebar's), again 1 s after a burst of the log's events, on the next frame once it's up or
-- after a watch changed (our track Command, QUEST_WATCH_LIST_CHANGED) or the super-tracked quest did. Each row is compared with its last as it's read and kept
-- if the same (a header by its name, a quest by its id), and the list too: a read that finds nothing new makes nothing.

local _, ns = ...
local Game, Runtime = ns.Game, ns.Runtime

local DELAY = 1 -- s: QUEST_LOG_UPDATE fires a lot (with every loot); a list beside the map needn't be faster
local NONE = {}

local list -- the last handed over
local dirty, pending = true, false
local followed, wasBig

local function Due() pending, dirty = false, true end
local function Soon()
	if pending then return end
	pending = true
	Runtime.After(DELAY, "game.questlog refresh", Due)
end
for _, event in ipairs({ "QUEST_LOG_UPDATE", "QUEST_ACCEPTED", "QUEST_REMOVED", "PLAYER_LEVEL_UP" }) do
	Runtime.On(event, "game.questlog", Soon)
end
Runtime.On("QUEST_WATCH_LIST_CHANGED", "game.questlog", Due)

-- A watch changed by our own Command (game/commands/questwatch.lua): read on the next frame.
function Game.QuestLogChanged() dirty = true end

-- The lines under a quest: its unfinished objectives (QuestLogQuests_AddQuestButton), or done, the one line; was (its
-- last) if the same.
local function Lines(id, index, complete, was)
	local out = {}
	if complete then
		local text = GetQuestLogCompletionText(index)
		out[1] = { text = text ~= nil and text ~= "" and text or QUEST_WATCH_QUEST_READY, finished = true }
	else
		for _, o in ipairs(C_QuestLog.GetQuestObjectives(id) or NONE) do
			if o.text and o.text ~= "" and not o.finished then out[#out + 1] = { text = o.text, finished = false } end
		end
	end
	if not was or #was ~= #out then return out end
	for k, o in ipairs(out) do
		if o.text ~= was[k].text or o.finished ~= was[k].finished then return out end
	end
	return was
end

local function Shown(info)
	return not (info.isTask or info.isHidden or info.isBounty and not C_QuestLog.IsComplete(info.questID))
end

local rows = {} -- quest ID or header title -> its row in list: kept while the same

-- Quest row r (as read) or was, its last, if the same.
local function Keep(r, was)
	if was and r.title == was.title and r.level == was.level and r.trivial == was.trivial and r.complete == was.complete
		and r.failed == was.failed and r.watched == was.watched and r.followed == was.followed and r.map == was.map
		and r.objectives == was.objectives then return was end
	return r
end

local function Read(super)
	local n, quests = C_QuestLog.GetNumQuestLogEntries()
	local consts = Constants and Constants.QuestLogConsts
	local out, header = { quests = quests or 0, max = consts and consts.MAXIMUM_NUM_QUESTS_LOG_CAN_ACCEPT }, nil
	local kept = {}
	for i = 1, n do
		local info = C_QuestLog.GetInfo(i)
		if info and info.isHeader then
			header = rows[info.title] or { header = true, title = info.title }
		elseif info and Shown(info) then
			if header then
				out[#out + 1] = header
				kept[header.title] = header
				header = nil
			end
			local id = info.questID
			local was = rows[id]
			local complete = C_QuestLog.IsComplete(id) == true
			local map = GetQuestUiMapID(id) or 0
			local r = Keep({ id = id, title = info.title, level = info.level > 0 and info.level or nil,
				trivial = C_QuestLog.IsQuestTrivial(id) == true, complete = complete, failed = C_QuestLog.IsFailed(id) == true,
				watched = C_QuestLog.GetQuestWatchType(id) ~= nil, followed = id == super, map = map > 0 and map or nil,
				objectives = Lines(id, i, complete, was and was.objectives) }, was)
			out[#out + 1] = r
			kept[id] = r
		end
	end
	rows = kept
	return out
end

-- Two reads the same: row for row the same tables (Keep's).
local function Same(a, b)
	if not (a and b) or #a ~= #b or a.quests ~= b.quests or a.max ~= b.max then return false end
	for i, x in ipairs(a) do
		if x ~= b[i] then return false end
	end
	return true
end

Game.Part("questlog", function()
	local big = Game.bigShown == true
	if big and not wasBig then dirty = true end -- (what came while it wasn't up)
	wasBig = big
	if not big then return list end
	local super = C_SuperTrack.GetSuperTrackedQuestID()
	if not dirty and super == followed then return list end
	dirty, followed = false, super
	local read = Read(super)
	if not Same(read, list) then list = read end
	return list
end)

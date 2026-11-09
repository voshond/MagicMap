-- Your quest log as the big map's sidebar lists it (obs.questlog: game/parts/QuestLog.lua): Model.questlog, its rows
-- handed on with each quest's colour (the quest log's difficulty colours: model/Quests.lua's, as its pin has it)
-- and rev, one more each time the log or your level changed (UI lays the sidebar out again only then); a row the same
-- as before (Game kept it) is the same table, coloured, while your level is. nil until Game first read it (the big
-- map first up).

local _, ns = ...
local Model = ns.Model

local log, level
local rev = 0
local built = setmetatable({}, { __mode = "k" }) -- Game's row -> its coloured copy, for the level it was made at

local WHITE = { 1, 1, 1 }

-- Game's quest row r with its colour: the last made for it if your level is the same.
local function Row(r)
	local b = built[r]
	if b and b.atLevel == level then return b end
	b = { atLevel = level }
	for k, v in pairs(r) do b[k] = v end
	b.color = r.level and Model.LogQuestColor(r.level, r.trivial) or WHITE
	built[r] = b
	return b
end

local function Build(raw)
	local out = { quests = raw.quests, max = raw.max, rev = rev }
	for i, r in ipairs(raw) do out[i] = r.header and r or Row(r) end
	return out
end

Model.Part(function(obs)
	local raw, lvl = obs.questlog, obs.you.level or level
	if not raw or raw == log and lvl == level then return end
	log, level, rev = raw, lvl, rev + 1
	Model.questlog = Build(raw)
end)

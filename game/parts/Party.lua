-- obs.party (types/observation.lua MM.ObsPartyMember[]), on change: your party's other members (your subgroup's in a
-- raid: party1-4, as QuestUtils_GetNumPartyMembersOnQuest) and which quests of your log (obs.questlog) each has
-- (C_QuestLog.IsUnitOnQuest), with what a quest's requirements are checked against (level, race, class:
-- model/Party.lua). Read only while the big map is up (the log's), on the frame the log changes or the roster does,
-- and 1 s after a burst of the members' own events (their logs, levels, coming online). A read that finds nothing
-- new hands the same table on. In no party, known and empty.

local _, ns = ...
local Game, Runtime = ns.Game, ns.Runtime

local DELAY = 1 -- s: as the log's (UNIT_QUEST_LOG_CHANGED fires with every kill a member makes)
local PARTY = { "party1", "party2", "party3", "party4" }

local list -- the last handed over
local log -- the obs.questlog it was read against
local dirty, pending = true, false
local wasBig

local function Due() pending, dirty = false, true end
local function Soon()
	if pending then return end
	pending = true
	Runtime.After(DELAY, "game.party refresh", Due)
end
for _, event in ipairs({ "UNIT_QUEST_LOG_CHANGED", "UNIT_LEVEL", "UNIT_CONNECTION" }) do
	Runtime.On(event, "game.party", function(_, unit)
		if unit ~= "player" then Soon() end
	end)
end
Runtime.On("GROUP_ROSTER_UPDATE", "game.party", Due)

-- Member unit, with the quests of rows it has.
local function Member(unit, rows)
	local _, class, classID = UnitClass(unit)
	local _, _, race = UnitRace(unit)
	local level = UnitLevel(unit) or 0
	local quests = {}
	for _, r in ipairs(rows) do
		if not r.header and C_QuestLog.IsUnitOnQuest(unit, r.id) then quests[r.id] = true end
	end
	return { id = UnitGUID(unit), name = UnitName(unit) or "?", class = class, classID = classID, race = race,
		level = level > 0 and level or nil, online = UnitIsConnected(unit) == true, quests = quests }
end

local function Read(rows)
	local out = {}
	for i = 1, math.min(GetNumSubgroupMembers(), #PARTY) do
		out[i] = Member(PARTY[i], rows)
	end
	return out
end

Game.Part("party", function(obs)
	local big = Game.bigShown == true
	if big and not wasBig then dirty = true end -- (what came while it wasn't up)
	wasBig = big
	local rows = obs.questlog
	if not big or not rows then return list end
	if not dirty and rows == log then return list end
	dirty, log = false, rows
	local read = Read(rows)
	if not Game.SameRead(read, list) then list = read end
	return list
end)

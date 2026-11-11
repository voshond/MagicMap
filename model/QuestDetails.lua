-- The details of the quest the big map's quest log opened (obs.questdetails: game/parts/QuestDetails.lua): Model.questdetails,
-- its fields handed on with rev, one more each time they changed (UI lays the details out again only then); false
-- when none is asked for or it left the log. nil until Game first read.

local _, ns = ...
local Model = ns.Model

local last
local rev = 0

Model.Part(function(obs)
	local raw = obs.questdetails
	if raw == nil or raw == last then return end
	last, rev = raw, rev + 1
	if not raw then
		Model.questdetails = false
		return
	end
	local out = { rev = rev }
	for k, v in pairs(raw) do out[k] = v end
	Model.questdetails = out
end)

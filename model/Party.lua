-- Your party's other members and the quests of your log each has (obs.party: game/parts/Party.lua): Model.party, the
-- list with rev, one more each time it changed; nil until Game first read it (the big map first up).
-- Model.PartyOnQuest(id): who has quest id (accepted), who could take it but hasn't (missing; offline: can't tell) and
-- who can't (ineligible: under its required level, or not its race or class, by Atlas's QuestieDB row), each in the
-- party's order. A quest Atlas lacks: nobody ineligible.

local _, ns = ...
local Atlas, Model = ns.Atlas, ns.Model

local last
local rev = 0

Model.Part(function(obs)
	local raw = obs.party
	if raw == nil or raw == last then return end
	last, rev = raw, rev + 1
	local out = { rev = rev }
	for i, m in ipairs(raw) do out[i] = m end
	Model.party = out
end)

-- Bit n - 1 of mask set (a QuestieDB races or classes mask); no mask (nil, 0) or no n: any.
local function Allows(mask, n)
	if not mask or mask == 0 or not n then return true end
	local bit = 2 ^ (n - 1)
	return mask % (bit * 2) >= bit
end

-- Why member m can't take quest q (its Atlas row); nil: it can, as far as Atlas knows.
local function Why(m, q)
	if not q then return nil end
	if q.requiredLevel and m.level and m.level < q.requiredLevel then
		return "level " .. m.level .. ", needs " .. q.requiredLevel
	end
	if not Allows(q.races, m.race) then return "wrong race" end
	if not Allows(q.classes, m.classID) then return "wrong class" end
end

function Model.PartyOnQuest(id)
	local out = { accepted = {}, missing = {}, ineligible = {} }
	local q = Atlas.Quest(id)
	for _, m in ipairs(Model.party or {}) do
		local e = { name = m.name, class = m.class }
		if m.quests[id] then
			out.accepted[#out.accepted + 1] = e
		else
			e.why = Why(m, q)
			local into = e.why and out.ineligible or out.missing
			if not e.why and not m.online then e.why = "offline" end
			into[#into + 1] = e
		end
	end
	return out
end

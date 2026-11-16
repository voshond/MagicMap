-- Who in your party has a quest (Model.PartyOnQuest: accepted, missing, ineligible), as the big map's quest log shows
-- it: beside a quest's name in the list, a class icon each (ui/QuestLog.lua: accepted bright, missing faded, ineligible
-- faded red) and its tooltip's lines; in a quest's details, a Party section (ui/QuestDetails.lua). A member's icon is
-- Blizzard's classicon-<class> (GetClassAtlas), else a square in its class colour; its name in its class colour, with
-- why it's ineligible (its level, race or class) or that it's offline.

local _, ns = ...
local UI, Model = ns.UI, ns.Model

local PartyQuest = {}
UI.PartyQuest = PartyQuest

PartyQuest.GROUPS = {
	{ key = "accepted", label = "Accepted", alpha = 1 },
	{ key = "missing", label = "Missing", alpha = 0.45, faded = true },
	{ key = "ineligible", label = "Ineligible", alpha = 0.6, faded = true, tint = { 1, 0.35, 0.35 } },
}
local WHITE = { r = 1, g = 1, b = 1, colorStr = "ffffffff" }
local NO_TINT = { 1, 1, 1 }
local LABEL, WHY = "|cffffd100%s:|r ", " |cff999999(%s)|r"
local INLINE = "|A:%s:%d:%d|a "

local function Color(class) return class and RAID_CLASS_COLORS[class] or WHITE end

local atlases = {} -- class token -> its classicon atlas, false: the client hasn't it
local function ClassAtlas(class)
	if not class then return nil end
	local atlas = atlases[class]
	if atlas == nil then
		atlas = "classicon-" .. class:lower()
		if not C_Texture.GetAtlasInfo(atlas) then atlas = false end
		atlases[class] = atlas
	end
	return atlas or nil
end

-- The party's rev (Model.party), nil before Game read it; whether you have anyone in it.
function PartyQuest.Rev() return Model.party and Model.party.rev end
function PartyQuest.Any() return Model.party ~= nil and #Model.party > 0 end

-- Texture t as member e's icon, in group g's look; left as it is if it has them already.
function PartyQuest.Icon(t, e, g)
	if t.class == e.class and t.look == g then return end
	t.class, t.look = e.class, g
	local atlas = ClassAtlas(e.class)
	if atlas then
		t:SetAtlas(atlas)
	else
		local c = Color(e.class)
		t:SetColorTexture(c.r, c.g, c.b)
	end
	local tint = g.tint or NO_TINT
	t:SetDesaturated(g.faded == true)
	t:SetVertexColor(tint[1], tint[2], tint[3], g.alpha)
end

-- Member e as text: its icon (size px) and name in its class colour, why after it.
function PartyQuest.Name(e, size)
	local atlas = ClassAtlas(e.class)
	local icon = atlas and INLINE:format(atlas, size, size) or ""
	local why = e.why and WHY:format(e.why) or ""
	return icon .. "|c" .. Color(e.class).colorStr .. e.name .. "|r" .. why
end

-- Quest id's party as lines, one a group with anyone in it ("Accepted: ..."); none out of a party.
function PartyQuest.Lines(id, size)
	local on, out = Model.PartyOnQuest(id), {}
	for _, g in ipairs(PartyQuest.GROUPS) do
		local names = {}
		for _, e in ipairs(on[g.key]) do names[#names + 1] = PartyQuest.Name(e, size) end
		if #names > 0 then out[#out + 1] = LABEL:format(g.label) .. table.concat(names, ", ") end
	end
	return out
end

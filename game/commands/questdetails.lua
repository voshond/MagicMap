-- questdetails (types/view.lua MM.CmdQuestDetails): which quest Game reads the details of for the big map's quest log
-- (game/parts/QuestDetails.lua); false: none. Idempotent: it only names the quest.

local _, ns = ...
local Game = ns.Game

Game.Handle("questdetails", function(c)
	Game.detailsQuest = c.quest or nil
end)

-- questabandon (types/view.lua MM.CmdQuestAbandon): the client's own Abandon Quest dialog for a quest, as the quest
-- log's Abandon (QuestMapQuestOptions_AbandonQuest: its items named, the dialog's Accept abandons it). Not
-- idempotent: each asks once.

local _, ns = ...
local Game = ns.Game

Game.Handle("questabandon", function(c)
	if not C_QuestLog.CanAbandonQuest(c.quest) then return end
	QuestMapQuestOptions_AbandonQuest(c.quest)
end)

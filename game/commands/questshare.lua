-- questshare (types/view.lua MM.CmdQuestShare): a quest shared with your group, as the quest log's Share
-- (QuestMapQuestOptions_ShareQuest: QuestLogPushQuest on its log index). Not idempotent: each shares once.

local _, ns = ...
local Game = ns.Game

Game.Handle("questshare", function(c)
	local index = C_QuestLog.GetLogIndexForQuestID(c.quest)
	if index and index > 0 then QuestLogPushQuest(index) end
end)

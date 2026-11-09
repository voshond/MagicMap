-- questwatch (types/view.lua MM.CmdQuestWatch): a quest in Blizzard's tracker or out of it, as the world map's quest
-- log's checkbox does (QuestMapQuestOptions_TrackQuest): no more than the tracker holds (MAX_QUEST_WATCHES, the
-- client's own error said). The quest log's sidebar reads the log again on the next frame (game/parts/QuestLog.lua).

local _, ns = ...
local Game = ns.Game

Game.Handle("questwatch", function(c)
	local id = c.quest
	local watched = C_QuestLog.GetQuestWatchType(id) ~= nil
	if c.on == watched then return end
	if not c.on then
		C_QuestLog.RemoveQuestWatch(id)
	elseif C_QuestLog.GetNumQuestWatches() >= Constants.QuestWatchConsts.MAX_QUEST_WATCHES then
		if UIErrorsFrame then UIErrorsFrame:AddMessage(OBJECTIVES_WATCH_TOO_MANY, 1.0, 0.1, 0.1, 1.0) end
		return
	else
		C_QuestLog.AddQuestWatch(id)
	end
	Game.QuestLogChanged()
end)

-- Keys Blizzard owns, caught for UI (types/view.lua HookedInput; spike MinimapMode.lua:130-133, 195-202):
--   M (ToggleWorldMap) while View.replace.worldmap (the user chose to replace the world map) and our window is
--     shown, or the minimap isn't replaced (then the window is hidden until M opens it big): the world map it
--     just opened is hidden again, and
--     UI hears "worldmap" (it grows or shrinks the window). M closing Blizzard's map (opened by L,
--     the quest log) is left alone.
--   L (ToggleQuestLog) while View.replace.questlog, the window as for M: the log it just opened (the world map
--     on a Retail-engine client, else the QuestLogFrame) is hidden again, and UI hears "questlog" (it opens the
--     big map with its quest log, or closes it). L closing Blizzard's and our own call
--     (Game.ToggleQuestLog: game/commands/questlog.lua, the client's log asked for) are left alone.
--   In combat hiding Blizzard's is blocked (spike-bugs K2), so M or L opening it while ours is small stashes
--     it instead: alpha 0, under ours as it grows (not if its strata is above ours: then it shows as usual).
--     The key again closes it (the client's own secure path) and ours with it. Ours shrinking otherwise in
--     combat shows the stashed one again; combat ending while ours is big hides it.
--   Escape while big: a catcher in UISpecialFrames is shown, and Escape closing it is "escape"
--   (the settings window, ui/Feel.lua, is named there too).
-- What's caught (game/Button.lua's "toggle" too) is handed over as obs.hooked, its own part:
-- everything since the last observe, each a constant table.
-- /mm check combat answers the M1 gate's question for the guard (the spike has none,
-- MinimapMode.lua:198-201): in combat, Blizzard's map open, it hides it once as M would and says
-- whether it hid and whether the client blocked us (a block is taint's too: game/Telemetry.lua).

local ADDON, ns = ...
local Game, Runtime = ns.Game, ns.Runtime

local INPUT = { worldmap = { kind = "worldmap" }, questlog = { kind = "questlog" }, escape = { kind = "escape" },
	toggle = { kind = "toggle" } }
local caught, handed = {}, {}
local shown, big = false, false -- the window, as the last apply read View
local override = false -- M is ours to take (View.replace.worldmap, and the window shown or the minimap not ours); else Blizzard's opens as it always does
local questlog = false -- L is ours to take (View.replace.questlog, the window as for M)
local passing = false -- our own ToggleQuestLog: the client's log is what's asked for

function Game.Hooked(kind) caught[#caught + 1] = INPUT[kind] end

Game.Part("hooked", function()
	caught, handed = wipe(handed), caught
	return handed
end)

local STRATA = { BACKGROUND = 1, LOW = 2, MEDIUM = 3, HIGH = 4, DIALOG = 5, FULLSCREEN = 6, FULLSCREEN_DIALOG = 7,
	TOOLTIP = 8 }
local stashed -- Blizzard's map or log opened in combat, left open but unseen under ours till combat ends

local function Stash(frame)
	if big or (STRATA[frame:GetFrameStrata()] or 4) > STRATA.HIGH then return false end
	frame:SetAlpha(0)
	stashed = frame
	return true
end

local function Unstash()
	if not stashed then return false end
	stashed:SetAlpha(1)
	stashed = nil
	return true
end

-- Hides what M or L just opened (in combat: stashes it); true when ours should hear the key.
local function Take(frame)
	if not InCombatLockdown() then
		HideUIPanel(frame)
		return true
	end
	return Stash(frame)
end

-- The key closed the client's own stashed one (its secure path): ours closes with it.
local function Closed()
	return stashed ~= nil and not stashed:IsShown() and Unstash()
end

hooksecurefunc("ToggleWorldMap", Runtime.Wrap("game: M", function()
	if not override then return end
	if not WorldMapFrame:IsShown() then
		if Closed() then Game.Hooked("worldmap") end
		return
	end
	if Take(WorldMapFrame) then Game.Hooked("worldmap") end
end))

function Game.ToggleQuestLog()
	passing = true
	ToggleQuestLog()
	passing = false
end

hooksecurefunc("ToggleQuestLog", Runtime.Wrap("game: L", function()
	if passing then passing = false; return end
	if not questlog then return end
	local log = WorldMapFrame:IsShown() and WorldMapFrame or QuestLogFrame and QuestLogFrame:IsShown() and QuestLogFrame
	if not log then
		if Closed() then Game.Hooked("questlog") end
		return
	end
	if Take(log) then Game.Hooked("questlog") end
end))

local catcher = CreateFrame("Frame", "MagicMapWorldMapEscape", UIParent) -- (UISpecialFrames takes names)
catcher:Hide()
tinsert(UISpecialFrames, catcher:GetName())
-- Hidden by Escape while big; Apply hides it only once big is over.
catcher:SetScript("OnHide", Runtime.Wrap("game: escape", function()
	if big then Game.Hooked("escape") end
end))
-- UI's settings window (ui/Feel.lua, made on its first open) closes on Escape too: the client reads the
-- name when Escape is pressed, so it's registered before the frame exists.
tinsert(UISpecialFrames, "MagicMapFeel")
-- The first-run welcome (ui/Welcome.lua): Escape closes it with nothing chosen.
tinsert(UISpecialFrames, "MagicMapWelcome")
-- A pin's popup (ui/Popup.lua): Escape closes it.
tinsert(UISpecialFrames, "MagicMapPopup")

Game.Apply("hooks", function(view)
	local w = view.window
	shown, big = w.shown, w.big
	local r = view.replace
	local ours = r ~= nil and (shown or r.minimap ~= true)
	override = ours and r.worldmap == true
	questlog = ours and r.questlog == true
	if catcher:IsShown() ~= big then catcher:SetShown(big) end
	-- A stash lasts while ours covers it in combat: after, it's hidden, or (still in combat) seen again.
	if not stashed or (big and stashed:IsShown() and InCombatLockdown()) then return end
	if stashed:IsShown() and not InCombatLockdown() then HideUIPanel(stashed) end
	Unstash()
end)

local probe -- a check waiting for the client's word: { hid, blocked }
local function Blocked(_, addon, fn)
	if probe and addon == ADDON then probe.blocked = tostring(fn) end
end
Runtime.On("ADDON_ACTION_BLOCKED", "game: check combat", Blocked)
Runtime.On("ADDON_ACTION_FORBIDDEN", "game: check combat", Blocked)
Game.Slash("check combat", "in combat, Blizzard's map open (M): is hiding it blocked? (M's guard, spike-bugs K2)", function()
	if not (InCombatLockdown() and WorldMapFrame:IsShown()) then
		return Game.Print("check combat: in combat, open Blizzard's map (M), then again")
	end
	probe = {}
	HideUIPanel(WorldMapFrame)
	probe.hid = not WorldMapFrame:IsShown()
	Runtime.After(1, "game: check combat", function()
		Runtime.Trace("check", { e = "combat", hid = probe.hid, blocked = probe.blocked or false })
		Game.Print(string.format("check combat: HideUIPanel(WorldMapFrame) %s; the client %s", probe.hid and "hid it" or
			"left it open", probe.blocked and ("blocked " .. probe.blocked) or "blocked nothing"))
		probe = nil
	end)
end)

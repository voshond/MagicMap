"""A quest's details in the big map's quest log (ui/QuestDetails.lua, game/parts/QuestDetails.lua, model/QuestDetails.lua,
the questdetails Command and the tooltip Command's questItem) on the simulated client, as Blizzard's QuestMapFrame.DetailsFrame
shows a quest:

  test_questdetails_observation: Game reads a quest's details only while the big map is up and one is asked for (the
    questdetails Command): its text, objectives, rewards, choices, money, experience and what you may do; the client's
    selected quest put back after each read; a read that finds nothing new hands the same table on, a change a new
    one; a quest that left the log reads false; Model.questdetails has it with a rev that moves only on change.
  test_questdetails_panel: a click on a quest (still following it) shows its details in the list's place: the title, Quest
    Objectives, Description and Rewards in order, the rewards two a row with their count and quality colour, money and
    experience; Back returns to the list, its scroll kept; the panel put away returns to the list for next time; a
    quest abandoned (gone from the log) returns to the list; the right-click menu's Details opens it too.
  test_questdetails_buttons: Abandon, Share and Track send their Commands; Abandon is enabled by what the quest allows,
    Share by a group and a pushable quest, Track says Untrack while it's tracked.
  test_questdetails_tooltip: hovering a reward shows the item's tooltip through the tooltip Command, the selected quest
    put back; leaving hides it.
"""
from test_addon import errors
from test_quests import CANDLES, FRONTIER, LOVERS, client
from test_questlog import big, row, seq

DETAILS = """local Sim = ...
local q = Sim.quests[60]
q.text = "Bring me 8 candles.\\nI mean it."
q.objectivesText = "Gather the candles from the kobolds."
q.objectives[2] = { text = "Find the mine", type = "event", finished = true, numFulfilled = 1, numRequired = 1 }
q.rewards = { { name = "Large Candle", texture = 133750, count = 5, quality = 1, itemID = 772 },
	{ name = "Gold-Trimmed Cloak", texture = 133001, count = 1, quality = 2, itemID = 1001 } }
q.choices = { { name = "Rusty Dagger", texture = 135641, count = 1, quality = 1, itemID = 1002 },
	{ name = "Kobold Mace", texture = 135321, count = 1, quality = 3, itemID = 1003 } }
q.money, q.xp = 12500, 450
Sim.selectedQuest = 52
Sim.selects = 0
local set = C_QuestLog.SetSelectedQuest
C_QuestLog.SetSelectedQuest = function(id) Sim.selects = Sim.selects + 1; return set(id) end
for id = 1000, 1030 do -- (a list longer than the panel: it scrolls)
	Sim.quests[id] = { title = "Filler " .. id, level = 5, map = 1429, x = 0.5, y = 0.5, complete = false, objectives = {} }
	Sim.watches[id] = false -- (the tracker holds 25)
end"""

GOLD_ICON = "|TInterface\\MoneyFrame\\UI-GoldIcon:0:0:2:0|t"
SILVER_ICON = "|TInterface\\MoneyFrame\\UI-SilverIcon:0:0:2:0|t"
TICK = "|TInterface\\RaidFrame\\ReadyCheck-Ready:12|t "


def setup(shown=True):
    L, sim, ns, G = client([CANDLES, FRONTIER, LOVERS])
    L.execute(DETAILS, sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    if shown:
        big(sim)
    return L, sim, ns, G


def ask(ns, L, quest):
    ns.Game.Command(L.table_from({"kind": "questdetails", "quest": quest}))


def shown_texts(ns):
    return [fs.GetText(fs) for fs in seq(ns.UI.QuestDetails.texts) if fs.IsShown(fs)]


def shown_items(ns):
    return [b for b in seq(ns.UI.QuestDetails.cells) if b.IsShown(b)]


def open_candles(ns, sim):
    sim.Click(row(ns, "[7] Kobold Candles"))
    sim.Run(0.3)


def test_questdetails_observation():
    L, sim, ns, G = setup(shown=False)
    same = L.eval("function(a, b) return rawequal(a, b) end")
    ask(ns, L, 60)
    sim.Run(1.5)
    assert ns.Game.obs.questdetails is False and sim.selects == 0  # small: nothing read
    big(sim)
    d = ns.Game.obs.questdetails
    assert d and d.id == 60 and d.title == "Kobold Candles" and d.level == 7 and not d.complete
    assert d.text == "Bring me 8 candles.\nI mean it." and d.objectivesText == "Gather the candles from the kobolds."
    assert [(o.text, o.finished) for o in seq(d.objectives)] == [("Large Candle: 3/8", False), ("Find the mine", True)]
    assert [(r.index, r.name, r.count, r.quality, r.itemID) for r in seq(d["items"])] == [
        (1, "Large Candle", 5, 1, 772), (2, "Gold-Trimmed Cloak", 1, 2, 1001)]
    assert [(r.name, r.quality) for r in seq(d.choices)] == [("Rusty Dagger", 1), ("Kobold Mace", 3)]
    assert d.money == 12500 and d.xp == 450 and d.canAbandon and not d.canShare and d.watched
    assert sim.selectedQuest == 52 and sim.selects >= 2  # (read through the selection, put back)
    model = ns.Model.questdetails
    assert model.id == 60 and model.rev >= 1
    # Nothing new: the same table, the same rev; a change: a new one.
    selects, rev = sim.selects, model.rev
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    assert same(ns.Game.obs.questdetails, d) and ns.Model.questdetails.rev == rev and sim.selects > selects
    L.execute("local Sim = ...; Sim.quests[60].xp = 500", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    assert not same(ns.Game.obs.questdetails, d) and ns.Game.obs.questdetails.xp == 500
    assert ns.Model.questdetails.rev == rev + 1 and sim.selectedQuest == 52
    # A quest that left the log: false; none asked for: false.
    L.execute("local Sim = ...; Sim.quests[60] = nil", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    assert ns.Game.obs.questdetails is False and ns.Model.questdetails is False
    ask(ns, L, False)
    sim.Run(0.2)
    assert ns.Game.obs.questdetails is False
    # The big map down: nothing read, whatever is asked.
    L.execute("local Sim = ...; Sim.quests[60] = { title = 'Kobold Candles', level = 7, map = 1429, x = 0.3, y = 0.5, complete = false, objectives = {} }", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    ns.UI.Window.frame.Hide(ns.UI.Window.frame)
    sim.Run(0.5)
    selects = sim.selects
    ask(ns, L, 60)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(2)
    assert sim.selects == selects
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_questdetails_panel():
    L, sim, ns, G = setup()
    UI = ns.UI
    ql, dq = UI.QuestLog, UI.QuestDetails
    assert not dq.frame.IsShown(dq.frame) and ql.scroll.IsShown(ql.scroll)
    ql.scroll.SetVerticalScroll(ql.scroll, 40)
    assert ql.scroll.GetVerticalScroll(ql.scroll) == 40
    open_candles(ns, sim)
    assert sim.superTracked == 60  # (the click still follows it)
    assert dq.frame.IsShown(dq.frame) and not ql.scroll.IsShown(ql.scroll) and not ql.title.IsShown(ql.title)
    assert not ql.count.IsShown(ql.count) and ql.panel.IsShown(ql.panel)
    assert dq.band.GetText(dq.band) == "Kobold Candles"
    money = "Money: 1" + GOLD_ICON + " 25" + SILVER_ICON
    assert shown_texts(ns) == [
        "Kobold Candles", "Quest Objectives", "Gather the candles from the kobolds.", "- Large Candle: 3/8",
        TICK + "Find the mine", "Description", "Bring me 8 candles.", "I mean it.", "Rewards",
        "You will be able to choose one of these rewards:", "You will receive:", money, "Experience: 450"]
    # The finished objective greyed; the body in a light colour, the headings gold.
    texts = {fs.GetText(fs): fs for fs in seq(dq.texts) if fs.IsShown(fs)}
    assert tuple(texts[TICK + "Find the mine"].GetTextColor(texts[TICK + "Find the mine"]))[:3] == (0.6, 0.6, 0.6)
    assert tuple(texts["Description"].GetTextColor(texts["Description"]))[:3] == (1, 0.82, 0)
    assert tuple(texts["I mean it."].GetTextColor(texts["I mean it."]))[0] > 0.9
    # Rewards: the choices, then what you receive, two a row, a count at the corner, the name in its quality's colour.
    items = shown_items(ns)
    assert [b.name.GetText(b.name) for b in items] == ["Rusty Dagger", "Kobold Mace", "Large Candle", "Gold-Trimmed Cloak"]
    assert [(b.kind, b.index, b.quest) for b in items] == [("choice", 1, 60), ("choice", 2, 60), ("reward", 1, 60), ("reward", 2, 60)]
    at = [b.GetPoint(b, 1) for b in items]
    assert at[0][3] == at[2][3] == 10 and at[1][3] == at[3][3] == 150 and at[0][4] == at[1][4] and at[2][4] == at[3][4]
    assert at[2][4] < at[0][4] and sim.state[items[0].icon].width == 36
    assert items[2].count.GetText(items[2].count) == "5" and not items[3].count.GetText(items[3].count)
    assert tuple(items[1].name.GetTextColor(items[1].name))[:3] == (0, 0.44, 0.87)
    assert tuple(items[3].name.GetTextColor(items[3].name))[:3] == (0.12, 1, 0)
    assert dq.body.GetHeight(dq.body) > 300
    # Back: the list, its scroll where it was; nothing asked of Game any more.
    sim.Click(dq.back)
    sim.Run(0.2)
    assert not dq.frame.IsShown(dq.frame) and ql.scroll.IsShown(ql.scroll) and ql.title.IsShown(ql.title)
    assert ql.scroll.GetVerticalScroll(ql.scroll) == 40 and ns.Game.detailsQuest is None
    sim.Run(1.5)
    assert ns.Game.obs.questdetails is False and not dq.frame.IsShown(dq.frame)
    # The map put away and back: the list.
    open_candles(ns, sim)
    assert dq.frame.IsShown(dq.frame)
    f = UI.Window.frame
    f.Hide(f)
    sim.Run(0.1)
    assert not dq.frame.IsShown(dq.frame) and ns.Game.detailsQuest is None
    f.Show(f)
    sim.Run(0.2)
    big(sim)
    assert ql.panel.IsShown(ql.panel) and ql.scroll.IsShown(ql.scroll) and not dq.frame.IsShown(dq.frame)
    # The right-click menu's Details opens a quest too (without following it).
    sim.FireScript(row(ns, "[11] Protect the Frontier"), "OnClick", "RightButton", False)
    assert [e.text for e in sim.menu["items"].values()][1] == "Details"
    sim.Pick(next(e for e in sim.menu["items"].values() if e.text == "Details"))
    sim.Run(0.3)
    assert dq.frame.IsShown(dq.frame) and dq.band.GetText(dq.band) == "Protect the Frontier" and sim.superTracked == 60
    assert shown_texts(ns)[:3] == ["Protect the Frontier", "Quest Objectives", "- Prowler slain: 2/8"]
    # The quest abandoned (gone from the log): back to the list.
    L.execute("local Sim = ...; Sim.quests[52] = nil", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(2)
    assert not dq.frame.IsShown(dq.frame) and ql.scroll.IsShown(ql.scroll) and ns.Game.detailsQuest is None
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_questdetails_buttons():
    L, sim, ns, G = setup()
    dq = ns.UI.QuestDetails
    open_candles(ns, sim)
    assert dq.abandon.IsEnabled(dq.abandon) and not dq.share.IsEnabled(dq.share)
    assert dq.abandon.GetText(dq.abandon) == "Abandon" and dq.share.GetText(dq.share) == "Share"
    assert dq.track.GetText(dq.track) == "Untrack"
    # Share: a pushable quest and a group.
    L.execute("local Sim = ...; Sim.quests[60].pushable = true", sim)
    sim.FireEvent("QUEST_LOG_UPDATE")
    sim.Run(1.5)
    assert not dq.share.IsEnabled(dq.share)
    sim.group = L.table_from(["party1"])
    sim.FireEvent("GROUP_ROSTER_UPDATE")
    sim.Run(0.3)
    assert dq.share.IsEnabled(dq.share)
    sim.Click(dq.share)
    sim.Run(0.1)
    assert sim.pushed == G.C_QuestLog.GetLogIndexForQuestID(60)
    sim.Click(dq.abandon)
    sim.Run(0.1)
    assert sim.abandonAsked == 60
    # Track: out of the tracker and the button says so; again, in.
    sim.Click(dq.track)
    sim.Run(0.3)
    assert sim.watches[60] is False and dq.track.GetText(dq.track) == "Track"
    sim.Click(dq.track)
    sim.Run(0.3)
    assert sim.watches[60] and dq.track.GetText(dq.track) == "Untrack"
    # A quest that can't be abandoned: its button off.
    L.execute("local Sim = ...; C_QuestLog.CanAbandonQuest = function() return false end", sim)
    sim.FireEvent("QUEST_WATCH_LIST_CHANGED")
    sim.Run(0.3)
    assert not dq.abandon.IsEnabled(dq.abandon)
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_questdetails_tooltip():
    L, sim, ns, G = setup()
    dq, tip, S = ns.UI.QuestDetails, G.GameTooltip, sim.state
    open_candles(ns, sim)
    items = shown_items(ns)
    sim.FireScript(items[1], "OnEnter", False)
    sim.Step()
    assert S[tip].shown and tip.GetOwner(tip) is not None and S[tip.GetLeftLine(tip, 1)].text == "Kobold Mace"
    assert list(S[tip.GetLeftLine(tip, 1)].textColor.values()) == [0, 0.44, 0.87]
    assert sim.selectedQuest == 52  # (the client's selection put back)
    sim.FireScript(items[1], "OnLeave", False)
    sim.Step()
    assert not S[tip].shown
    sim.FireScript(items[2], "OnEnter", False)
    sim.Step()
    assert S[tip].shown and S[tip.GetLeftLine(tip, 1)].text == "Large Candle" and sim.selectedQuest == 52
    sim.Click(dq.back)
    sim.Run(0.2)
    assert not S[tip].shown
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_questlog_rewards_line():
    """The list's rows show each quest's rewards in a line under its objectives: the choices' then the items' icons
    (hovered: the item's tooltip, the selection put back), its experience and its money; a quest with none has no line."""
    L, sim, ns, G = setup()
    tip, S = G.GameTooltip, sim.state
    candles, frontier = row(ns, "[7] Kobold Candles"), row(ns, "[11] Protect the Frontier")
    icons = [b for b in seq(candles.rewards) if b.IsShown(b)]
    assert [(b.kind, b.index) for b in icons] == [("choice", 1), ("choice", 2), ("reward", 1), ("reward", 2)]
    assert [S[b.icon].texture for b in icons] == [135641, 135321, 133750, 133001]
    assert icons[2].count.GetText(icons[2].count) == "5" and icons[0].count.GetText(icons[0].count) == ""
    assert candles.xp.GetText(candles.xp) == "450 XP" and candles.xp.IsShown(candles.xp)
    assert candles.money.GetText(candles.money) == "1" + GOLD_ICON + " 25" + SILVER_ICON
    assert abs(sim.state[candles].height - (18 + 14 + 4 + 20)) < 1e-6
    assert all(abs(b.GetTop(b) - icons[0].GetTop(icons[0])) < 1e-6 for b in icons)  # (all in a line)
    assert icons[0].GetTop(icons[0]) <= candles.GetTop(candles) - 18 - 14  # (under its objective)
    assert not any(b.IsShown(b) for b in seq(frontier.rewards)) and not frontier.xp.IsShown(frontier.xp)
    assert abs(sim.state[frontier].height - (18 + 14 + 4)) < 1e-6
    selects = sim.selects
    sim.FireScript(icons[3], "OnEnter", False)
    sim.Step()
    assert S[tip].shown and S[tip.GetLeftLine(tip, 1)].text == "Gold-Trimmed Cloak" and sim.selectedQuest == 52
    assert sim.selects > selects
    sim.FireScript(icons[3], "OnLeave", False)
    sim.Step()
    assert not S[tip].shown
    # A click on an icon is the row's: its details.
    sim.Click(icons[0])
    sim.Run(0.3)
    assert ns.UI.QuestDetails.frame.IsShown(ns.UI.QuestDetails.frame)
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))

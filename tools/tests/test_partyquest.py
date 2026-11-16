"""Who in your party has a quest (game/parts/Party.lua, model/Party.lua, ui/PartyQuest.lua) in the big map's quest log
on the simulated client:

  test_party_observation: Game reads the party's quests only while the big map is up (C_QuestLog.IsUnitOnQuest, for
    the log's quests), with each member's class, race, level and whether it's online; a read that finds nothing new
    hands the same table on; Model.PartyOnQuest sorts the party into accepted, missing (offline: said) and ineligible
    (under the quest's required level, or not its class: Atlas's row).
  test_party_list: beside a quest's name in the list, a class icon each, accepted bright nearest the name, missing
    faded, ineligible faded red; hovering the quest adds who has it to its tooltip; out of a party, none.
  test_party_details: a quest's details have a Party section (after its objectives), laid out again when a member picks the quest up, and
    gone out of a party.
"""
from test_addon import errors
from test_questdetails import open_candles, shown_texts
from test_questlog import big, row, seq
from test_quests import CANDLES, FRONTIER, LOVERS, client

PARTY = {
    "party1": {"name": "Brannock", "class": "WARRIOR", "classID": 1, "raceID": 3, "level": 9,
               "guid": "Player-1-0A1B2C3D", "quests": {60: True, 52: True}},
    "party2": {"name": "Elandra", "class": "PRIEST", "classID": 5, "raceID": 1, "level": 4,
               "guid": "Player-1-0A1B2C3E", "quests": {}},
    "party3": {"name": "Thorn", "class": "ROGUE", "classID": 4, "raceID": 1, "level": 8,
               "guid": "Player-1-0A1B2C3F", "quests": {}, "offline": True},
}

# Kobold Candles needs level 5; Young Lovers is for warriors alone (classes mask: bit 1 - 1).
RULES = """local Sim, ns = ...
local rules = { [60] = { requiredLevel = 5 }, [106] = { classes = 1 } }
local quest = ns.Atlas.Quest
ns.Atlas.Quest = function(id)
	local row = quest(id) or { finishedBy = { npcs = {}, objects = {} } }
	for k, v in pairs(rules[id] or {}) do row[k] = v end
	return row
end"""


def label(group, names):
    return f"|cffffd100{group}:|r " + ", ".join(names)


def name(n, why=None):
    return f"|cffffffff{n}|r" + (f" |cff999999({why})|r" if why else "")


def setup():
    L, sim, ns, G = client([CANDLES, FRONTIER, LOVERS])
    L.execute(RULES, sim, ns)
    for unit, m in PARTY.items():
        sim.units[unit] = L.table_from({k: L.table_from(v) if isinstance(v, dict) else v for k, v in m.items()})
    sim.group = L.table_from(list(PARTY))
    sim.FireEvent("GROUP_ROSTER_UPDATE")
    sim.Run(1.5)
    return L, sim, ns, G


def names(entries):
    return [(e.name, e.why) for e in seq(entries)]


def test_party_observation():
    L, sim, ns, G = setup()
    assert ns.Game.obs.party is None  # small: not read
    big(sim)
    party = ns.Game.obs.party
    assert [(m.name, m["class"], m.classID, m.race, m.level, m.online) for m in seq(party)] == [
        ("Brannock", "WARRIOR", 1, 3, 9, True), ("Elandra", "PRIEST", 5, 1, 4, True), ("Thorn", "ROGUE", 4, 1, 8, False)]
    assert sorted(party[1].quests.keys()) == [52, 60] and list(party[2].quests.keys()) == []
    sim.FireEvent("UNIT_QUEST_LOG_CHANGED", "party2")
    sim.Run(1.5)
    assert L.eval("rawequal")(ns.Game.obs.party, party)  # nothing new: the same table
    on = ns.Model.PartyOnQuest(60)
    assert names(on.accepted) == [("Brannock", None)]
    assert names(on.missing) == [("Thorn", "offline")]
    assert names(on.ineligible) == [("Elandra", "level 4, needs 5")]
    on = ns.Model.PartyOnQuest(106)
    assert names(on.accepted) == [] and names(on.missing) == [("Brannock", None)]
    assert names(on.ineligible) == [("Elandra", "wrong class"), ("Thorn", "wrong class")]
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_party_list():
    L, sim, ns, G = setup()
    big(sim)
    r = row(ns, "[7] Kobold Candles")
    icons = [t for t in seq(r.members) if t.IsShown(t)]
    S = sim.state
    # Right to left from the box: Elandra (ineligible), Thorn (missing), Brannock (accepted, nearest the name).
    looks = [(S[t].desaturated, t.GetVertexColor(t)) for t in icons]
    assert looks == [(True, (1, 0.35, 0.35, 0.6)), (True, (1, 1, 1, 0.45)), (False, (1, 1, 1, 1))]
    assert [tuple(S[t].color.values())[:3] for t in icons] == [(1, 1, 1)] * 3  # (no class atlas in the sim: its colour)
    sim.FireScript(r, "OnEnter", False)
    tip = G.GameTooltip
    lines = [S[tip.GetLeftLine(tip, i)].text for i in range(1, tip.NumLines(tip) + 1)]
    assert lines[-3:] == [label("Accepted", [name("Brannock")]), label("Missing", [name("Thorn", "offline")]),
                          label("Ineligible", [name("Elandra", "level 4, needs 5")])]
    sim.FireScript(r, "OnLeave", False)
    sim.group = L.table_from([])
    sim.FireEvent("GROUP_ROSTER_UPDATE")
    sim.Run(0.3)
    assert not [t for t in seq(row(ns, "[7] Kobold Candles").members) if t.IsShown(t)]
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))


def test_party_details():
    L, sim, ns, G = setup()
    big(sim)
    open_candles(ns, sim)
    texts = shown_texts(ns)
    at = texts.index("Party")
    assert texts[at + 1:at + 4] == [label("Accepted", [name("Brannock")]), label("Missing", [name("Thorn", "offline")]),
                                    label("Ineligible", [name("Elandra", "level 4, needs 5")])]
    assert texts.index("Quest Objectives") < at
    # Elandra levels and takes it: laid out again.
    sim.units.party2.level = 6
    sim.units.party2.quests[60] = True
    sim.FireEvent("UNIT_QUEST_LOG_CHANGED", "party2")
    sim.Run(1.5)
    texts = shown_texts(ns)
    at = texts.index("Party")
    assert texts[at + 1:at + 3] == [label("Accepted", [name("Brannock"), name("Elandra")]),
                                    label("Missing", [name("Thorn", "offline")])]
    sim.group = L.table_from([])
    sim.FireEvent("GROUP_ROSTER_UPDATE")
    sim.Run(0.3)
    assert "Party" not in shown_texts(ns)
    assert not errors(sim, ns), "\n\n".join(errors(sim, ns))

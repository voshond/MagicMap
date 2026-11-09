"""The simulated client (wowsim.lua) held to the real one's API: every widget method it defines, per object type, and
every global function and C_* / table function it installs must be in wow-ui-testing's client API snapshot for the
Forever build (wowmock/api.lua: documented, defined by a Blizzard Lua mixin, a Lua VM addition the engine defines, or
an engine call Blizzard's code makes).
A sim the client doesn't match lets the addon call what the game hasn't got, and every test still passes.

Today's gaps are in api_allowlist.json, each with its reason: a ratchet (as maplint-baseline.json), so a new gap
fails, and so does an entry that's no longer one (drop it). The library comes from .wut/ (tools/wut.py)."""
import json
import os

import pytest
from lupa import lua51

import wut

TESTS = os.path.dirname(os.path.abspath(__file__))
ALLOWLIST = os.path.join(TESTS, "api_allowlist.json")

# Lua 5.1, lupa and the sim's own: not client API. (Sim: the tests' handle on the sim; LibStub: an addon library
# other addons embed, not the client's.)
NOT_CLIENT = """_G _VERSION assert collectgarbage coroutine debug dofile error gcinfo getfenv getmetatable io ipairs load
    loadfile loadstring math module newproxy next os package pairs pcall print rawequal rawget rawset require select
    setfenv setmetatable string table tonumber tostring type unpack xpcall python Sim LibStub""".split()

# wowsim's classes the library's API.TYPES doesn't type: their chains from the snapshot's own APIs.
EXTRA_TYPES = """local API = ...
local function Chain(base, ...) local chain = { unpack(API.TYPES[base]) }; for _, v in ipairs({ ... }) do chain[#chain + 1] = v end; return chain end
API.TYPES.Minimap = Chain("Frame", "MinimapFrameAPI")
API.TYPES.ScrollFrame = Chain("Frame", "SimpleScrollFrameAPI")
API.TYPES.QuestPOIFrame = Chain("Frame", "FrameAPIBlob", "FrameAPIQuestPOI")
API.TYPES.MaskTexture = Chain("Texture", "SimpleMaskTextureAPI")
"""

GAPS = """local Sim, API, notClient = ...
local gaps = {}
local function documented(objectType, name)
    return API.Method(objectType, name) or API.LuaMethod(name) or API.Called(":" .. name)
end
local function under(d, c)  -- class d is c or derives from it
    while d do
        if d == c then return true end
        d = Sim.classes[d].base
    end
end
for c, class in pairs(Sim.classes) do
    for name, fn in pairs(class.methods) do
        if type(fn) == "function" then
            local missing = {}
            for d, other in pairs(Sim.classes) do
                if d ~= "Region" and under(d, c) and other.methods[name] == fn then
                    local _, modelled = API.Method(d, name)
                    if not modelled then error("wowsim's " .. d .. " has no API type: add it to EXTRA_TYPES", 0) end
                    if not documented(d, name) then missing[#missing + 1] = d end
                end
            end
            if #missing > 0 then
                table.sort(missing)
                gaps[c .. ":" .. name] = table.concat(missing, " ")
            end
        end
    end
end
local function client(name) return API.Function(name) or API.LuaGlobal(name) or API.EngineLua(name) or API.Called(name) end
-- C_Map and the like hold only documented functions; another table is an object (a font, a colour, Blizzard's Lua)
-- whose methods may come from a Blizzard mixin (ColorMixin's GetRGB).
local namespaces = {}
for full in pairs(API.Snapshot().functions) do
    local space = full:match("^(.-)%.")
    if space then namespaces[space] = true end
end
local function field(space, key)
    return client(space .. "." .. key) or not namespaces[space] and API.LuaMethod(key)
end
for name, value in pairs(_G) do
    if not notClient[name] and type(name) == "string" then
        if type(value) == "function" and not client(name) then
            gaps[name] = "global"
        elseif type(value) == "table" and Sim.state[value] == nil then
            for key, fn in pairs(value) do
                if type(key) == "string" and type(fn) == "function" and not field(name, key) then
                    gaps[name .. "." .. key] = "global"
                end
            end
        end
    end
end
return gaps
"""


def boot():
    """A fresh Lua with wowsim loaded (no addon: only what the sim installs) and the library's API contract."""
    lib = wut.library("wowmock/api.lua")
    assert lib, "wow-ui-testing couldn't be fetched (scripts/fetch-wut.sh) or has no wowmock/api.lua"
    L = lua51.LuaRuntime(encoding="latin-1", unpack_returned_tuples=True)
    sim = L.eval("function(path) return assert(loadfile(path))() end")(os.path.join(TESTS, "wowsim.lua"))
    api = L.eval("dofile")(os.path.join(lib, "wowmock", "api.lua"))
    L.execute(EXTRA_TYPES, api)
    return L, sim, api


@pytest.fixture(scope="module")
def gaps():
    return gaps_of(*boot())


def gaps_of(L, sim, api):
    """{ "Class:method": the object types lacking it, or "global name": "global" } that aren't the client's."""
    return dict(L.execute(GAPS, sim, api, L.table_from({n: True for n in NOT_CLIENT})).items())


def allowed():
    with open(ALLOWLIST) as f:
        return json.load(f)


def test_allowlist_has_reasons():
    bare = [k for k, why in allowed().items() if not isinstance(why, str) or len(why.strip()) < 10]
    assert not bare, f"api_allowlist.json entries without a reason: {bare}"


def test_wowsim_matches_the_client_api(gaps):
    allow = allowed()
    new = {k: v for k, v in gaps.items() if k not in allow}
    gone = sorted(k for k in allow if k not in gaps)
    assert not new, ("wowsim defines what the client API snapshot hasn't got (fix the sim, or add it to "
                     f"tools/tests/api_allowlist.json with its reason): {json.dumps(new, indent=1, sort_keys=True)}")
    assert not gone, f"no longer gaps: drop them from tools/tests/api_allowlist.json: {gone}"


def test_a_fake_method_fails(gaps):
    """The check bites: a method no client has, on Frame, and a fake C_ function, come out as gaps."""
    L, sim, api = boot()
    L.execute("local Sim = ...; Sim.classes.Frame.methods.SetMagicSauce = function() end; C_Map.GetMagicSauce = function() end", sim)
    faked = gaps_of(L, sim, api)
    assert "Frame:SetMagicSauce" in faked and "Button" in faked["Frame:SetMagicSauce"]
    assert faked.get("C_Map.GetMagicSauce") == "global"
    assert set(faked) - set(gaps) == {"Frame:SetMagicSauce", "C_Map.GetMagicSauce"}

"""Regenerates tools/proof/atlases.lua: the atlas table the proof pictures draw Blizzard's art from (name -> file,
size and coordinates), pinned to the client build in .wut/clientdata/forever.json. It keeps the atlases the addon's Lua
names (wow-ui-testing's scripts/atlas_catalog.py scan: names with a hyphen in files that mention atlas), plus every
quoted name in ui/Art.lua, ui/PinTypes.lua, tools/proof/atlas_names.lua and the sim's ATLASES (tools/tests/wowsim.lua:
names with no hyphen, built by concatenation, or wanted ahead), plus the -c60 art variants (members of the element without the suffix: the table lists them under that name), plus any ping atlas (Ping_*, *-ping-*) of the export.

    .venv/bin/python tools/proof.py --atlases        # downloads the build's wago.tools exports (cached in .proof-art/)
"""
import importlib.util
import os
import re
import sys

import wut

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "tools", "proof", "atlases.lua")
SCAN = ["ui/**/*.lua", "game/**/*.lua", "atlas/**/*.lua"]
LOOSE = ["ui/Art.lua", "ui/PinTypes.lua", "tools/proof/atlas_names.lua", "tools/tests/wowsim.lua"]
NAME = re.compile(r"""["']([A-Za-z_!][\w!.\-]*)["']""")
MARKUP = re.compile(r"\|A:([\w!.\-]+):")


def load_catalog(lib):
    spec = importlib.util.spec_from_file_location("atlas_catalog", os.path.join(lib, "scripts", "atlas_catalog.py"))
    catalog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalog)
    return catalog


def loose_names():
    names = set()
    for path in LOOSE:
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            text = f.read()
        names.update(m.group(1).lower() for m in NAME.finditer(text))
        names.update(m.group(1).lower() for m in MARKUP.finditer(text))
    return names


def forever_members(catalog):
    """The member Forever draws for an element, as its GetAtlasInfo reports it (in game, 1.60.1.70862: the metal frame's
    pieces): a 1x member before a -2x, the -c60 art before the plain (its -2x as well: `-c60-2x`), and a -2x member at
    half its texels (the !UI-Frame-Metal-EdgeLeft-c60-2x's 190x256 is 95x128). Swaps the catalog's pick; returns the
    chosen -2x members by element id, whose sizes the table halves."""
    doubled = {}

    def preferred(members):
        def rank(member):
            name = member["CommittedName"].lower()
            base = name[:-3] if name.endswith("-2x") else name
            return (name.endswith("-2x"), not base.endswith("-c60"), int(member["ID"]))
        member = min(members, key=rank)
        if member["CommittedName"].lower().endswith("-2x"):
            doubled[member["UiTextureAtlasElementID"]] = True
        return member

    catalog.preferred_member = preferred
    return doubled


def generate(cache):
    lib = wut.library("scripts/atlas_catalog.py")
    if not lib:
        print("wow-ui-testing's scripts/atlas_catalog.py not found (scripts/fetch-wut.sh couldn't fetch it)")
        return 2
    catalog = load_catalog(lib)
    pin = catalog.pinned_source("forever")
    manifest = catalog.read_manifest(pin)
    tables, fetched, compressed = catalog.download(pin)
    if fetched != manifest:
        print("downloaded tables do not match the pinned checksums")
        return 1
    catalog.write_cache(pin, catalog.Path(cache), compressed)
    literals, pattern = catalog.atlas_uses(SCAN, catalog.Path(ROOT))
    literals |= loose_names()
    ping = re.compile(r"(.*[-_])?ping([-_].*)?")
    for element in tables["UiTextureAtlasElement"]:
        if ping.fullmatch(element["Name"].lower()):
            literals.add(element["Name"].lower())
    variants = {name[:-4]: name for name in literals if name.endswith("-c60")}
    literals |= set(variants)
    doubled = forever_members(catalog)
    atlases = catalog.compile_atlases(tables, (literals, pattern))
    for element in tables["UiTextureAtlasElement"]:
        info = atlases.get(element["Name"])
        if info and doubled.get(element["ID"]):
            info["width"], info["height"] = int(info["width"]) // 2, int(info["height"]) // 2
    for base, variant in variants.items():
        found = next((n for n in atlases if n.lower() == base), None)
        if found:
            atlases[variant] = atlases[found]
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(catalog.lua_atlases(atlases, pin["build"]))
    print(f"{OUTPUT}: {len(atlases)} atlases at build {pin['build']}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(generate(os.path.join(ROOT, ".proof-art", "atlas-exports")))

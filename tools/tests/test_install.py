"""tools/install.py: the local install, and --host with ssh and rsync stubbed. The stub runs the ssh command
with the local sh (so the quoting of a spaced WoW folder is really tested) and rsync without the host."""
import os
import subprocess
import sys

import pytest

import install

FILES = ["runtime/Boot.lua", "atlas/files.txt"]
TEXTURE = install.texture_files()[0]


@pytest.fixture
def wow(tmp_path, monkeypatch):
    """A WoW folder with a space in its name and an empty _forever_ AddOns folder; a small file set."""
    root = tmp_path / "World of Warcraft"
    (root / "_forever_" / "Interface" / "AddOns").mkdir(parents=True)
    monkeypatch.setattr(install, "existing_toc_files", lambda: list(FILES))
    monkeypatch.setattr(install, "toc_files", lambda: list(FILES))
    monkeypatch.setattr(install, "texture_files", lambda: [TEXTURE])
    for name in ("MAGICMAP_WOW", "MAGICMAP_HOST", "MAGICMAP_HOST_WOW"):
        monkeypatch.delenv(name, raising=False)
    return root


@pytest.fixture
def host(monkeypatch):
    """ssh and rsync stubbed: what they were asked to run."""
    calls = []
    real_run, real_call = subprocess.run, subprocess.call

    def run(argv, **kw):
        if argv[0] != "ssh":  # git describe (check_output)
            return real_run(argv, **kw)
        assert argv[1] == "arch" and len(argv) == 3
        calls.append(argv)
        return real_run(["sh", "-c", argv[2]], **kw)

    def call(argv, **kw):
        calls.append(argv)
        assert argv[:5] == ["rsync", "-a", "--delete", "-s", argv[4]] and argv[5].startswith("arch:")
        return real_call(argv[:5] + [argv[5][len("arch:"):]], **kw)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "call", call)
    return calls


def addons(wow):
    return wow / "_forever_" / "Interface" / "AddOns"


def install_(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["install.py", "--no-check", *args])
    install.main()
    return capsys.readouterr().out


def refused(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["install.py", "--no-check", *args])
    with pytest.raises(SystemExit) as e:
        install.main()
    return str(e.value.code)


def spike(wow):
    old = addons(wow) / "MagicMap"
    old.mkdir()
    (old / "MagicMap.toc").write_text("## Title: MagicMap\n## SavedVariables: MagicMapDB\n")
    (old / "Old.lua").write_text("")


def stamped(dest):
    text = (dest / "MagicMap.toc").read_text()
    assert "## X-Stamped: " in text
    return text.split("## X-Stamped: ", 1)[1].split("\n", 1)[0]


@pytest.mark.parametrize("remote", [False, True])
def test_install_then_reload(wow, monkeypatch, capsys, request, remote):
    calls = request.getfixturevalue("host") if remote else None
    args = ["--wow", str(wow)] + (["--host", "arch"] if remote else [])
    where = "arch:" if remote else ""
    dest = addons(wow) / "MagicMap"
    other = addons(wow) / "MagicMap_old"
    other.mkdir()
    (other / "MagicMap_old.toc").write_text("## Title: MagicMap 1.9\n")

    out = install_(monkeypatch, capsys, *args)
    rev = stamped(dest)
    assert f"installed MagicMap {rev} " in out and f"into {where}{dest}\n" in out
    assert "restart the client (not /reload)" in out
    assert f"{where}{other} (MagicMap 1.9) loads too" in out
    assert sorted(os.listdir(dest)) == ["MagicMap.toc", "Textures", "atlas", "runtime"]
    (dest / "stray.lua").write_text("")

    out = install_(monkeypatch, capsys, *args)
    assert "/reload in game" in out and "restart" not in out
    assert not (dest / "stray.lua").exists()
    if remote:
        assert {c[0] for c in calls} == {"ssh", "rsync"}
        assert all(c[2] == "python3 -" for c in calls if c[0] == "ssh")
        assert [c[5] for c in calls if c[0] == "rsync"] == [f"arch:{dest}/"] * 2


@pytest.mark.parametrize("remote", [False, True])
def test_refusals(wow, monkeypatch, request, remote):
    if remote:
        request.getfixturevalue("host")
    args = ["--wow", str(wow)] + (["--host", "arch"] if remote else [])
    where = "arch:" if remote else ""
    dest = addons(wow) / "MagicMap"

    assert refused(monkeypatch, *args, "_classic_") == (
        f"no {where}{wow / '_classic_' / 'Interface' / 'AddOns'}; pass --wow / a flavor folder"
        " (has this flavor been run once?)")

    dest.symlink_to(wow)
    assert refused(monkeypatch, *args).startswith(f"{where}{dest} is a symlink")
    dest.unlink()

    dest.mkdir()
    assert refused(monkeypatch, *args) == f"{where}{dest} doesn't look like MagicMap (no MagicMap.toc); not deleting it"
    dest.rmdir()

    spike(wow)
    assert refused(monkeypatch, *args).startswith(f"{where}{dest} is the spike (it saves MagicMapDB)")
    (addons(wow) / "MagicMap.spike-backup").mkdir()
    assert refused(monkeypatch, *args, "--replace-spike") == (
        f"{where}{addons(wow) / 'MagicMap.spike-backup'} is there already: move it away first")
    assert (dest / "Old.lua").exists()


@pytest.mark.parametrize("remote", [False, True])
def test_replace_spike(wow, monkeypatch, capsys, request, remote):
    calls = request.getfixturevalue("host") if remote else None
    args = ["--wow", str(wow)] + (["--host", "arch"] if remote else [])
    spike(wow)
    out = install_(monkeypatch, capsys, *args, "--replace-spike")
    backup = addons(wow) / "MagicMap.spike-backup"
    assert (backup / "Old.lua").exists() and not (addons(wow) / "MagicMap" / "Old.lua").exists()
    assert "restart the client" in out
    if remote:
        dest = addons(wow) / "MagicMap"
        assert ["ssh", "arch", f"mv -- '{dest}' '{backup}'"] in calls


def test_host_defaults(wow, monkeypatch, host):
    monkeypatch.setenv("MAGICMAP_HOST", "arch")
    assert refused(monkeypatch).startswith(f"no arch:{install.HOST_WOW}/_forever_/Interface/AddOns;")
    monkeypatch.setenv("MAGICMAP_HOST_WOW", str(wow))
    assert refused(monkeypatch, "_ptr_").startswith(f"no arch:{wow}/_ptr_/Interface/AddOns;")
    assert all(c[:3] == ["ssh", "arch", "python3 -"] for c in host)


def test_empty_host_is_local(wow, monkeypatch, capsys, host):
    monkeypatch.setenv("MAGICMAP_HOST", "arch")
    out = install_(monkeypatch, capsys, "--wow", str(wow), "--host", "")
    assert f"into {addons(wow) / 'MagicMap'}\n" in out and not host


def test_ssh_failure(wow, monkeypatch):
    def run(argv, **kw):
        return subprocess.CompletedProcess(argv, 255, "", "ssh: Could not resolve hostname nope")

    monkeypatch.setattr(subprocess, "run", run)
    assert refused(monkeypatch, "--host", "nope").endswith("ssh: Could not resolve hostname nope")

"""publish.py -- ship the rendered reel to a public GitHub repo.

Creates the repository if it does not exist yet, writes a README that links the
video to its source of truth (brief + spec), and pushes everything through the
already-authenticated `gh` CLI. No tokens are handled here.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

GH = shutil.which("gh") or "gh"
GIT = shutil.which("git") or "git"
LFS_LIMIT = 45 * 1024 * 1024  # GitHub soft limit for a plain file


def run(cmd, cwd=None, check=True, capture=True):
    r = subprocess.run(cmd, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                       stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{(r.stderr or '')[-1500:]}")
    return r


def whoami() -> str:
    return run([GH, "api", "user", "-q", ".login"]).stdout.strip()


def repo_exists(owner: str, name: str) -> bool:
    r = run([GH, "repo", "view", f"{owner}/{name}"], check=False)
    return r.returncode == 0


def create_repo(owner: str, name: str, description: str, public: bool) -> None:
    vis = "--public" if public else "--private"
    run([GH, "repo", "create", f"{owner}/{name}", vis,
         "--description", description, "--disable-wiki"])
    print(f"[repo] created {owner}/{name}")


def readme_for(meta: dict, has_video: bool, video_name: str, lfs: bool) -> str:
    title = meta.get("title", "Code Video")
    repo_url = meta.get("repo_url", "")
    lines = [
        f"# {title}",
        "",
        meta.get("subtitle", ""),
        "",
        "A 61-second promo reel where **every pixel is computed**. No diffusion model,",
        "no video-generation model, no sampled footage or music: frames are numpy arrays",
        "written to ffmpeg, and the score is built from oscillators and envelopes.",
        "",
    ]
    if has_video:
        embed = f"{video_name}" if not lfs else video_name
        lines += [
            "## Video",
            "",
            f"https://github.com/{repo_url}/blob/main/{embed}" if repo_url else embed,
            "",
        ]
    lines += [
        "## Reproduce",
        "",
        "```powershell",
        "python engine/director.py spec.json -o out.mp4 --probe",
        "```",
        "",
        "The whole timeline lives in `spec.json`, generated from `brief.json` by",
        "`engine/brief.py`. Nothing in the render path touches the network.",
        "",
        "## Structure",
        "",
        "```text",
        "brief.json      # interview answers: the only human input",
        "spec.json       # resolved timeline (act -> style -> payload)",
        "prompt.md       # human-readable version of the same timeline",
        "engine/         # render pipeline (core, typekit, scenes, score, director)",
        "scripts/        # smoke test, style check, publish",
        "```",
        "",
        "## Credits",
        "",
    ]
    for k, v in (meta.get("credits") or {}).items():
        lines.append(f"- **{k}**: {v}")
    lines += ["", "Generated with the `code-video` skill.", ""]
    return "\n".join(lines)


def git_init(src: pathlib.Path, owner: str, name: str) -> None:
    run([GIT, "init", "-q"], cwd=src)
    run([GIT, "checkout", "-q", "-b", "main"], cwd=src, check=False)
    run([GIT, "add", "-A"], cwd=src)
    r = run([GIT, "commit", "-q", "-m", "feat: pure-code promo reel"], cwd=src, check=False)
    if r.returncode != 0 and "nothing to commit" not in (r.stdout or "") + (r.stderr or ""):
        raise RuntimeError(r.stderr[-1200:])
    run([GIT, "remote", "remove", "origin"], cwd=src, check=False)
    run([GIT, "remote", "add", "origin", f"https://github.com/{owner}/{name}.git"], cwd=src)
    run([GIT, "push", "-q", "-u", "origin", "main"], cwd=src)


def main():
    ap = argparse.ArgumentParser(description="publish a rendered reel to GitHub")
    ap.add_argument("--brief", required=True, help="brief.json produced by the interview")
    ap.add_argument("--spec", default=None, help="spec.json (regenerated if omitted)")
    ap.add_argument("--prompt", default=None, help="prompt.md (regenerated if omitted)")
    ap.add_argument("--video", default=None, help="rendered mp4")
    ap.add_argument("--repo", default=None, help="repository name (default: title slug)")
    ap.add_argument("--private", action="store_true", help="create as private (default public)")
    ap.add_argument("--no-create", action="store_true", help="fail if the repo is missing")
    ap.add_argument("--description", default="")
    args = ap.parse_args()

    brief_path = pathlib.Path(args.brief).resolve()
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    sys.path.insert(0, str(brief_path.parent / "engine"))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "engine"))
    import brief as brief_mod

    owner = whoami()
    name = args.repo or "".join(
        c if c.isalnum() or c in "-_" else "-"
        for c in brief.get("title", "code-video").strip().lower()).strip("-")
    name = name or "code-video"
    public = not args.private

    print(f"[gh] account={owner} repo={name} public={public}")
    if not repo_exists(owner, name):
        if args.no_create:
            raise SystemExit(f"repo {owner}/{name} does not exist")
        create_repo(owner, name,
                    args.description or brief.get("subtitle", "Pure-code promo reel"),
                    public)
    else:
        print(f"[repo] exists, pushing into it")

    # assemble a staging tree so the repo never contains build leftovers
    stage = pathlib.Path(tempfile.mkdtemp(prefix="codevideo-"))
    skill = pathlib.Path(__file__).resolve().parent.parent
    for sub in ("engine", "scripts"):
        shutil.copytree(skill / sub, stage / sub,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if (skill / "references").exists():
        shutil.copytree(skill / "references", stage / "references")

    spec = brief_mod.build_spec(brief)
    (stage / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    if args.spec and pathlib.Path(args.spec).exists():
        shutil.copy2(args.spec, stage / "spec.json")
    else:
        (stage / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    prompt = brief_mod.render_prompt(brief)
    (stage / "prompt.md").write_text(prompt, encoding="utf-8")

    has_video, video_name, lfs = False, "", False
    if args.video and pathlib.Path(args.video).exists():
        vp = pathlib.Path(args.video)
        video_name = vp.name
        shutil.copy2(vp, stage / video_name)
        has_video = True
        lfs = vp.stat().st_size > LFS_LIMIT
        if lfs:
            print(f"[warn] {video_name} is {vp.stat().st_size/1048576:.0f} MB; "
                  f"GitHub rejects files over 100 MB without LFS")

    meta = {
        "title": brief.get("title", ""),
        "subtitle": brief.get("subtitle", ""),
        "repo_url": f"{owner}/{name}",
        "credits": brief.get("credits") or {},
    }
    (stage / "README.md").write_text(
        readme_for(meta, has_video, video_name, False), encoding="utf-8")

    git_init(stage, owner, name)
    url = f"https://github.com/{owner}/{name}"
    print(f"[done] {url}")
    shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    main()
# sgroi.ga — Publication and working rules

This repository is a static website published through GitHub Pages in legacy mode.

## 1. Publishing model

The live site is published directly from the `main` branch in the repository root.

- Branch: `main`
- Publishing location: root `/`
- Build system: no workflow, no CI, no deploy script
- Publication method: push the resulting generated HTML to `main`

This means:

- `src/` is source code and templates
- generated files in the repository root are what GitHub Pages serves
- a local preview is only for validation and does not publish anything
- live publication is only complete after a successful push to `main`

## 2. What gets published

The actual public website is the generated output in the root folder, for example:

- `index.html`
- `blog/.../index.html`
- `legal/.../index.html`
- `de/.../index.html`
- `assets/...`

The site is not published from `src/` alone.

## 3. Build process

Whenever content, templates, CSS, JS, or blog entries are changed, run:

```sh
python3 src/scripts/build.py
```

This regenerates the root HTML and asset copies that GitHub Pages serves.

## 4. Required publication workflow

Use this exact order:

```sh
git fetch origin
python3 src/scripts/build.py

git add -A

git commit -m "Rebuild static pages" -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"

git push origin HEAD:main
git push origin HEAD
```

Important requirements:

- always commit the generated root files
- do not assume a local preview means the site is live
- do not publish only source files in `src/`
- do not rely on a workflow or deploy action that does not exist

## 5. Branch and merge rules

The publishing branch is `main`.

If the current branch is not already based on `origin/main`:

```sh
git fetch origin
git rebase origin/main
python3 src/scripts/build.py

git add -A

git commit -m "Rebuild static pages" -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
```

Then push to `main`:

```sh
git push origin HEAD:main
git push origin HEAD
```

## 6. Verification after publish

After pushing to `main`, prove the live site is built and reachable:

```sh
gh api repos/0nhub/homepage/pages/builds/latest --jq '.status+" "+.commit[0:7]'
```

Expected output is a successful build such as:

```sh
built 7160832
```

Then validate the actual website:

```sh
curl -s "https://sgroi.ga/blog/?x=$RANDOM"
curl -s "https://sgroi.ga/blog/keyboard-shortcuts-the-hidden-superpowers/?x=$RANDOM"
```

Only a successful GitHub Pages build and a live HTTP check confirm publication.

## 7. Communication rules

The following rules must be followed in all communication and execution notes:

- never describe GitHub Pages as unavailable when the repo is configured for legacy root publishing
- never say there is no publishing path if the repository is using direct `main` GitHub Pages publishing
- never equate local preview with deployment
- always describe the site as published by direct pushes to `main`
- always state that generated root HTML must be committed and pushed
- always keep the workflow consistent and explicit

## 8. Short summary

If something should go live, the required path is:

```sh
python3 src/scripts/build.py

git add -A
git commit -m "Rebuild static pages" -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
git push origin HEAD:main
git push origin HEAD
```

That is the publication process for this repository.

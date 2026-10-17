# Krithika’s photo journals

A photo blog where each trip is a scrolling story. You add a folder of photos and videos; the site builds and publishes itself.

## Adding a new trip

1. Make a folder for the trip, named with the year first: `2026-lisbon`.
2. Put the photos and videos you want to show in it. They can keep their original names, like `IMG_4410.HEIC`.
   - The order comes from `story.md`. Files it doesn't list go at the end, sorted by name.
   - To mark an artsy shot, add `| art` after its name in `story.md` (`## IMG_4402.HEIC | art`). It's shown on a white border with just a short caption. Adding `.art` to the file name (`tiles.art.jpg`) also works.
   - Videos (`.mp4` or `.mov`) play silently on a loop while they're on screen. Readers can tap for sound. Keep clips short, about 10–20 seconds.
   - iPhone `.heic` photos work.
3. Optional: copy `story-template.md` into the folder, rename it `story.md`, and fill it in. Skip it and the trip still publishes, with the folder name as the title and no text.
4. Upload the folder into the `trips` folder on GitHub (see below). The site updates a couple of minutes later.

To change a trip, edit or replace files in its folder the same way. To remove a trip, delete its folder.

To hide a trip without deleting it, add `hidden: yes` between the `---` lines of its `story.md`. Remove that line to show it again.

## The story.md file

```
---
title: Lisbon
year: 2026
where: Portugal
---

Optional opening paragraph.

## IMG_4410.HEIC
First evening
We landed late and walked down to the river.

## IMG_4402.HEIC | art
Tiles in Alfama
```

- The part between the `---` lines shows on the home page and at the top of the trip.
- Each `##` line is a file name from the folder, exactly as it's spelled (capital letters don't matter). The order of the `##` blocks is the order on the page.
- The line under it is the title (or the caption, for artsy shots). Anything after that is the text.
- Leave a blank line between paragraphs.

## Uploading from the browser

1. Open the repository on github.com and click into the `trips` folder.
2. Click **Add file → Upload files** and drag your trip folder onto the page.
3. Click **Commit changes**.

The browser upload only accepts files up to 25 MB. For bigger videos, use the free GitHub Desktop app instead, which accepts files up to 100 MB.

## What happens to your photos

The build step runs automatically on GitHub every time you upload. It:

- removes location (GPS) and camera details from every photo and video
- resizes photos and compresses videos so pages load fast
- asks search engines not to list the site (turn this off by setting `"hide_from_search": false` in `settings.json`)

**The repository is public.** The original files you upload, including their location data, can be seen by anyone who opens the repository on GitHub. Only the cleaned copies appear on the site, but the originals are still there. Before uploading, remove location from photos you care about:

- **iPhone:** in the share sheet, tap **Options** and turn off **Location**.
- **Mac Photos:** Image → Location → Hide Location before exporting, or in the Export dialog leave "Include Location" unchecked.

## Settings

`settings.json` holds the site title, the footer text, and the search setting.

## One-time setup

1. Create a **public** repository on GitHub and upload everything in this folder to it.
2. In the repository, go to **Settings → Pages**, and under **Build and deployment** set **Source** to **GitHub Actions**.
3. Open the **Actions** tab. Once the "Publish site" run has a green check, the site is live. Its address is shown in **Settings → Pages**.
4. Turn on two-factor authentication for your GitHub account (Settings → Password and authentication).

Delete the two sample trips in `trips/` once you've added your own.

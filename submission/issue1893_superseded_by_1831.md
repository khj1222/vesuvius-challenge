<!--
#1893 closing comment draft (2026-10-02). NOT posted — needs the user's OK.

Why this replaces the PR: BioMarco's #1831 (opened 09-19, merged 09-30 by hendrikschilling)
fixes the same thing. Main f637f3b35 built in the CI image passes 5/6 of our own test cases and
matches our fix on every real-data case (remote PHerc0139 -g 5 = micrometer 299.584, TIFF 4/4).
The one difference is a documented design choice (--voxel-unit only describes --voxel-size).
Evidence: planning/2026-09-29_issue1893_build/results/{unittest_on_main_f637f3b.txt,
more_main_f637f3b.txt}, build log build_main_f637f3b.log.
Our branch fix/render-voxel-unit-from-metadata (ca4a5bd68, D:/vw12) stays local and unpushed.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

This is fixed on main by #1831 (merged 09-30), so I am not opening the PR I had prepared.

I built main at `f637f3b35` in the CI image (`vc3d-deps/linux:sha-0c371b1d…`) and re-ran the cases from my comment above, plus a remote render:

| input | release f07d33b | main f637f3b |
|---|---|---|
| local, `meta.json` voxelsize 9.362 | nanometer, 9.362 | micrometer, 9.362 |
| local, only the published `metadata.json` scan record | nanometer, 1.0 | micrometer, 9.362 |
| local, no metadata | nanometer, 1.0 | no unit, 1.0 |
| PHerc0139 over `--remote-url`, `-g 5` | nanometer, 32.0 | micrometer, 299.584 |
| local, `--voxel-size 9.362` only | nanometer, 9.362 | nanometer, 9.362 |

TIFF resolution is unchanged in all four cases I checked.

The only place main differs from what I had: `--voxel-unit nanometer` on a volume that has metadata keeps micrometres instead of converting to 9362 nm. The help text now says `--voxel-unit` only describes `--voxel-size`, and the value written is correct either way, so I don't see anything left here. I think this issue can be closed.

@Sartoshirelli, if you still want to run the #1891 check, main is the thing to run it against now.

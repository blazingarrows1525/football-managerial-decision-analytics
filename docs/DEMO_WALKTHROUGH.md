# Demo Walk-through and Presentation Outline

## Before the demo

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the app once beforehand so the data are downloaded and cached (the first load takes a minute or two).
Keep `notebooks/Football_Managerial_Analytics_Complete.ipynb` open in a second tab. For a clean look switch on
**Presentation mode** (top right of every page): it hides the sidebar and technical panels and enlarges labels.

## Ten-minute demo script

| Minute | Page | What to do | What to say |
|---|---|---|---|
| 0–1 | Executive Overview | Read the KPI strip and the coverage line | 34 matches, all involving one team: a team-centric sample. Historical data, nothing live. |
| 1–2 | Executive Overview | Points vs expected points; concentration chart | Results ran ahead of chance quality; three players create 40% of the chances. |
| 2–3 | Sidebar | Set Venue to *home* | Every number and chart is recomputed on 17 matches — filters recompute, they do not hide. Reset. |
| 3–4 | Match Centre | Pick a match; Timeline → Shots & xG | Timeline from the event clock; the interval chart is xG per five minutes, not "momentum". |
| 4–5 | Player Lab | Profile → Consistency | Percentiles are within the role group; bootstrap intervals show which gaps are real. |
| 5–6 | Team Tactics | Passing network → By betweenness; Progression | Hubs and bridges; lanes used to progress; the xT surface is project-computed and in-sample. |
| 6–7 | Starting XI Lab | Change a weight; mark a player unavailable | A transparent shortlist under stated weights; the tool cannot know who is injured. |
| 7–8 | Substitution Lab | Scenario at minute 65 | A labelled counterfactual: who is on the bench and unused, why each is ranked. |
| 8–9 | Statistical Explorer | Match-level associations; Power | Nothing survives FDR at n = 34; power curve shows why. |
| 9–10 | Chart Explorer + Data Quality | Search "voronoi"; open the validation panel | Charts that need tracking are listed as not implemented; 16/16 rules pass. |

## Presentation outline (about 10 slides)

1. **Title and question** — decision support, not an oracle.
2. **Data** — source, scope, licence, what is and is not in it (chart A-012).
3. **Pipeline and architecture** — one shared package, two front-ends (`docs/ARCHITECTURE.md` diagram).
4. **Data quality** — validation panel (A-016), structural missingness (A-005).
5. **Team performance** — points vs expected points (L-262), shot volume vs quality (C-046).
6. **Players** — role percentiles (D-069), bootstrap intervals (D-079), concentration (B-029).
7. **Tactics** — pass network and centrality (F-140, F-139), progression lanes (E-133).
8. **Decision support** — shortlisted XI and decomposition (G-149, G-166); substitution scenario (H-182).
9. **Statistics and models** — forest plot with FDR (J-202), power (J-214), model vs baseline (K-221).
10. **Limitations and next steps** — sample, missing modalities, association not causation.

Export any chart for slides from its **Export** button (interactive HTML) or run
`python scripts/export_gallery.py --formats png --ids L-262 C-046 …` (PNG needs the optional `kaleido`).

## If something goes wrong during the demo

- No network: the raw files are cached locally after the first run; the app works offline afterwards.
- A chart says "implemented but unavailable": the message names the missing prerequisite — usually too few
  matches after filtering. Reset the filters.
- Fall back to the executed notebooks in `notebooks/`, which contain the same charts as static images.

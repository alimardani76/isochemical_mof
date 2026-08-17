# Analysis provenance and frozen scientific design

This file records the scientific lineage of the analysis used by the manuscript **Matched MOF Families Reveal Regime-Dependent Pore-Geometry Effects on Adsorption**. It replaces the earlier coauthor-handover narrative with a publication-facing provenance record.

## Frozen primary design

The primary analysis is outcome-blind through pair construction: define families using the recorded chemistry representation; require agreement in recorded topology and dimensionality; measure within-family variation across eight pore descriptors; freeze a 10% geometry criterion; select one deterministic maximum-separation pair per eligible family; freeze pair orientation from geometry-low to geometry-high on the largest-contrast descriptor; freeze CH4 uptake at 298 K and 65 bar in mmol g^-1 as the primary endpoint; and only then open adsorption outcomes.

The frozen primary catalogue contains 11,072 pairs (22,144 unique frameworks). The primary median response is +0.5835545 mmol g^-1 with a 95% family-bootstrap interval of 0.5545650–0.6149215 mmol g^-1; 70.502% of pairs are positive. The 20% and 30% contrast tiers are prespecified stronger-contrast subsets, not post-hoc threshold optimization.

## Representation boundary

“Same recorded chemistry” is not atom-by-atom identity. The match uses scale-invariant whole-CIF elemental composition, scale-invariant metal-element composition, and ARC–MOF metal/linker/functional cluster assignments. Architecture uses recorded topology and dimensionality. No bond graph, oxidation state, linker identity, node identity, or local coordination environment is reconstructed.

The internal `driver_descriptor` field means the descriptor with the largest observed geometry contrast inside an already-frozen pair. Publication text uses **largest-contrast descriptor/class** because pore descriptors can co-vary.

## Post-freeze analyses

These analyses do not redefine pair membership, orientation, the 10% criterion, the primary endpoint, or the estimand.

### H2 — geometry-attribution stability

Increasing the required top-1/top-2 contrast ratio attenuates the pooled response, but the pooled attenuation is not a uniform loss of class-specific behavior. At a ratio ≥1.50, the retained cohort becomes strongly Df-weighted. ASA remains strongly favorable in its cleaner subset, AVA remains strongly favorable at the well-supported ≥1.25 criterion, and Df remains slightly negative.

Canonical outputs: `results/submission_upgrade/H2_geometry_attribution/`.

### H3 — uptake-basis and density robustness

The positive population sign persists on the source crystallographic volumetric basis (median +3.7972 v/v; 60.9% positive), while signed density change is strongly coupled to the gravimetric response (Spearman rho = -0.772) and more weakly to the volumetric response (rho = -0.325). ASA/AVA-labelled pairs remain favorable volumetrically; the non-ASA/AVA group is slightly negative on median.

This is a crystallographic-basis robustness check, not packed-bed/device storage.

Canonical outputs: `results/submission_upgrade/H3_uptake_basis_density/`.

### H4 — deterministic structural cases

Six mutually exclusive frozen pairs were selected from predeclared geometry/response strata by robust representativeness distance, without optimizing effect size or visual attractiveness. The 12 CIFs are used only to translate the population-level regimes into crystallographic intuition.

Panel A is publication-facing as a **broad accessible-space contrast** while retaining ASA as its frozen ordering label. Panels D/E are diameter counter-regimes. Panel F is an experimental-source crystallographic record, not experimental adsorption validation.

Canonical outputs: `results/submission_upgrade/H4_structural_cases/`.

### H6 — same-source heterogeneity

Same-source populations have strongly different medians, geometry magnitudes, and ASA/AVA composition. Source labels are therefore treated as provenance/applicability variables rather than causal explanations.

Canonical outputs: `results/submission_upgrade/H6_source_stratified/`.

## Repository milestones

- PR #1 merged post-freeze robustness, reproducibility, and initial coauthor documentation.
- PR #2 merged deterministic Figure 5 selection/rendering provenance.
- PR #3 merged reproducible publication-figure redesign code.

The publication-hardening branch synchronizes the current manuscript/SI and removes obsolete internal handover artifacts without modifying frozen science.

## Experimental-transferability boundary

Of the 11,072 pairs, 10,981 are hypothetical–hypothetical, 82 are experimental–experimental, and 9 are mixed. The small experimental-source subset is not sufficient to claim broad experimental validation.

## Rule for future changes

Changes to frozen analytical definitions must be implemented as a new analysis branch/output set. They must not silently overwrite the results used by the current manuscript.

# Publication artifact manifest

This manifest records the exact local PASS-E publication artifacts used during the repository-hardening pass on 2026-08-17.

The quantitative figures are reproducible from committed result tables and `figures/redesign/` source. Figure 5 additionally depends on its locked structural rendering workflow and a manually assembled publication composite.

| Artifact | SHA-256 |
|---|---|
| `manuscript/SI.tex` | `fe8eb2e0d9881baba43032fabc16eb6f8185759062b53fe32b2f75056d2ebc37` |
| `manuscript/Project17_References.bib` | `9385cb735cea8df4fc3633351031add8642ff87953456a921b2d68924859ca68` |
| `manuscript/Project17_SI_closure_tables.tex` | `f2b19ae830f1ddd6cac66d5aa029713f561d2e57b14926542f06d39bb4b7505c` |
| local PASS-E `main.pdf` | `7483490130f8d661509481ed9463ea8fecc6101f4dd59b799dc55b85020c1e74` |
| local PASS-E `SI.pdf` | `d367968a6ecb55e89d5e26f7e899183e2de00f9a4a38112fb113aed3426fced8` |
| `Figure_1.pdf` | `44b802197c56bfba4c3374df34501cda3df459ba92a865cfc4018395d521f7bb` |
| `Figure_2.pdf` | `1f791b4fa19540f12feb25d531ffee6ef0f2e92e8c34af8bad45380d26ac4fa6` |
| `Figure_3.pdf` | `3596603e0f8da2ce5b4a4bad7aa2c5985252e42e4186945f1cd6ff7f1b5934dd` |
| `Figure_4.pdf` | `4ec2e7c0e517c9d508584d71b24e0072680999030f4b381177e8299c5cfa4eda` |
| `Figure5_Structural_Panel.pdf` | `113fc0031fde5e0a3161ff929f651baefa10e1f39ced9a83640fc1b9bf6b17b2` |
| `Figure_S1.pdf` | `3a635c05b3989ebb6c703684d8a520c15561570226fd3592d1261b5fa27165c3` |
| `Figure_S2.pdf` | `fbac09c85b2e6b80bb5f47f2f75bcad7791439429ca7df6cd3bcc4aa4246a145` |
| `Figure_S3.pdf` | `80eacda72c3243dfe2554bc84e9be2f9d295a4be9d9055a3a0aadb754c2ec752` |
| `Figure_S4_geometry_attribution_stability.pdf` | `7ec9a187b5c714e055a6098bbba70b21638a7321fd70a39fd0572958a4234ff9` |
| `Figure_S5_basis_density_robustness.pdf` | `998192a9243427f07bf9cc8a73e6bbb44151c5f5d89a1dcd9ad35fe29d1a8134` |
| `Figure_S6_source_stratified.pdf` | `73a79be1107cd13c0e912e929e60856545a85950017bae49ef6473df5c9dbb67` |

Earlier generated artwork remains in Git history for provenance, but generated binary figures are not the scientific source of truth. The source tables, frozen analysis definitions, plotting/rendering code, and hashes above define the publication snapshot.

The exact large Figure 5 PDF must be included in the permanent DOI-minting release bundle. Before archival release, regenerate/collect the final publication binaries, verify all hashes, and update this manifest if any presentation-only export changes. A changed scientific value requires a new analysis/audit, not a manifest edit.

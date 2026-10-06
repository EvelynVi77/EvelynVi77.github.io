---
title: "HeriTell"
order: 10
home_section: research
home_order: 1
home_label: "Human–computer interaction · 2026"
home_excerpt: "A VR technology probe for documenting cultural-heritage knowledge through voice and spatial authoring. Experts contribute interpretations directly within the 3D environments they describe."
home_note: "Published in CHI EA ’26"
home_link_label: "View research"
excerpt: "A VR technology probe for spatial authoring of interpretive cultural-heritage knowledge."
header:
  teaser: /assets/research/spatialtel/SpatialTellCover.gif
classes: wide
---

Research Project | CHI EA '26 | 2026

*Cheng Zeng, Qinrong Liu, and Pengcheng An. [HeriTell: Supporting Interactive Documentation of Cultural Heritage Knowledge through Spatial Authoring](https://doi.org/10.1145/3772363.3798478). Extended Abstracts of the 2026 CHI Conference on Human Factors in Computing Systems, Barcelona, Spain.*

<a href="https://youtu.be/xrT5RJzHc70" target="_blank" rel="noopener noreferrer"><img src="/assets/research/spatialtel/SpatialTellCover.gif" alt="HeriTell VR authoring demo" loading="lazy" width="800" height="450"></a>

*Full demo: [youtu.be/xrT5RJzHc70](https://youtu.be/zDYq8y6fiTM)*

## Spatial authoring for interpretive heritage knowledge

Cultural-heritage expertise is often interpretive, relational, and inseparable from spatial context. Yet in common documentation workflows, photographs, textual descriptions, and annotated drawings remain separated from the 3D assets they describe. This spatial-referencing gap makes it difficult to revisit a component in context, compare contributions, or understand how an interpretation relates to its surroundings.

HeriTell is a VR-based technology probe that lets heritage experts author knowledge directly within an immersive 3D scene. Instead of translating observations into a separate document, an expert selects an architectural component and narrates an interpretation in natural language. The system retains the interpretation while lightly parsing clearly stated information, such as material, period, or function, into a spatially anchored panel.

<img src="/assets/research/spatialtel/usage%20scenarios.png" alt="HeriTell usage scenarios: exploring a heritage scene, narrating an interpretation, resolving ambiguity, and viewing spatially anchored knowledge" loading="lazy" width="8359" height="5126">

The authoring flow is designed to be low-friction: enter and explore the scene, point to a component, speak, then receive either a confirmation or a clarification prompt when the referent or description is ambiguous. Over time, the scene is augmented with component-level knowledge panels that retain both the original narrative and its spatial reference.

## From records to situated interpretation

The project was developed as a design-led research probe rather than as a system-performance evaluation. Its design follows three principles: articulate interpretive knowledge in space; allow casual expert narration before applying minimal structure; and support knowledge that can accumulate, be revisited, and be compared across contributors and sessions.

<img src="/assets/research/spatialtel/expert%20records.png" alt="Examples of current heritage documentation: annotated CAD drawings and written records alongside digital-asset images" loading="lazy" width="8549" height="3124">

In a formative study, two cultural-heritage experts with more than fifteen years of professional experience used HeriTell to contribute interpretations to five to eight components of a Chinese Buddhist-temple scene. Their situated accounts revealed three forms of knowledge that are difficult to reduce to isolated attributes:

- **Historical reasoning across time and cultures**: formal details became evidence for processes of cultural transmission and change.
- **Style as social and political code**: decorative features gained meaning through their placement, role, and symbolic status.
- **Relational knowledge across components**: experts explained objects through their relationships to adjacent elements and to the larger spatial setting.

Experts also identified remote contribution, long-term multi-expert documentation, teaching, and museum interpretation as promising scenarios for further development. These are opportunities suggested by the probe, rather than claims of a completed deployment.

## System Implementation

The prototype was built in Unity and deployed on Meta Quest 3. It combines voice interaction with an LLM-orchestrated workflow: speech is transcribed, minimally parsed, and returned as a spatially anchored semi-structured annotation; ambiguous input triggers a clarification request. Component-specific records are stored as JSON, allowing contributions to be updated and revisited within the scene.

<img src="/assets/research/spatialtel/system%20implementation.png" alt="System Implementation" loading="lazy" width="8549" height="3124">

## Project Poster

<img src="/assets/research/spatialtel/20260404_HeriTell%20Poster.png" alt="HeriTell CHI EA 2026 poster" loading="lazy" width="5027" height="7082">

The study is published as a CHI EA '26 extended abstract. [Read the paper ↗](https://doi.org/10.1145/3772363.3798478)

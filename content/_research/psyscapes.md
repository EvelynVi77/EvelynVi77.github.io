---
title: "PsyScapes"
order: 25
home_section: research
home_order: 3
home_label: "Personalized VR · Research in progress · 2026"
home_excerpt: "An exploration of compassionate-place imagery in personalized VR, examining how ambient sound, object interaction, and environmental motion shape experiences of comfort and support."
excerpt: "Exploring how sound, object interaction, and environmental motion shape compassionate-place imagery in personalized VR."
header:
  teaser: /assets/research/psyscapes/teaser.png
classes: wide
---

Research in Progress | 2026

*Externalizing compassionate-place imagery in VR*

What happens when a place imagined for comfort becomes a space we can enter? PsyScapes explores how personal mental imagery can take shape as an immersive environment. Inspired by compassionate-place practice, the project translates a person's description of a place associated with safeness, calmness, and compassionate support into a personalized VR scene.

I am developing a configurable prototype to study how particular sensory and interactive features shape this experience. The research focuses on three features: ambient sound, object interaction, and proximity-responsive motion.

{% include figure image_path="/assets/research/psyscapes/cover.png" alt="A first-person VR view of a sunlit greenhouse with suspended flowers, a central path, and virtual hands" caption="An early visualization of a personalized compassionate place: a sunlit, flower-filled greenhouse." %}

## From imagined place to immersive environment

Compassionate-place practice invites a person to imagine a setting that feels safe and supportive. PsyScapes asks how a virtual environment could help someone explore and sustain their own imagery. Personalization begins with their description, followed by an opportunity to check the generated image before it becomes a three-dimensional scene.

The proposed workflow has five stages:

1. **Describe the place.** Following Compassion-Focused Imagery (CFI) guidance, the person describes their compassionate place in their own words.
2. **Confirm the image.** A diffusion model produces an initial panoramic image for the person to review.
3. **Generate the scene.** World Labs Atlas converts the image into a navigable environment represented with 3D Gaussian Splatting (3DGS).
4. **Identify elements for interaction.** Scene segmentation separates potential interactable objects and environmental elements such as trees or water.
5. **Configure the experience.** Sound, object interaction, and proximity-responsive motion are added as independently adjustable features.

{% include figure image_path="/assets/research/psyscapes/system-pipeline.svg" alt="Proposed PsyScapes pipeline from a guided place description through image confirmation, 3D scene generation, and segmentation to VR with three configurable features" caption="Proposed system pipeline, illustrated through the greenhouse example. Open the figure to inspect the stages and feature settings." popup=true %}

## What makes a place feel responsive?

The central research question is: **How do specific features in personalized VR environments shape compassionate affect during CFI-based compassionate-place practice?**

The prototype is being designed to vary three aspects of the same personalized scene:

- **Ambient sound:** the type, volume, and spatial placement of sounds in the environment.
- **Object interaction:** which objects can be interacted with, how the person interacts, and what feedback follows.
- **Proximity-responsive motion:** how environmental elements respond as the person approaches, including trigger distance, response delay, and motion intensity.

These controls will make it possible to compare experiences while keeping the underlying place consistent. A feasibility pilot will refine the features for perceptibility, comfort, and technical reliability before the main study.

## Planned study

The proposed study uses four conditions within participants, presented in counterbalanced order: a baseline without the three added features and three variants that each introduce one feature. Each person will explore the same personalized scene across all conditions. The same CFI voice guidance, exposure duration, and exploration instructions will be used throughout, with movement permitted within a 3 × 3 m area.

{% include figure image_path="/assets/research/psyscapes/study-design.svg" alt="Planned study: generate a personalized VR scene, compare a baseline and three variants in counterbalanced order, then conduct an interview; compassionate affect is rated before and after each condition, with HRV recorded during VR" caption="Planned four-condition comparison. CA denotes compassionate affect; HRV denotes heart rate variability." popup=true %}

Compassionate-affect ratings before and after each condition will be the primary measure, supported by heart rate variability and a final interview. The interviews will examine which features help maintain imagery, which become distracting, and which feel personally meaningful. The aim is to develop design guidance for systems that externalize personal mental imagery through VR.

## Work to date

Preliminary work includes a review of CFI and VR literature, an initial description-to-scene pipeline, a compassionate-figure prototype, and interviews with four practitioners experienced in Compassion-Focused Therapy or guided mental imagery. The complete configurable pipeline and comparative study are the next stages of the project.

This work builds on my experience with spatial externalization in [HeriTell]({{ '/research/spatialtel/' | relative_url }}) and Unity development and VR interaction in [Flux Tower]({{ '/research/flux-tower/' | relative_url }}).

- *Collaboration with Pengcheng An from Southern University of Science and Technology.*
